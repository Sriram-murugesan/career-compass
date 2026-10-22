"""Fan one search out to several job boards and merge the results.

One board failing doesn't fail the search; only all of them failing does. Results are
interleaved (board A #1, board B #1, A #2, …) so no single source crowds out the rest,
and the same role at the same company is kept once.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from itertools import zip_longest
from typing import Protocol

from app.agents.base import JobBoardUnavailable, JobListing

logger = logging.getLogger("app.jobs")


class ClosableJobBoard(Protocol):
    name: str

    async def search(self, query: str, location: str, *, limit: int = 10) -> list[JobListing]: ...

    async def aclose(self) -> None: ...


class MultiJobBoard:
    def __init__(self, boards: Sequence[ClosableJobBoard]) -> None:
        self.boards = list(boards)
        self.name = "+".join(board.name for board in self.boards)

    async def aclose(self) -> None:
        for board in self.boards:
            await board.aclose()

    async def search(self, query: str, location: str, *, limit: int = 10) -> list[JobListing]:
        results = await asyncio.gather(
            *(board.search(query, location, limit=limit) for board in self.boards),
            return_exceptions=True,
        )
        batches: list[list[JobListing]] = []
        for board, result in zip(self.boards, results, strict=True):
            if isinstance(result, JobBoardUnavailable):
                logger.warning(
                    "job board unavailable",
                    extra={"context": {"provider": board.name, "error": str(result)}},
                )
            elif isinstance(result, BaseException):
                raise result
            else:
                batches.append(result)
        if not batches:
            raise JobBoardUnavailable("Every job board is unavailable")

        merged: list[JobListing] = []
        seen: set[tuple[str, str]] = set()
        for row in zip_longest(*batches):
            for job in row:
                if job is None:
                    continue
                key = (job.title.casefold(), job.company.casefold())
                if key not in seen:
                    seen.add(key)
                    merged.append(job)
        return merged[:limit]
