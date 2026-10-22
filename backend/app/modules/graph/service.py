"""BUSINESS LAYER for the shared knowledge graph's HTTP API.

Everything here is shared knowledge (public edges only), except `me`, which adds the
signed-in user's own links — never another user's.
"""

from __future__ import annotations

import uuid

from app.core.errors import NotFound, ValidationFailed
from app.knowledge.normalize import company_key, role_key, skill_key
from app.knowledge.repository import GraphRepository
from app.knowledge.types import GraphNode, Neighbour
from app.modules.graph.schemas import (
    LinkOut,
    MyGraphOut,
    NeighbourOut,
    NodeDetailOut,
    NodeOut,
    PathsOut,
    RoleInsightOut,
)
from app.modules.profile import ProfileService

KINDS = {"skill": skill_key, "role": role_key, "company": company_key}


def _node(node: GraphNode) -> NodeOut:
    return NodeOut(kind=node.kind, key=node.key, label=node.label)


def _neighbour(n: Neighbour) -> NeighbourOut:
    return NeighbourOut(
        node=_node(n.node), relation=n.relation, users=n.users, postings=n.postings, yours=n.yours
    )


class GraphService:
    def __init__(self, repository: GraphRepository, profiles: ProfileService) -> None:
        self.repository = repository
        self.profiles = profiles

    async def me(self, user_id: uuid.UUID) -> MyGraphOut:
        if not await self.repository.has_links(user_id):
            # Profiles saved before the graph existed join it on first view.
            await self.repository.sync_user(user_id, await self.profiles.snapshot(user_id))
        insights = await self.repository.insights(user_id)
        return MyGraphOut(
            links=[
                LinkOut(relation=link.relation, node=_node(link.node)) for link in insights.links
            ],
            roles=[
                RoleInsightOut(
                    role=_node(role.role),
                    skills=[_neighbour(n) for n in role.skills],
                    companies=[_neighbour(n) for n in role.companies],
                    next_roles=[_neighbour(n) for n in role.next_roles],
                )
                for role in insights.roles
            ],
            adjacent_skills=[_neighbour(n) for n in insights.adjacent_skills],
            min_users=self.repository.min_users,
        )

    async def node(self, kind: str, key: str) -> NodeDetailOut:
        normalise = KINDS.get(kind)
        if normalise is None:
            raise ValidationFailed("kind must be skill, role or company")
        normalised = normalise(key)
        node = await self.repository.node(kind, normalised)
        if node is None:  # unknown, or only backed privately: indistinguishable on purpose
            raise NotFound("Not in the shared graph yet")
        groups = await self.repository.node_neighbourhood(kind, normalised)
        return NodeDetailOut(
            node=_node(node),
            groups={name: [_neighbour(n) for n in items] for name, items in groups.items()},
        )

    async def search(self, query: str, kind: str | None) -> list[NodeOut]:
        if kind is not None and kind not in KINDS:
            raise ValidationFailed("kind must be skill, role or company")
        return [_node(n) for n in await self.repository.search(query, kind)]

    async def paths(self, role: str) -> PathsOut:
        paths = await self.repository.paths(role)
        return PathsOut(role=role, paths=[[_node(n) for n in path] for path in paths])
