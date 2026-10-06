"""Runs the graph for one chat turn and turns LangGraph's stream into UI events.

Event types (sent to the browser as SSE by the chat module):
    plan    {"plan": [["job_search"], ["resume"], ["validation"]]}
    step    {"agentId", "agentName", "status": "running" | "completed" | "failed", "summary"?}
    memory  {"saved": 2}
    answer  {"answer": "...", "agentOutputs": {...}, "steps": [...]}

Memory tiers:
    working       graph state for this run (shared by every agent via reducers)
    conversation  checkpointer keyed by conversation id (agent outputs survive between turns)
                  + recent messages from the database (survive restarts)
    long-term     SqlMemoryStore facts per user (shared across all conversations)
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import StreamMode
from pydantic.alias_generators import to_camel

from app.agents.base import AgentSpec
from app.orchestrator.graph import OrchestratorDeps, build_graph
from app.orchestrator.state import CareerState


class Orchestrator:
    def __init__(
        self, deps: OrchestratorDeps, checkpointer: BaseCheckpointSaver[Any] | None = None
    ) -> None:
        # InMemorySaver keeps per-conversation agent state for the life of the process.
        # Phase 3: AsyncPostgresSaver (langgraph-checkpoint-postgres) for durability.
        self.deps = deps
        self.graph = build_graph(deps.registry, checkpointer or InMemorySaver())

    @property
    def agents(self) -> list[AgentSpec]:
        return list(self.deps.registry.values())

    async def stream(
        self,
        *,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID,
        request: str,
        profile: dict[str, Any],
        history: list[dict[str, str]],
    ) -> AsyncIterator[dict[str, Any]]:
        run_id = str(uuid.uuid4())
        config: RunnableConfig = {"configurable": {"thread_id": str(conversation_id)}}
        initial: CareerState = {
            "user_id": str(user_id),
            "run_id": run_id,
            "request": request,
            "profile": profile,
            "history": history,
        }
        modes: list[StreamMode] = ["custom", "updates"]

        async for mode, chunk in self.graph.astream(
            initial, config, context=self.deps, stream_mode=modes
        ):
            if not isinstance(chunk, dict):
                continue
            if mode == "custom":  # events nodes emitted via runtime.stream_writer
                yield dict(chunk)
                continue
            # mode == "updates": {node_name: the partial state that node returned}
            for node, update in chunk.items():
                if not isinstance(update, dict):
                    continue
                for step in update.get("steps", []):
                    yield {
                        "type": "step",
                        "agentId": step["agent_id"],
                        "agentName": step["agent_name"],
                        "status": step["status"],
                        "summary": step["summary"],
                        "usedLlm": step["used_llm"],
                    }
                if node == "respond":
                    final = await self.graph.aget_state(config)
                    values = final.values
                    steps = [s for s in values.get("steps", []) if s["run_id"] == run_id]
                    ran = {s["agent_id"] for s in steps}
                    yield {
                        "type": "answer",
                        "runId": run_id,
                        "answer": update["answer"],
                        # Agent ids stay as keys; everything inside goes camelCase for the UI.
                        "agentOutputs": {
                            agent_id: camelize(output)
                            for agent_id, output in values.get("agent_outputs", {}).items()
                            if agent_id in ran
                        },
                        "steps": camelize(steps),
                    }


def camelize(value: Any) -> Any:
    """Recursively convert dict keys to camelCase (match_score → matchScore)."""
    if isinstance(value, dict):
        return {to_camel(str(key)): camelize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [camelize(item) for item in value]
    return value
