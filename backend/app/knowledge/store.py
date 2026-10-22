"""Knowledge graph for the orchestrator: opens its own sessions (like SqlMemoryStore).

insights_text()   what agents see: shared knowledge around the user's roles and skills
record_postings() learn from the Job Search agent's live postings after each run
"""

from __future__ import annotations

import uuid
from typing import Any

from app.db.session import Database
from app.knowledge.repository import GraphRepository
from app.knowledge.types import Neighbour, UserInsights


def _support(n: Neighbour) -> str:
    parts = []
    if n.postings:
        parts.append(f"{n.postings} posting{'s' if n.postings != 1 else ''}")
    if n.users:
        parts.append(f"{n.users} users")
    return ", ".join(parts)


def render_insights(insights: UserInsights) -> str:
    """Compact text block for agent prompts; "" when the graph has nothing to add yet."""
    if insights.empty:
        return ""
    lines = ["Anonymous aggregates from all users and real job postings (not this user's data)."]
    for role in insights.roles:
        if role.skills:
            skills = "; ".join(
                f"{n.node.label} ({_support(n)}{', user has it' if n.yours else ', GAP'})"
                for n in role.skills
            )
            lines.append(f"- {role.role.label}: skills most associated — {skills}")
        if role.companies:
            names = ", ".join(n.node.label for n in role.companies)
            lines.append(f"- {role.role.label}: companies seen hiring — {names}")
        if role.next_roles:
            names = ", ".join(n.node.label for n in role.next_roles)
            lines.append(f"- {role.role.label}: people often move on to — {names}")
    if insights.adjacent_skills:
        names = ", ".join(f"{n.node.label} ({_support(n)})" for n in insights.adjacent_skills)
        lines.append(f"- Skills often paired with the user's: {names}")
    return "\n".join(lines)


class SqlKnowledgeGraph:
    def __init__(self, db: Database, *, min_users: int = 3) -> None:
        self.db = db
        self.min_users = min_users

    async def insights_text(self, user_id: uuid.UUID, profile: dict[str, Any]) -> str:
        async with self.db.session() as session:
            repository = GraphRepository(session, min_users=self.min_users)
            # Profiles saved before the graph existed join it on their first run.
            if profile and not await repository.has_links(user_id):
                await repository.sync_user(user_id, profile)
            return render_insights(await repository.insights(user_id))

    async def record_postings(self, job_search_output: dict[str, Any]) -> int:
        async with self.db.session() as session:
            return await GraphRepository(session, min_users=self.min_users).record_postings(
                job_search_output
            )
