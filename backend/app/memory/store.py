"""Long-term memory store.

recall(): the most relevant facts for a request. Ranking is keyword overlap
plus recency today. Phase 3 swaps it for pgvector similarity behind this same
interface, so no agent code changes.
remember(): saves new facts, deduplicated per user.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import utcnow
from app.db.session import Database
from app.memory.models import MemoryRecord

_WORD = re.compile(r"[a-z0-9]+")
_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "for",
    "of",
    "in",
    "on",
    "my",
    "me",
    "i",
    "is",
    "with",
}


@dataclass(frozen=True)
class NewMemory:
    kind: str
    content: str
    source_agent: str


class MemoryStore(Protocol):
    async def recall(self, user_id: uuid.UUID, query: str, limit: int) -> list[str]: ...
    async def remember(self, user_id: uuid.UUID, facts: list[NewMemory]) -> int: ...


def _words(text: str) -> set[str]:
    return {word for word in _WORD.findall(text.lower()) if word not in _STOPWORDS}


class SqlMemoryStore:
    def __init__(self, db: Database, *, scan_limit: int = 200) -> None:
        self.db = db
        self.scan_limit = scan_limit

    async def recall(self, user_id: uuid.UUID, query: str, limit: int) -> list[str]:
        if limit <= 0:
            return []
        async with self.db.session() as session:
            rows = (
                (
                    await session.execute(
                        select(MemoryRecord)
                        .where(MemoryRecord.user_id == user_id)
                        .order_by(MemoryRecord.created_at.desc())
                        .limit(self.scan_limit)
                    )
                )
                .scalars()
                .all()
            )
            query_words = _words(query)
            # Relevance first (shared words), then recency (rows are newest-first, sort is stable).
            ranked = sorted(rows, key=lambda r: len(query_words & _words(r.content)), reverse=True)
            chosen = ranked[:limit]
            for record in chosen:
                record.last_used_at = utcnow()
            return [record.content for record in chosen]

    async def remember(self, user_id: uuid.UUID, facts: list[NewMemory]) -> int:
        """Insert new facts; identical facts for the same user are ignored. Returns rows added."""
        async with self.db.session() as session:
            return await SessionMemoryWriter(session).remember(user_id, facts)


class SessionMemoryWriter:
    """remember() inside a session someone else owns, so the facts commit (or roll back)
    together with that unit of work, e.g. a graded mock-test attempt."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def remember(self, user_id: uuid.UUID, facts: list[NewMemory]) -> int:
        if not facts:
            return 0
        rows = [
            {
                "id": uuid.uuid4(),
                "user_id": user_id,
                "kind": fact.kind,
                "content": fact.content,
                "content_hash": hashlib.sha256(fact.content.strip().lower().encode()).hexdigest(),
                "source_agent": fact.source_agent,
                "created_at": utcnow(),
                "last_used_at": utcnow(),
            }
            for fact in facts
        ]
        is_sqlite = self.session.get_bind().dialect.name == "sqlite"
        insert = sqlite_insert if is_sqlite else pg_insert
        statement = (
            insert(MemoryRecord)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["user_id", "content_hash"])
        )
        result = await self.session.execute(statement)
        return int(result.rowcount or 0)  # type: ignore[attr-defined]
