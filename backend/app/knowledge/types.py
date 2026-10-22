"""Plain data + interfaces for the knowledge graph (no SQL here).

Business code (profile service, graph service) and the orchestrator depend on these,
never on the SQL repository directly.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

NodeKind = Literal["skill", "role", "company"]
Relation = Literal["role_skill", "skill_pair", "leads_to", "hires_for"]
UserRelation = Literal["has_skill", "targets_role", "current_role"]


@dataclass(frozen=True)
class GraphNode:
    kind: str
    key: str
    label: str


@dataclass(frozen=True)
class Neighbour:
    node: GraphNode
    relation: str
    direction: Literal["out", "in", "both"]
    users: int  # distinct users backing the edge (only shown at or above the threshold)
    postings: int  # real job postings backing the edge
    yours: bool = False  # the viewing user is linked to this node (e.g. has the skill)

    @property
    def strength(self) -> int:
        return self.users + self.postings


@dataclass(frozen=True)
class UserLink:
    relation: str
    node: GraphNode


@dataclass
class RoleInsight:
    role: GraphNode
    skills: list[Neighbour] = field(default_factory=list)  # most associated skills
    companies: list[Neighbour] = field(default_factory=list)  # who hires for it
    next_roles: list[Neighbour] = field(default_factory=list)  # where people move next


@dataclass
class UserInsights:
    links: list[UserLink] = field(default_factory=list)  # the user's own (private) links
    roles: list[RoleInsight] = field(default_factory=list)
    adjacent_skills: list[Neighbour] = field(default_factory=list)  # pairs well with yours

    @property
    def empty(self) -> bool:
        return not any(
            [r.skills or r.companies or r.next_roles for r in self.roles] + [self.adjacent_skills]
        )


class ProfileGraphSync(Protocol):
    """What the profile service needs: rebuild one user's contribution after an edit."""

    async def sync_user(self, user_id: uuid.UUID, profile: dict[str, Any]) -> None: ...


class KnowledgeGraph(Protocol):
    """What the orchestrator needs: insights for agents, and postings to learn from."""

    async def insights_text(self, user_id: uuid.UUID, profile: dict[str, Any]) -> str: ...

    async def record_postings(self, job_search_output: dict[str, Any]) -> int: ...
