"""The supervisor's planning step: which agents run, in which order.

A plan is a list of stages. Agents inside one stage run in parallel; stages
run one after another. With an LLM configured, the model plans from the
agents' descriptions. Without one (or if its plan is invalid), keyword rules
decide. Either way, an agent is always scheduled after the agents it `reads`.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from app.agents.base import AgentSpec, LlmClient
from app.llm.errors import LlmError

logger = logging.getLogger("app.orchestrator")

FULL_REVIEW_WORDS = ("everything", "full review", "all agents", "complete review")


class PlanOutput(BaseModel):
    agents: list[str]


def order_into_stages(agent_ids: list[str], registry: dict[str, AgentSpec]) -> list[list[str]]:
    """Group agents into stages so each runs after the agents it reads (if they're in the plan)."""
    selected = [agent_id for agent_id in dict.fromkeys(agent_ids) if agent_id in registry]
    stages: list[list[str]] = []
    placed: set[str] = set()
    while len(placed) < len(selected):
        ready = [
            agent_id
            for agent_id in selected
            if agent_id not in placed
            and all(dep in placed or dep not in selected for dep in registry[agent_id].reads)
        ]
        if not ready:  # a dependency cycle: run the rest sequentially rather than fail
            ready = [next(a for a in selected if a not in placed)]
        stages.append(ready)
        placed.update(ready)
    return stages


def keyword_plan(request: str, registry: dict[str, AgentSpec]) -> list[str]:
    text = request.lower()
    if any(phrase in text for phrase in FULL_REVIEW_WORDS):
        return list(registry)
    words = set(text.replace("?", " ").replace(",", " ").split())
    chosen = [spec.id for spec in registry.values() if words & set(spec.keywords)]
    # Tailoring a resume "for a role" needs a job match first; validating a draft needs the draft.
    if "resume" in chosen and ("job_search" in chosen or "for" in words):
        chosen.insert(0, "job_search")
    if "validation" in chosen and "resume" not in chosen:
        chosen.insert(0, "resume")
    return chosen or ["advisor"]


async def make_plan(
    request: str, registry: dict[str, AgentSpec], llm: LlmClient
) -> list[list[str]]:
    agent_ids: list[str] = []
    if llm.available:
        catalogue = "\n".join(f"- {s.id}: {s.description}" for s in registry.values())
        try:
            plan = await llm.complete_json(
                system=(
                    "You route a career-coaching request to specialist agents. Pick the smallest "
                    f"set of agent ids that answers it. Available agents:\n{catalogue}"
                ),
                user=request,
                schema=PlanOutput,
                tier="fast",
            )
            agent_ids = [agent_id for agent_id in plan.agents if agent_id in registry]
        except LlmError as exc:
            logger.warning("llm planning failed, using keyword plan: %s", exc)
    if not agent_ids:
        agent_ids = keyword_plan(request, registry)
    return order_into_stages(agent_ids, registry)
