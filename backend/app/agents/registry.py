"""Every agent the orchestrator can run. Adding an agent:
1. copy any folder in app/agents/ (schema.py, prompt.py, agent.py, __init__.py),
2. add its SPEC below. The graph, planner and /api/agents pick it up automatically.
"""

from __future__ import annotations

from app.agents import (
    advisor,
    interview,
    job_search,
    productivity,
    resume,
    roadmap,
    validation,
)
from app.agents.base import AgentSpec

AGENTS: tuple[AgentSpec, ...] = (
    job_search.SPEC,
    resume.SPEC,
    validation.SPEC,
    productivity.SPEC,
    roadmap.SPEC,
    advisor.SPEC,
    interview.SPEC,
)

REGISTRY: dict[str, AgentSpec] = {spec.id: spec for spec in AGENTS}
