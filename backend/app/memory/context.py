"""Context builder: decides exactly what each agent sees.

Fills the prompt in priority order until the character budget is spent, so a
long history can never overflow the model's context window:

    1. the user's request           (always)
    2. the profile snapshot
    3. outputs of agents this agent declared in `reads`   ← shared memory within a run
    4. long-term memories recalled for this request       ← shared memory across conversations
    5. recent messages, newest kept first                  ← conversation memory
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.base import AgentContext, AgentSpec, LlmClient


class ContextBuilder:
    def __init__(self, budget_chars: int) -> None:
        self.budget = budget_chars

    def build(
        self,
        spec: AgentSpec,
        *,
        request: str,
        profile: dict[str, Any],
        memories: list[str],
        agent_outputs: dict[str, Any],
        history: list[dict[str, str]],
        llm: LlmClient,
    ) -> AgentContext:
        inputs = {name: agent_outputs[name] for name in spec.reads if name in agent_outputs}
        sections: list[str] = [f"## User request\n{request}"]
        remaining = self.budget - len(sections[0])

        def add(title: str, body: str) -> None:
            nonlocal remaining
            block = f"## {title}\n{body}"
            if len(block) > remaining:
                block = block[: max(remaining, 0)].rstrip()
                if len(block) <= len(title) + 4:  # nothing useful left
                    return
                block += " …"
            sections.append(block)
            remaining -= len(block)

        if profile:
            add("Profile", json.dumps(profile, ensure_ascii=False))
        for name, output in inputs.items():
            add(f"Output of {name} agent", json.dumps(output, ensure_ascii=False))
        if memories:
            add("What we remember about the user", "\n".join(f"- {m}" for m in memories))
        if history:
            recent: list[str] = []
            for message in reversed(history):  # newest first, so trimming drops the oldest
                recent.append(f"{message['role']}: {message['content']}")
            add("Recent conversation (newest first)", "\n".join(recent))

        return AgentContext(
            request=request,
            profile=profile,
            memories=memories,
            inputs=inputs,
            recent_messages=history,
            rendered="\n\n".join(sections),
            llm=llm,
        )
