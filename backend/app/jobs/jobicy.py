"""Jobicy remote-jobs API (https://jobicy.com/jobs-rss-feed) — free, no API key.

GET https://jobicy.com/api/v2/remote-jobs?count=N&tag=<keywords>

Jobs carry: id, url, jobTitle, companyName, jobGeo, jobType[], pubDate,
jobExcerpt, and optionally annualSalaryMin/annualSalaryMax/salaryCurrency.

Terms: credit Jobicy and send applicants to the job URL from the feed — the apply
link IS that URL and every card shows "via jobicy".
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.agents.base import JobBoardUnavailable, JobListing
from app.jobs.text import clean_html

logger = logging.getLogger("app.jobs")

API_URL = "https://jobicy.com/api/v2/remote-jobs"
USER_AGENT = "CareerCompass/1.0 (job search assistant)"


class JobicyJobBoard:
    name = "jobicy"

    def __init__(
        self,
        *,
        cache_ttl_seconds: float = 1800.0,
        timeout_seconds: float = 15.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._ttl = cache_ttl_seconds
        self._cache: dict[tuple[str, int], tuple[float, list[JobListing]]] = {}
        self._client = httpx.AsyncClient(
            timeout=timeout_seconds, transport=transport, headers={"User-Agent": USER_AGENT}
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def search(self, query: str, location: str, *, limit: int = 10) -> list[JobListing]:
        # Every Jobicy job is remote and its geo filter only takes fixed region slugs, so
        # location isn't sent; each listing's region is shown and the ranker weighs it.
        key = (query.strip().lower(), limit)
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < self._ttl:
            return cached[1]

        params: dict[str, str | int] = {"count": max(1, min(limit, 50))}
        if query.strip():
            params["tag"] = query.strip()

        started = time.perf_counter()
        try:
            response = await self._client.get(API_URL, params=params)
        except httpx.HTTPError as exc:
            raise JobBoardUnavailable(f"Jobicy unreachable ({type(exc).__name__})") from None
        if response.status_code != 200:
            raise JobBoardUnavailable(f"Jobicy returned HTTP {response.status_code}")
        try:
            jobs = response.json().get("jobs", [])
        except ValueError:
            raise JobBoardUnavailable("Jobicy returned an unreadable response") from None

        listings = [_to_listing(item) for item in jobs if isinstance(item, dict)]
        listings = [listing for listing in listings if listing.apply_url]
        logger.info(
            "job search ok",
            extra={
                "context": {
                    "provider": "jobicy",
                    "query": query,
                    "results": len(listings),
                    "latencyMs": round((time.perf_counter() - started) * 1000),
                }
            },
        )
        self._cache[key] = (time.monotonic(), listings)
        return listings


def _to_listing(item: dict[str, Any]) -> JobListing:
    geo = clean_html(item.get("jobGeo"))
    job_type = item.get("jobType")
    return JobListing(
        id=f"jobicy-{item.get('id', '')}",
        title=clean_html(item.get("jobTitle")) or "Untitled role",
        company=clean_html(item.get("companyName")) or "Company not listed",
        location=f"Remote · {geo}" if geo else "Remote",
        description=clean_html(item.get("jobExcerpt") or item.get("jobDescription"), 500),
        apply_url=str(item.get("url") or ""),
        posted_at=item.get("pubDate"),
        salary=_salary(item),
        contract=", ".join(map(str, job_type)) if isinstance(job_type, list) and job_type else None,
        source="jobicy",
    )


def _salary(item: dict[str, Any]) -> str | None:
    low, high = item.get("annualSalaryMin"), item.get("annualSalaryMax")
    values = [f"{round(float(v)):,}" for v in (low, high) if isinstance(v, int | float)]
    if not values:
        return None
    currency = str(item.get("salaryCurrency") or "").strip()
    text = " - ".join(dict.fromkeys(values))  # min == max → show once
    return f"{currency} {text} / year".strip()
