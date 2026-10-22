"""Shared career knowledge graph: one set of nodes and edges for every user.

    kg_nodes        skill | role | company — shared, one row per normalised key
    kg_edges        typed relation between two nodes (see Relation)
    kg_evidence     who backs an edge: a user (user_id) or a real job posting (posting_key).
                    Support is COUNTED from here, so removing a user's evidence (profile
                    change, account deletion → cascade) removes their contribution exactly.
    kg_user_links   a user's own links (has_skill, targets_role, current_role). PRIVATE:
                    only ever read for that user.

Other users see an edge only when it is backed by >= GRAPH_MIN_USERS distinct users or by
at least one posting — never one person's data.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UuidPrimaryKey, utcnow


class KgNode(UuidPrimaryKey, Base):
    __tablename__ = "kg_nodes"
    __table_args__ = (UniqueConstraint("kind", "key"),)

    kind: Mapped[str] = mapped_column(String(20))  # skill | role | company
    key: Mapped[str] = mapped_column(String(120))  # normalised, e.g. "next.js"
    label: Mapped[str] = mapped_column(String(120))  # display text, first spelling seen
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KgEdge(UuidPrimaryKey, Base):
    __tablename__ = "kg_edges"
    __table_args__ = (
        UniqueConstraint("src_id", "dst_id", "relation"),
        Index("ix_kg_edges_dst_relation", "dst_id", "relation"),
    )

    src_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("kg_nodes.id", ondelete="CASCADE"), index=True
    )
    dst_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("kg_nodes.id", ondelete="CASCADE"))
    # role_skill (role → skill) · skill_pair (skill → skill, src key < dst key)
    # leads_to (role → role) · hires_for (company → role)
    relation: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KgEvidence(UuidPrimaryKey, Base):
    __tablename__ = "kg_evidence"
    __table_args__ = (
        UniqueConstraint("edge_id", "user_id"),
        UniqueConstraint("edge_id", "posting_key", name="uq_kg_evidence_edge_id_posting_key"),
    )

    edge_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("kg_edges.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    posting_key: Mapped[str | None] = mapped_column(String(64), nullable=True)  # sha256(url)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class KgUserLink(Base):
    __tablename__ = "kg_user_links"
    __table_args__ = (PrimaryKeyConstraint("user_id", "node_id", "relation"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    node_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("kg_nodes.id", ondelete="CASCADE"))
    relation: Mapped[str] = mapped_column(String(30))  # has_skill | targets_role | current_role
