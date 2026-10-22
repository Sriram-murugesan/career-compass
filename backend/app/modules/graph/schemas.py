from __future__ import annotations

from app.core.schema import ApiModel


class NodeOut(ApiModel):
    kind: str  # skill | role | company
    key: str  # normalised id, use it in /graph/nodes/{kind}/{key}
    label: str


class NeighbourOut(ApiModel):
    node: NodeOut
    relation: str
    users: int  # distinct users backing it (0 when below the privacy threshold)
    postings: int  # real job postings backing it
    yours: bool = False  # the signed-in user has this (e.g. the skill)


class LinkOut(ApiModel):
    relation: str  # has_skill | targets_role | current_role
    node: NodeOut


class RoleInsightOut(ApiModel):
    role: NodeOut
    skills: list[NeighbourOut]
    companies: list[NeighbourOut]
    next_roles: list[NeighbourOut]


class MyGraphOut(ApiModel):
    links: list[LinkOut]  # private: only ever returned to this user
    roles: list[RoleInsightOut]
    adjacent_skills: list[NeighbourOut]
    min_users: int  # privacy threshold for profile-derived edges


class NodeDetailOut(ApiModel):
    node: NodeOut
    groups: dict[str, list[NeighbourOut]]  # e.g. skills / companies / next_roles


class PathsOut(ApiModel):
    role: str
    paths: list[list[NodeOut]]  # each path starts at the role
