"""Remotive remote-jobs API (https://remotive.com/api-documentation) — free, no API key.

GET https://remotive.com/api/remote-jobs

The public feed is small, delayed by 24 h, ignores its `search` parameter, and Remotive
asks clients to fetch it at most ~4 times a day. So the whole feed is fetched once,
cached for 6 h, and every search filters it locally by keyword.

Jobs carry: id, url, title, company_name, category, tags[], job_type,
publication_date, candidate_required_location, salary, description.

Terms: link back to the Remotive URL and name Remotive as the source — the apply link
IS that URL and every card shows "via remotive".
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

import httpx

from app.agents.base import JobBoardUnavailable, JobListing
from app.jobs.text import clean_html

logger = logging.getLogger("app.jobs")

API_URL = "https://remotive.com/api/remote-jobs"
USER_AGENT = "CareerCompass/1.0 (job search assistant)"
_WORD = re.compile(r"[a-z0-9+#.]+")

# (listing, words in its title, words in its tags + category)
_Indexed = tuple[JobListing, set[str], set[str]]


def _words(text: str) -> set[str]:
    words = (word.strip(".") for word in _WORD.findall(text.lower()))
    return {word for word in words if len(word) > 1}


class RemotiveJobBoard:
    name = "remotive"

    def __init__(
        self,
        *,
        cache_ttl_seconds: float = 6 * 3600.0,
        timeout_seconds: float = 20.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._ttl = cache_ttl_seconds
        self._feed: tuple[float, list[_Indexed]] | None = None
        self._lock = asyncio.Lock()  # parallel searches share one fetch
        self._client = httpx.AsyncClient(
            timeout=timeout_seconds, transport=transport, headers={"User-Agent": USER_AGENT}
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def search(self, query: str, location: str, *, limit: int = 10) -> list[JobListing]:
        feed = await self._load()
        wanted = _words(query)
        scored: list[tuple[int, int, JobListing]] = []
        for position, (listing, title_words, tag_words) in enumerate(feed):
            score = 2 * len(wanted & title_words) + len(wanted & tag_words)
            if score:
                scored.append((-score, position, listing))  # best match first, then feed order
        scored.sort(key=lambda row: (row[0], row[1]))
        return [listing for _, _, listing in scored[:limit]]

    async def _load(self) -> list[_Indexed]:
        async with self._lock:
            if self._feed and time.monotonic() - self._feed[0] < self._ttl:
                return self._feed[1]
            started = time.perf_counter()
            try:
                response = await self._client.get(API_URL)
            except httpx.HTTPError as exc:
                raise JobBoardUnavailable(f"Remotive unreachable ({type(exc).__name__})") from None
            if response.status_code != 200:
                raise JobBoardUnavailable(f"Remotive returned HTTP {response.status_code}")
            try:
                jobs = response.json().get("jobs", [])
            except ValueError:
                raise JobBoardUnavailable("Remotive returned an unreadable response") from None

            feed: list[_Indexed] = []
            for item in jobs:
                if not isinstance(item, dict) or not item.get("url"):
                    continue
                listing = _to_listing(item)
                tags = " ".join(str(tag) for tag in item.get("tags") or [])
                feed.append(
                    (listing, _words(listing.title), _words(f"{tags} {item.get('category', '')}"))
                )
            logger.info(
                "job feed refreshed",
                extra={
                    "context": {
                        "provider": "remotive",
                        "results": len(feed),
                        "latencyMs": round((time.perf_counter() - started) * 1000),
                    }
                },
            )
            self._feed = (time.monotonic(), feed)
            return feed


def _to_listing(item: dict[str, Any]) -> JobListing:
    region = clean_html(item.get("candidate_required_location"))
    job_type = str(item.get("job_type") or "").replace("_", " ")
    return JobListing(
        id=f"remotive-{item.get('id', '')}",
        title=clean_html(item.get("title")) or "Untitled role",
        company=clean_html(item.get("company_name")) or "Company not listed",
        location=f"Remote · {region}" if region else "Remote",
        description=clean_html(item.get("description"), 500),
        apply_url=str(item.get("url")),
        posted_at=item.get("publication_date"),
        salary=clean_html(item.get("salary")) or None,
        contract=job_type or None,
        source="remotive",
    )
