"""The agent graph: planning, parallel stages, shared state between agents,
memory across turns and conversations, failure isolation, LLM-backed agents."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, TypeVar

import pytest
from pydantic import BaseModel

from app.agents.base import AgentContext, AgentResult, AgentSpec
from app.agents.registry import REGISTRY
from app.db.session import Database
from app.memory.context import ContextBuilder
from app.memory.store import NewMemory, SqlMemoryStore
from app.model_registry import Base
from app.orchestrator import Orchestrator, OrchestratorDeps
from app.orchestrator.planner import keyword_plan, order_into_stages

M = TypeVar("M", bound=BaseModel)

PROFILE = {
    "headline": "Full-stack engineer",
    "target_roles": ["Senior Frontend Engineer"],
    "skills": [{"name": "TypeScript", "category": "Technical", "level": "Expert"}],
    "goals": ["Senior role in 6 months"],
    "location": "London",
}


class NoLlm:
    available = False

    async def complete_json(
        self, *, system: str, user: str, schema: type[M], tier: str = "large"
    ) -> M:
        raise AssertionError("must not be called when unavailable")


@pytest.fixture
async def database(tmp_path: Path) -> AsyncIterator[Database]:
    db = Database(f"sqlite+aiosqlite:///{(tmp_path / 'o.db').as_posix()}")
    async with db.engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield db
    await db.dispose()


def make_orchestrator(
    db: Database, registry: dict[str, AgentSpec] | None = None, llm: Any = None
) -> Orchestrator:
    return Orchestrator(
        OrchestratorDeps(
            llm=llm or NoLlm(),
            memory=SqlMemoryStore(db),
            context_builder=ContextBuilder(budget_chars=6000),
            registry=registry or REGISTRY,
        )
    )


async def run(
    orchestrator: Orchestrator, request: str, *, user: uuid.UUID, thread: uuid.UUID
) -> list[dict[str, Any]]:
    return [
        event
        async for event in orchestrator.stream(
            user_id=user, conversation_id=thread, request=request, profile=PROFILE, history=[]
        )
    ]


def answer_of(events: list[dict[str, Any]]) -> dict[str, Any]:
    return next(e for e in events if e["type"] == "answer")


# ── Planning ────────────────────────────────────────────────────────────────


def test_dependencies_order_the_stages() -> None:
    stages = order_into_stages(list(REGISTRY), REGISTRY)
    assert stages[0] == ["job_search", "productivity"]  # no inputs → run first, in parallel
    flat = [agent for stage in stages for agent in stage]
    for agent_id, spec in REGISTRY.items():
        for dependency in spec.reads:
            assert flat.index(dependency) < flat.index(agent_id), (agent_id, dependency)


def test_keyword_plan_adds_what_an_agent_needs() -> None:
    assert keyword_plan("validate my resume", REGISTRY) == ["resume", "validation"]
    assert keyword_plan("tailor my resume for Kepler", REGISTRY)[:2] == ["job_search", "resume"]
    assert keyword_plan("hello there", REGISTRY) == ["advisor"]


# ── Shared state ────────────────────────────────────────────────────────────


async def test_full_review_runs_every_agent_and_merges_parallel_outputs(database: Database) -> None:
    events = await run(
        make_orchestrator(database), "give me a full review", user=uuid.uuid4(), thread=uuid.uuid4()
    )
    plan = next(e for e in events if e["type"] == "plan")["plan"]
    assert plan[0] == ["job_search", "productivity"]

    answer = answer_of(events)
    assert set(answer["agentOutputs"]) == set(REGISTRY)  # reducer merged all 7, parallel ones too
    assert [s["status"] for s in answer["steps"]] == ["completed"] * 7
    running = [e["agentId"] for e in events if e["type"] == "step" and e["status"] == "running"]
    assert sorted(running) == sorted(REGISTRY)


async def test_agents_read_each_others_outputs_through_state(database: Database) -> None:
    events = await run(
        make_orchestrator(database),
        "tailor my resume for a role and validate it",
        user=uuid.uuid4(),
        thread=uuid.uuid4(),
    )
    outputs = answer_of(events)["agentOutputs"]
    top_match = outputs["job_search"]["matches"][0]["role"]
    assert outputs["resume"]["targetRole"] == top_match  # resume read job_search's output
    assert outputs["validation"]["checks"][0]["label"] == "Summary present"  # validated that resume


async def test_outputs_persist_between_turns_of_one_conversation(database: Database) -> None:
    orchestrator, user, thread = make_orchestrator(database), uuid.uuid4(), uuid.uuid4()
    await run(orchestrator, "find jobs for me", user=user, thread=thread)

    # Turn 2 runs only the interview agent; it still sees turn 1's job search (checkpointer).
    events = await run(orchestrator, "practice interview questions", user=user, thread=thread)
    answer = answer_of(events)
    assert [s["agentId"] for s in answer["steps"]] == ["interview"]
    assert answer["agentOutputs"]["interview"]["focus"] == "Senior Frontend Engineer"


async def test_long_term_memory_is_shared_across_conversations(database: Database) -> None:
    orchestrator, user = make_orchestrator(database), uuid.uuid4()
    first = await run(orchestrator, "find jobs for me", user=user, thread=uuid.uuid4())
    assert next(e for e in first if e["type"] == "memory")["saved"] == 1

    seen: list[list[str]] = []

    async def spy(ctx: AgentContext) -> AgentResult:
        seen.append(ctx.memories)
        return await REGISTRY["advisor"].run(ctx)

    registry = {**REGISTRY, "advisor": AgentSpec(**{**REGISTRY["advisor"].__dict__, "run": spy})}
    # A brand-new conversation (new thread) still recalls what job search learned.
    await run(
        make_orchestrator(database, registry),
        "any career advice for me?",
        user=user,
        thread=uuid.uuid4(),
    )
    assert seen and any("Senior Frontend Engineer" in fact for fact in seen[0])

    other_user = await SqlMemoryStore(database).recall(uuid.uuid4(), "jobs", 5)
    assert other_user == []  # memories are per user


async def test_memory_store_deduplicates_facts(database: Database) -> None:
    store, user = SqlMemoryStore(database), uuid.uuid4()
    fact = NewMemory(kind="preference", content="Prefers remote roles", source_agent="advisor")
    assert await store.remember(user, [fact]) == 1
    assert (
        await store.remember(user, [fact, NewMemory("preference", "prefers REMOTE roles ", "x")])
        == 0
    )
    assert await store.recall(user, "remote", 5) == ["Prefers remote roles"]


# ── Resilience ──────────────────────────────────────────────────────────────


async def test_one_failing_agent_does_not_sink_the_run(database: Database) -> None:
    async def explode(_: AgentContext) -> AgentResult:
        raise RuntimeError("boom")

    registry = {
        **REGISTRY,
        "resume": AgentSpec(**{**REGISTRY["resume"].__dict__, "run": explode}),
    }
    events = await run(
        make_orchestrator(database, registry),
        "tailor my resume for a role and validate it",
        user=uuid.uuid4(),
        thread=uuid.uuid4(),
    )
    statuses = {s["agentId"]: s["status"] for s in answer_of(events)["steps"]}
    assert statuses == {"job_search": "completed", "resume": "failed", "validation": "completed"}


class ScriptedLlm:
    """Fake LLM: returns schema-valid objects, records which schemas were requested."""

    available = True

    def __init__(self) -> None:
        self.calls: list[str] = []

    async def complete_json(
        self, *, system: str, user: str, schema: type[M], tier: str = "large"
    ) -> M:
        self.calls.append(schema.__name__)
        if schema.__name__ == "PlanOutput":
            return schema.model_validate({"agents": ["interview"]})
        return schema.model_validate({"focus": "Staff Engineer", "questions": ["Why us?"]})


async def test_llm_plans_and_agents_use_the_llm_when_available(database: Database) -> None:
    llm = ScriptedLlm()
    events = await run(
        make_orchestrator(database, llm=llm),
        "help me get ready",
        user=uuid.uuid4(),
        thread=uuid.uuid4(),
    )
    answer = answer_of(events)
    assert llm.calls == ["PlanOutput", "InterviewOutput"]
    assert answer["steps"][0]["usedLlm"] is True
    assert answer["agentOutputs"]["interview"]["focus"] == "Staff Engineer"
