"""Small sliding-window rate limiter for sensitive endpoints (sign-in, sign-up…).

In-process memory is correct for a single API instance (a modular monolith).
When the API runs as several instances, swap the storage for Redis.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from app.core.errors import RateLimited


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0) -> None:
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            raise RateLimited("Too many requests — try again shortly")
        hits.append(now)
