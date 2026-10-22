"""The shared graph state: the only way agents communicate.

Each agent node returns a partial update. The reducer on each field decides
how that update merges in. Reducers are also what make it safe to run two
agents in parallel: both updates merge, neither overwrites the other.

    field           reducer              holds
    agent_outputs   merge dicts          each agent's latest output, keyed by agent id;
                                         persists across turns via the checkpointer
    steps           append               every agent run (the UI's step list)
    memory_writes   append               facts agents proposed; saved after the run
    errors          append               failures, so the run continues and reports them
    (others)        last write wins      request, plan, profile, memories, graph_insights,
                                         history, answer
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict


def merge_dicts(left: dict[str, Any] | None, right: dict[str, Any] | None) -> dict[str, Any]:
    return {**(left or {}), **(right or {})}


class Step(TypedDict):
    run_id: str
    agent_id: str
    agent_name: str
    status: Literal["completed", "failed"]
    summary: str
    used_llm: bool


class MemoryWrite(TypedDict):
    run_id: str
    kind: str
    content: str
    source_agent: str


class AgentFailure(TypedDict):
    run_id: str
    agent_id: str
    message: str


class CareerState(TypedDict, total=False):
    # Input for each run (last write wins)
    user_id: str
    run_id: str
    request: str
    requested_agents: list[str]  # set by an agent's own page; empty = let the planner decide
    profile: dict[str, Any]
    history: list[dict[str, str]]  # recent messages, loaded from the database each turn

    # Set by the graph
    memories: list[str]
    graph_insights: str  # shared knowledge-graph aggregates around this user's roles/skills
    plan: list[list[str]]  # stages; agents inside one stage run in parallel
    answer: str

    # Merged by reducers
    agent_outputs: Annotated[dict[str, Any], merge_dicts]
    steps: Annotated[list[Step], operator.add]
    memory_writes: Annotated[list[MemoryWrite], operator.add]
    errors: Annotated[list[AgentFailure], operator.add]
