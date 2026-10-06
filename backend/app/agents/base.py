"""The contract every agent implements.

An agent is a pure async function: AgentContext in, AgentResult out.

- It reads what it needs from the context: the user's request, profile,
  long-term memories, recent messages, and the outputs of the agents it
  declared in `reads`. That is the shared memory; agents never call each
  other.
- It may propose durable facts (`facts`). The orchestrator saves them to
  long-term memory after the run, so every agent sees them in later
  conversations.
- It never touches the database or HTTP. lint-imports enforces this.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from app.llm.errors import LlmError
from app.llm.pool import Tier

M = TypeVar("M", bound=BaseModel)


class LlmClient(Protocol):
    """What agents may do with the LLM gateway (keeps agents testable with fakes)."""

    @property
    def available(self) -> bool: ...

    async def complete_json(
        self, *, system: str, user: str, schema: type[M], tier: Tier = "large"
    ) -> M: ...


@dataclass(frozen=True)
class MemoryFact:
    """A durable fact about the user, e.g. kind="preference", content="Prefers remote roles"."""

    kind: str
    content: str


@dataclass(frozen=True)
class AgentContext:
    request: str
    profile: dict[str, Any]
    memories: list[str]
    inputs: dict[str, Any]  # outputs of the agents listed in AgentSpec.reads (if they ran)
    recent_messages: list[dict[str, str]]
    rendered: str  # all of the above as one prompt block, already trimmed to the token budget
    llm: LlmClient


@dataclass(frozen=True)
class AgentResult:
    output: BaseModel
    summary: str  # one line for the chat's step list
    facts: list[MemoryFact] = field(default_factory=list)
    used_llm: bool = False


@dataclass(frozen=True)
class AgentSpec:
    id: str
    name: str
    description: str  # the supervisor reads this when planning
    run: Callable[[AgentContext], Awaitable[AgentResult]]
    reads: tuple[str, ...] = ()  # other agents' outputs this agent consumes
    keywords: tuple[str, ...] = ()  # fallback routing when no LLM is configured


async def generate(
    ctx: AgentContext,
    *,
    system: str,
    schema: type[M],
    fallback: Callable[[], M],
    tier: Tier = "large",
) -> tuple[M, bool]:
    """LLM output validated against `schema`, or the agent's deterministic fallback.

    Returns (output, used_llm). The pipeline always completes, even with no
    keys configured or every key rate-limited.
    """
    if not ctx.llm.available:
        return fallback(), False
    try:
        return await ctx.llm.complete_json(
            system=system, user=ctx.rendered, schema=schema, tier=tier
        ), True
    except LlmError:
        return fallback(), False
