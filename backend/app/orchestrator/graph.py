"""Builds the LangGraph StateGraph from the agent registry.

    START → load_memory → supervisor → dispatch ─┬─► stage N agents (parallel) ─┐
                                         ▲       │                              │
                                         └───────┼──────────────────────────────┘
                                                 └─► respond → save_memory → END

Dependencies (LLM gateway, memory store, context builder) arrive through the
LangGraph runtime context, so the graph imports no infrastructure and is
easy to test with fakes.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.runtime import Runtime

from app.agents.base import AgentSpec, LlmClient
from app.memory.context import ContextBuilder
from app.memory.store import MemoryStore, NewMemory
from app.orchestrator.planner import make_plan
from app.orchestrator.state import CareerState, MemoryWrite, Step

logger = logging.getLogger("app.orchestrator")

RESPOND = "respond"
DISPATCH = "dispatch"


@dataclass(frozen=True)
class OrchestratorDeps:
    llm: LlmClient
    memory: MemoryStore
    context_builder: ContextBuilder
    registry: dict[str, AgentSpec]
    memory_recall_limit: int = 5


def _finished_this_run(state: CareerState) -> set[str]:
    run_id = state.get("run_id")
    return {step["agent_id"] for step in state.get("steps", []) if step["run_id"] == run_id}


def route(state: CareerState) -> list[str] | str:
    """Next stage of the plan with agents still to run in THIS run, else respond."""
    done = _finished_this_run(state)
    for stage in state.get("plan", []):
        pending = [agent_id for agent_id in stage if agent_id not in done]
        if pending:
            return pending
    return RESPOND


async def load_memory(state: CareerState, runtime: Runtime[OrchestratorDeps]) -> dict[str, Any]:
    deps = runtime.context
    memories = await deps.memory.recall(
        uuid.UUID(state["user_id"]), state["request"], deps.memory_recall_limit
    )
    return {"memories": memories}


async def supervisor(state: CareerState, runtime: Runtime[OrchestratorDeps]) -> dict[str, Any]:
    deps = runtime.context
    plan = await make_plan(state["request"], deps.registry, deps.llm)
    runtime.stream_writer({"type": "plan", "plan": plan})
    return {"plan": plan}


def make_agent_node(spec: AgentSpec) -> Any:
    async def node(state: CareerState, runtime: Runtime[OrchestratorDeps]) -> dict[str, Any]:
        deps = runtime.context
        run_id = state["run_id"]
        runtime.stream_writer(
            {"type": "step", "agentId": spec.id, "agentName": spec.name, "status": "running"}
        )
        context = deps.context_builder.build(
            spec,
            request=state["request"],
            profile=state.get("profile", {}),
            memories=state.get("memories", []),
            agent_outputs=state.get("agent_outputs", {}),
            history=state.get("history", []),
            llm=deps.llm,
        )
        try:
            result = await spec.run(context)
        except Exception as exc:  # one failing agent must not sink the whole run
            logger.exception("agent %s failed", spec.id)
            failed: Step = {
                "run_id": run_id,
                "agent_id": spec.id,
                "agent_name": spec.name,
                "status": "failed",
                "summary": "Agent failed — the others continued",
                "used_llm": False,
            }
            return {
                "steps": [failed],
                "errors": [{"run_id": run_id, "agent_id": spec.id, "message": str(exc)[:300]}],
            }

        step: Step = {
            "run_id": run_id,
            "agent_id": spec.id,
            "agent_name": spec.name,
            "status": "completed",
            "summary": result.summary,
            "used_llm": result.used_llm,
        }
        writes: list[MemoryWrite] = [
            {"run_id": run_id, "kind": f.kind, "content": f.content, "source_agent": spec.id}
            for f in result.facts
        ]
        return {
            "agent_outputs": {spec.id: result.output.model_dump(mode="json")},
            "steps": [step],
            "memory_writes": writes,
        }

    node.__name__ = f"agent_{spec.id}"
    return node


async def dispatch(state: CareerState) -> dict[str, Any]:
    """Join point after each stage; `route` then picks the next stage."""
    return {}


async def respond(state: CareerState, runtime: Runtime[OrchestratorDeps]) -> dict[str, Any]:
    run_id = state["run_id"]
    steps = [step for step in state.get("steps", []) if step["run_id"] == run_id]
    if not steps:
        return {"answer": "I couldn't find an agent for that request."}
    lines = [f"- **{step['agent_name']}**: {step['summary']}" for step in steps]
    return {"answer": "Here's what your agents did:\n" + "\n".join(lines)}


async def save_memory(state: CareerState, runtime: Runtime[OrchestratorDeps]) -> dict[str, Any]:
    run_id = state["run_id"]
    facts = [
        NewMemory(kind=w["kind"], content=w["content"], source_agent=w["source_agent"])
        for w in state.get("memory_writes", [])
        if w["run_id"] == run_id
    ]
    saved = await runtime.context.memory.remember(uuid.UUID(state["user_id"]), facts)
    runtime.stream_writer({"type": "memory", "saved": saved})
    return {}


def build_graph(
    registry: dict[str, AgentSpec], checkpointer: BaseCheckpointSaver[Any]
) -> CompiledStateGraph[Any, Any, Any, Any]:
    graph = StateGraph(CareerState, context_schema=OrchestratorDeps)
    graph.add_node("load_memory", load_memory)
    graph.add_node("supervisor", supervisor)
    for spec in registry.values():
        graph.add_node(spec.id, make_agent_node(spec))
    graph.add_node(DISPATCH, dispatch)
    graph.add_node(RESPOND, respond)
    graph.add_node("save_memory", save_memory)

    graph.add_edge(START, "load_memory")
    graph.add_edge("load_memory", "supervisor")
    graph.add_edge("supervisor", DISPATCH)
    # Every agent joins back at dispatch. A routing function only sees its own node's
    # writes, so routing per agent would re-run parallel siblings; routing once at the
    # join sees the whole stage's merged state.
    for agent_id in registry:
        graph.add_edge(agent_id, DISPATCH)
    graph.add_conditional_edges(DISPATCH, route, [*registry, RESPOND])
    graph.add_edge(RESPOND, "save_memory")
    graph.add_edge("save_memory", END)
    return graph.compile(checkpointer=checkpointer)
