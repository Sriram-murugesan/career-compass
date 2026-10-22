"""DATA LAYER for the shared knowledge graph (nodes / edges / evidence / user links).

Writes
    sync_user        replace one user's links + evidence from their profile
    record_postings  learn company → role and role → skill from real job postings
Reads (shared — only PUBLIC edges: >= min_users distinct users, or >= 1 posting)
    neighbours, search, paths (recursive CTE), insights (for one user, + their own links)

Works on Postgres (Neon/Supabase) and SQLite (tests) alike.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import replace
from itertools import combinations
from typing import Any, Literal

from sqlalchemy import (
    Select,
    String,
    Text,
    and_,
    cast,
    delete,
    distinct,
    exists,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.db.base import utcnow
from app.knowledge.models import KgEdge, KgEvidence, KgNode, KgUserLink
from app.knowledge.normalize import (
    company_key,
    current_role_from_headline,
    role_key,
    role_label,
    skill_key,
)
from app.knowledge.types import GraphNode, Neighbour, RoleInsight, UserInsights, UserLink

MAX_SKILLS = 15  # per user: bounds the skill-pair edges a profile can create (15C2 = 105)
MAX_ROLES = 5
CHUNK = 400  # rows per INSERT (stays far below SQLite's / Postgres' bind-parameter limits)

NodeRef = tuple[str, str]  # (kind, key)
EdgeRef = tuple[uuid.UUID, uuid.UUID, str]  # (src, dst, relation)


def _node(row: KgNode) -> GraphNode:
    return GraphNode(kind=row.kind, key=row.key, label=row.label)


def _chunks(rows: Sequence[dict[str, Any]]) -> Iterable[Sequence[dict[str, Any]]]:
    for start in range(0, len(rows), CHUNK):
        yield rows[start : start + CHUNK]


class GraphRepository:
    def __init__(self, session: AsyncSession, *, min_users: int = 3) -> None:
        self.session = session
        self.min_users = min_users

    def _insert(self) -> Any:
        dialect = self.session.get_bind().dialect.name
        return sqlite_insert if dialect == "sqlite" else pg_insert

    # ── Upserts ─────────────────────────────────────────────────────────────

    async def _nodes(self, items: Iterable[tuple[str, str, str]]) -> dict[NodeRef, uuid.UUID]:
        """(kind, key, label) → node id, creating missing nodes (first label wins)."""
        wanted: dict[NodeRef, str] = {}
        for kind, key, label in items:
            if key and (kind, key) not in wanted:
                wanted[(kind, key)] = label[:120] or key
        if not wanted:
            return {}
        rows = [
            {"id": uuid.uuid4(), "kind": k, "key": key, "label": label, "created_at": utcnow()}
            for (k, key), label in wanted.items()
        ]
        for chunk in _chunks(rows):
            statement = self._insert()(KgNode).values(list(chunk))
            await self.session.execute(
                statement.on_conflict_do_nothing(index_elements=["kind", "key"])
            )
        ids: dict[NodeRef, uuid.UUID] = {}
        for kind in {k for k, _ in wanted}:
            keys = [key for k, key in wanted if k == kind]
            result = await self.session.execute(
                select(KgNode.id, KgNode.key).where(KgNode.kind == kind, KgNode.key.in_(keys))
            )
            ids.update({(kind, key): node_id for node_id, key in result.all()})
        return ids

    async def _edges(self, triples: Iterable[EdgeRef]) -> list[uuid.UUID]:
        wanted = list(dict.fromkeys(t for t in triples if t[0] != t[1]))
        if not wanted:
            return []
        rows = [
            {"id": uuid.uuid4(), "src_id": s, "dst_id": d, "relation": r, "created_at": utcnow()}
            for s, d, r in wanted
        ]
        for chunk in _chunks(rows):
            statement = self._insert()(KgEdge).values(list(chunk))
            await self.session.execute(
                statement.on_conflict_do_nothing(index_elements=["src_id", "dst_id", "relation"])
            )
        found: dict[EdgeRef, uuid.UUID] = {}
        srcs = list({s for s, _, _ in wanted})
        for start in range(0, len(srcs), CHUNK):
            result = await self.session.execute(
                select(KgEdge.id, KgEdge.src_id, KgEdge.dst_id, KgEdge.relation).where(
                    KgEdge.src_id.in_(srcs[start : start + CHUNK]),
                    KgEdge.relation.in_({r for _, _, r in wanted}),
                )
            )
            found.update({(s, d, r): edge_id for edge_id, s, d, r in result.all()})
        return [found[t] for t in wanted if t in found]

    async def _evidence(
        self, edge_ids: list[uuid.UUID], *, user_id: uuid.UUID | None = None, posting: str = ""
    ) -> None:
        rows = [
            {
                "id": uuid.uuid4(),
                "edge_id": edge_id,
                "user_id": user_id,
                "posting_key": posting or None,
                "created_at": utcnow(),
            }
            for edge_id in edge_ids
        ]
        for chunk in _chunks(rows):
            statement = self._insert()(KgEvidence).values(list(chunk))
            await self.session.execute(statement.on_conflict_do_nothing())

    # ── Writes ──────────────────────────────────────────────────────────────

    async def sync_user(self, user_id: uuid.UUID, profile: dict[str, Any]) -> None:
        """Rebuild this user's links and evidence from their current profile."""
        skills: dict[str, str] = {}
        for skill in profile.get("skills") or []:
            name = str(skill.get("name") or "").strip()
            if name and skill_key(name) not in skills and len(skills) < MAX_SKILLS:
                skills[skill_key(name)] = name
        roles: dict[str, str] = {}
        for role in profile.get("target_roles") or []:
            if role_key(str(role)) and role_key(str(role)) not in roles and len(roles) < MAX_ROLES:
                roles[role_key(str(role))] = role_label(str(role))
        current = current_role_from_headline(str(profile.get("headline") or ""))

        ids = await self._nodes(
            [("skill", k, label) for k, label in skills.items()]
            + [("role", k, label) for k, label in roles.items()]
            + ([("role", current.lower(), current)] if current else [])
        )

        await self.session.execute(delete(KgEvidence).where(KgEvidence.user_id == user_id))
        await self.session.execute(delete(KgUserLink).where(KgUserLink.user_id == user_id))

        links = [("has_skill", ids[("skill", k)]) for k in skills]
        links += [("targets_role", ids[("role", k)]) for k in roles]
        if current:
            links.append(("current_role", ids[("role", current.lower())]))
        if links:
            await self.session.execute(
                self._insert()(KgUserLink)
                .values([{"user_id": user_id, "node_id": n, "relation": r} for r, n in links])
                .on_conflict_do_nothing()
            )

        triples: list[EdgeRef] = [
            (ids[("role", r)], ids[("skill", s)], "role_skill") for r in roles for s in skills
        ]
        triples += [  # undirected: always stored with the smaller key first
            (ids[("skill", a)], ids[("skill", b)], "skill_pair")
            for a, b in combinations(sorted(skills), 2)
        ]
        if current:
            triples += [
                (ids[("role", current.lower())], ids[("role", r)], "leads_to")
                for r in roles
                if r != current.lower()
            ]
        await self._evidence(await self._edges(triples), user_id=user_id)
        await self.session.flush()

    async def record_postings(self, job_search_output: dict[str, Any]) -> int:
        """Learn from live postings: company → hires_for → role, role → role_skill → skill."""
        if job_search_output.get("mode") != "live":
            return 0
        recorded = 0
        for match in job_search_output.get("matches") or []:
            url = str(match.get("apply_url") or match.get("applyUrl") or "")
            role, company = str(match.get("role") or ""), str(match.get("company") or "")
            if not url or not role_key(role):
                continue
            skills = [
                str(s)
                for s in [
                    *(match.get("matched_skills") or match.get("matchedSkills") or []),
                    *(match.get("missing_skills") or match.get("missingSkills") or []),
                ]
            ]
            items = [("role", role_key(role), role_label(role))]
            items += [("skill", skill_key(s), s) for s in skills if skill_key(s)]
            has_company = bool(company_key(company)) and company != "Company not listed"
            if has_company:
                items.append(("company", company_key(company), company))
            ids = await self._nodes(items)
            role_id = ids[("role", role_key(role))]
            triples: list[EdgeRef] = [
                (role_id, ids[("skill", skill_key(s))], "role_skill")
                for s in skills
                if skill_key(s)
            ]
            if has_company:
                triples.append((ids[("company", company_key(company))], role_id, "hires_for"))
            posting = hashlib.sha256(url.encode()).hexdigest()
            await self._evidence(await self._edges(triples), posting=posting)
            recorded += 1
        await self.session.flush()
        return recorded

    # ── Reads (public edges only) ───────────────────────────────────────────

    def _public_edges(self) -> Any:
        """Edges with enough backing to show anyone, plus their support counts."""
        support = (
            select(
                KgEvidence.edge_id,
                func.count(distinct(KgEvidence.user_id)).label("users"),
                func.count(KgEvidence.posting_key).label("postings"),
            )
            .group_by(KgEvidence.edge_id)
            .subquery()
        )
        return (
            select(
                KgEdge.id,
                KgEdge.src_id,
                KgEdge.dst_id,
                KgEdge.relation,
                support.c.users,
                support.c.postings,
            )
            .join(support, support.c.edge_id == KgEdge.id)
            .where(or_(support.c.users >= self.min_users, support.c.postings >= 1))
            .subquery("public_edges")
        )

    async def node(self, kind: str, key: str) -> GraphNode | None:
        """A node by key — only if it has at least one public edge (no private-only nodes)."""
        pe = self._public_edges()
        row = (
            await self.session.execute(
                select(KgNode).where(
                    KgNode.kind == kind,
                    KgNode.key == key,
                    exists().where(or_(pe.c.src_id == KgNode.id, pe.c.dst_id == KgNode.id)),
                )
            )
        ).scalar_one_or_none()
        return _node(row) if row else None

    async def _node_id(self, kind: str, key: str) -> uuid.UUID | None:
        result = await self.session.execute(
            select(KgNode.id).where(KgNode.kind == kind, KgNode.key == key)
        )
        return result.scalar_one_or_none()

    async def neighbours(
        self,
        node_ids: Sequence[uuid.UUID],
        relation: str,
        direction: Literal["out", "in", "both"],
        *,
        limit: int = 8,
        exclude: Iterable[uuid.UUID] = (),
    ) -> list[Neighbour]:
        """Public neighbours of one or more nodes; support is summed when several share one."""
        if not node_ids:
            return []
        pe = self._public_edges()
        other = aliased(KgNode)
        queries: list[Select[Any]] = []
        if direction in ("out", "both"):
            queries.append(
                select(other, pe.c.users, pe.c.postings)
                .join(pe, pe.c.dst_id == other.id)
                .where(pe.c.src_id.in_(node_ids), pe.c.relation == relation)
            )
        if direction in ("in", "both"):
            queries.append(
                select(other, pe.c.users, pe.c.postings)
                .join(pe, pe.c.src_id == other.id)
                .where(pe.c.dst_id.in_(node_ids), pe.c.relation == relation)
            )
        excluded = set(exclude) | set(node_ids)
        merged: dict[uuid.UUID, tuple[KgNode, int, int]] = {}
        for query in queries:
            for node, users, postings in (await self.session.execute(query)).all():
                if node.id in excluded:
                    continue
                # A user count below the threshold is never shown (even on an edge a posting
                # made public): "1 user" could point at one person.
                shown = int(users) if int(users) >= self.min_users else 0
                _, u, p = merged.get(node.id, (node, 0, 0))
                merged[node.id] = (node, u + shown, p + int(postings))
        ranked = sorted(merged.values(), key=lambda row: (-(row[1] + row[2]), row[0].label))
        return [
            Neighbour(node=_node(n), relation=relation, direction=direction, users=u, postings=p)
            for n, u, p in ranked[:limit]
        ]

    async def node_neighbourhood(self, kind: str, key: str) -> dict[str, list[Neighbour]]:
        node_id = await self._node_id(kind, key)
        if node_id is None:
            return {}
        ids = [node_id]
        if kind == "skill":
            return {
                "roles": await self.neighbours(ids, "role_skill", "in"),
                "pairs_with": await self.neighbours(ids, "skill_pair", "both"),
            }
        if kind == "company":
            return {"hires_for": await self.neighbours(ids, "hires_for", "out")}
        return {
            "skills": await self.neighbours(ids, "role_skill", "out", limit=12),
            "companies": await self.neighbours(ids, "hires_for", "in"),
            "next_roles": await self.neighbours(ids, "leads_to", "out"),
            "previous_roles": await self.neighbours(ids, "leads_to", "in"),
        }

    async def search(self, query: str, kind: str | None = None, limit: int = 10) -> list[GraphNode]:
        text = query.strip().lower()
        if not text:
            return []
        pe = self._public_edges()
        statement = (
            select(KgNode)
            .where(
                KgNode.key.contains(text, autoescape=True),
                exists().where(or_(pe.c.src_id == KgNode.id, pe.c.dst_id == KgNode.id)),
            )
            .order_by(func.length(KgNode.key), KgNode.key)
            .limit(limit)
        )
        if kind:
            statement = statement.where(KgNode.kind == kind)
        return [_node(row) for row in (await self.session.execute(statement)).scalars().all()]

    async def paths(
        self, role: str, *, max_depth: int = 3, limit: int = 15
    ) -> list[list[GraphNode]]:
        """Career paths from a role along public leads_to edges (recursive CTE, no cycles)."""
        start = await self._node_id("role", role_key(role))
        if start is None:
            return []
        pe = self._public_edges()
        leads = select(pe.c.src_id, pe.c.dst_id).where(pe.c.relation == "leads_to").cte("leads")
        sep = literal(",")
        walk = (
            select(
                leads.c.dst_id.label("node_id"),
                literal(1).label("depth"),
                # Text on both sides: Postgres needs one type across the recursive union.
                cast(cast(leads.c.src_id, String) + sep + cast(leads.c.dst_id, String), Text).label(
                    "trail"
                ),
            )
            .where(leads.c.src_id == start)
            .cte("walk", recursive=True)
        )
        step = aliased(leads)
        walk = walk.union_all(
            select(
                step.c.dst_id,
                walk.c.depth + 1,
                cast(walk.c.trail + sep + cast(step.c.dst_id, String), Text),
            ).where(
                and_(
                    step.c.src_id == walk.c.node_id,
                    walk.c.depth < max_depth,
                    ~walk.c.trail.contains(cast(step.c.dst_id, String)),
                )
            )
        )
        rows = (
            await self.session.execute(
                select(walk.c.trail, walk.c.depth).order_by(walk.c.depth.desc()).limit(200)
            )
        ).all()
        trails = [[uuid.UUID(part) for part in str(trail).split(",")] for trail, _ in rows]
        # Keep maximal paths only (drop a path that is the prefix of a longer one).
        keys = {tuple(t) for t in trails}
        maximal = [
            t for t in trails if not any(len(o) > len(t) and o[: len(t)] == tuple(t) for o in keys)
        ]
        node_ids = {node_id for trail in maximal for node_id in trail}
        nodes = {
            row.id: _node(row)
            for row in (
                await self.session.execute(select(KgNode).where(KgNode.id.in_(node_ids)))
            ).scalars()
        }
        return [[nodes[n] for n in trail] for trail in maximal[:limit]]

    async def user_links(self, user_id: uuid.UUID) -> list[tuple[uuid.UUID, UserLink]]:
        rows = (
            await self.session.execute(
                select(KgUserLink.relation, KgNode)
                .join(KgNode, KgNode.id == KgUserLink.node_id)
                .where(KgUserLink.user_id == user_id)
                .order_by(KgUserLink.relation, KgNode.label)
            )
        ).all()
        return [(node.id, UserLink(relation=relation, node=_node(node))) for relation, node in rows]

    async def insights(self, user_id: uuid.UUID) -> UserInsights:
        """Shared knowledge around this user's own (private) links."""
        links = await self.user_links(user_id)
        skill_ids = [node_id for node_id, link in links if link.relation == "has_skill"]
        have = {link.node.key for _, link in links if link.relation == "has_skill"}
        role_links = [(i, link) for i, link in links if link.relation == "targets_role"][:3]

        roles: list[RoleInsight] = []
        for role_id, link in role_links:
            skills = await self.neighbours([role_id], "role_skill", "out", limit=10)
            roles.append(
                RoleInsight(
                    role=link.node,
                    skills=[replace(n, yours=n.node.key in have) for n in skills],
                    companies=await self.neighbours([role_id], "hires_for", "in", limit=5),
                    next_roles=await self.neighbours([role_id], "leads_to", "out", limit=5),
                )
            )
        adjacent = await self.neighbours(skill_ids, "skill_pair", "both", limit=6)
        return UserInsights(
            links=[link for _, link in links], roles=roles, adjacent_skills=adjacent
        )

    async def has_links(self, user_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(KgUserLink.node_id).where(KgUserLink.user_id == user_id).limit(1)
        )
        return result.first() is not None
