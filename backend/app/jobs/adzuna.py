"""Adzuna job search (https://developer.adzuna.com).

GET https://api.adzuna.com/v1/api/jobs/{country}/search/{page}
    ?app_id=…&app_key=…&what=<keywords>&where=<location>&results_per_page=N

Results carry: id, title, description (snippet), created, redirect_url,
company.display_name, location.display_name, salary_min, salary_max,
salary_is_predicted, contract_time.

The app key travels in the query string, so request URLs are never logged and
error messages never include them.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.agents.base import JobBoardUnavailable, JobListing
from app.jobs.text import clean_html

logger = logging.getLogger("app.jobs")

BASE_URL = "https://api.adzuna.com/v1/api/jobs"
_CURRENCY = {"in": "₹", "gb": "£", "us": "$", "ca": "CA$", "au": "A$", "nz": "NZ$"}
_EURO_COUNTRIES = {"de", "fr", "at", "nl", "it", "es", "be"}


class AdzunaJobBoard:
    name = "adzuna"

    def __init__(
        self,
        *,
        app_id: str,
        app_key: str,
        country: str = "in",
        cache_ttl_seconds: float = 600.0,
        timeout_seconds: float = 15.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._app_id = app_id
        self._app_key = app_key
        self.country = country.lower()
        self._ttl = cache_ttl_seconds
        # Same search within the TTL → no second request (saves the free-tier quota).
        self._cache: dict[tuple[str, str, int], tuple[float, list[JobListing]]] = {}
        self._client = httpx.AsyncClient(timeout=timeout_seconds, transport=transport)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def search(self, query: str, location: str, *, limit: int = 10) -> list[JobListing]:
        key = (query.strip().lower(), location.strip().lower(), limit)
        cached = self._cache.get(key)
        if cached and time.monotonic() - cached[0] < self._ttl:
            return cached[1]

        params: dict[str, str | int] = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "what": query,
            "results_per_page": max(1, min(limit, 50)),
            "content-type": "application/json",
        }
        if location.strip():
            params["where"] = location.strip()

        started = time.perf_counter()
        try:
            response = await self._client.get(f"{BASE_URL}/{self.country}/search/1", params=params)
        except httpx.HTTPError as exc:
            raise JobBoardUnavailable(f"Adzuna unreachable ({type(exc).__name__})") from None
        if response.status_code != 200:
            # Never include response.url: it contains the app key.
            raise JobBoardUnavailable(f"Adzuna returned HTTP {response.status_code}")

        try:
            results = response.json().get("results", [])
        except ValueError:
            raise JobBoardUnavailable("Adzuna returned an unreadable response") from None
        listings = [self._to_listing(item) for item in results if isinstance(item, dict)]
        listings = [listing for listing in listings if listing.apply_url]
        logger.info(
            "job search ok",
            extra={
                "context": {
                    "provider": "adzuna",
                    "country": self.country,
                    "query": query,
                    "location": location,
                    "results": len(listings),
                    "latencyMs": round((time.perf_counter() - started) * 1000),
                }
            },
        )
        self._cache[key] = (time.monotonic(), listings)
        return listings

    def _to_listing(self, item: dict[str, Any]) -> JobListing:
        company = (item.get("company") or {}).get("display_name") or "Company not listed"
        location = (item.get("location") or {}).get("display_name") or ""
        return JobListing(
            id=str(item.get("id", "")),
            title=clean_html(item.get("title")) or "Untitled role",
            company=str(company),
            location=str(location),
            description=clean_html(item.get("description"), 500),
            apply_url=str(item.get("redirect_url") or ""),
            posted_at=item.get("created"),
            salary=self._salary(item),
            contract=item.get("contract_time"),
            source="adzuna",
        )

    def _salary(self, item: dict[str, Any]) -> str | None:
        low, high = item.get("salary_min"), item.get("salary_max")
        if not isinstance(low, int | float) and not isinstance(high, int | float):
            return None
        symbol = "€" if self.country in _EURO_COUNTRIES else _CURRENCY.get(self.country, "")
        values = [f"{symbol}{round(v):,}" for v in (low, high) if isinstance(v, int | float)]
        text = " - ".join(dict.fromkeys(values))  # min == max → show once
        # Adzuna estimates salary when the ad doesn't state one.
        return f"{text} (estimated)" if str(item.get("salary_is_predicted")) == "1" else text
