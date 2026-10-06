"""Round-robin LLM gateway with failover.

Every agent calls the LLM through this one object. It rotates across all
pool entries of the requested tier and routes around trouble:

    event            action
    200              success; failure count reset
    429              cool the entry for Retry-After (else 2s doubling, max 60s); try the next
    5xx / timeout    try the next; 3 failures in a row → circuit open for 30s
    401 / 403        disable that key until restart; try the next
    other 4xx        LlmBadRequest — the request is wrong, retrying won't help
    all exhausted    LlmUnavailable — agents fall back to a non-LLM answer

The rotation pointer and health live in process memory: correct for one API
instance (a modular monolith). Several instances → move them to Redis.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.llm.errors import LlmBadOutput, LlmBadRequest, LlmUnavailable
from app.llm.pool import PoolEntry, Tier

logger = logging.getLogger("app.llm")

M = TypeVar("M", bound=BaseModel)

MAX_COOLDOWN_SECONDS = 60.0
CIRCUIT_OPEN_SECONDS = 30.0
CIRCUIT_FAILURE_THRESHOLD = 3


@dataclass
class EntryHealth:
    cooldown_until: float = 0.0
    consecutive_failures: int = 0
    rate_limit_streak: int = 0
    disabled: bool = False


class LlmGateway:
    def __init__(
        self,
        pool: list[PoolEntry],
        *,
        timeout_seconds: float = 30.0,
        transport: httpx.AsyncBaseTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._pool = pool
        self._health = {entry.id: EntryHealth() for entry in pool}
        self._cursor: dict[str, int] = {"large": 0, "fast": 0}
        self._lock = asyncio.Lock()
        self._clock = clock
        self._client = httpx.AsyncClient(timeout=timeout_seconds, transport=transport)

    @property
    def available(self) -> bool:
        return bool(self._pool)

    async def aclose(self) -> None:
        await self._client.aclose()

    def status(self) -> list[dict[str, Any]]:
        """Pool health for /api/health — ids and state only, never keys."""
        now = self._clock()
        return [
            {
                "id": entry.id,
                "model": entry.model,
                "healthy": not self._health[entry.id].disabled
                and self._health[entry.id].cooldown_until <= now,
            }
            for entry in self._pool
        ]

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        tier: Tier = "large",
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> str:
        """One chat completion, served by the next healthy entry in round-robin order."""
        for entry in await self._rotation(tier):
            health = self._health[entry.id]
            if health.disabled or health.cooldown_until > self._clock():
                continue

            payload: dict[str, Any] = {
                "model": entry.model,
                "messages": messages,
                "temperature": temperature,
            }
            if json_mode:
                payload["response_format"] = {"type": "json_object"}

            started = time.perf_counter()
            try:
                response = await self._client.post(
                    f"{entry.base_url}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {entry.api_key}"},
                )
            except httpx.HTTPError as exc:
                self._record_failure(entry, f"transport error: {type(exc).__name__}")
                continue

            latency_ms = round((time.perf_counter() - started) * 1000)
            status = response.status_code
            if status == 200:
                health.consecutive_failures = 0
                health.rate_limit_streak = 0
                body = response.json()
                usage = body.get("usage") or {}
                logger.info(
                    "llm call ok",
                    extra={
                        "context": {
                            "entry": entry.id,
                            "model": entry.model,
                            "latencyMs": latency_ms,
                            "promptTokens": usage.get("prompt_tokens"),
                            "completionTokens": usage.get("completion_tokens"),
                        }
                    },
                )
                return str(body["choices"][0]["message"]["content"])
            if status == 429:
                self._cool_down(entry, response.headers.get("retry-after"))
                continue
            if status in (401, 403):
                health.disabled = True
                logger.warning(
                    "llm key rejected - disabled", extra={"context": {"entry": entry.id}}
                )
                continue
            if 400 <= status < 500:
                raise LlmBadRequest(f"Provider rejected the request ({status}) on {entry.id}")
            self._record_failure(entry, f"HTTP {status}")

        raise LlmUnavailable(f"No healthy LLM entry for tier '{tier}'")

    async def complete_json(
        self, *, system: str, user: str, schema: type[M], tier: Tier = "large"
    ) -> M:
        """Ask for JSON matching `schema`; validate it. One retry (on the next key) if invalid."""
        schema_json = json.dumps(schema.model_json_schema())
        instructions = f"Respond with JSON only, matching this JSON Schema:\n{schema_json}"
        messages = [
            {"role": "system", "content": f"{system}\n\n{instructions}"},
            {"role": "user", "content": user},
        ]
        last_error: Exception | None = None
        for _ in range(2):
            content = await self.complete(messages, tier=tier, json_mode=True)
            try:
                return schema.model_validate_json(content)
            except ValidationError as exc:
                last_error = exc
                logger.warning("llm returned invalid JSON for %s - retrying", schema.__name__)
        raise LlmBadOutput(f"Model output did not match {schema.__name__}") from last_error

    async def _rotation(self, tier: Tier) -> list[PoolEntry]:
        entries = [entry for entry in self._pool if entry.tier == tier]
        if not entries:
            raise LlmUnavailable("No LLM keys configured (set GROQ_API_KEYS in backend/.env)")
        async with self._lock:
            start = self._cursor[tier] % len(entries)
            self._cursor[tier] = start + 1
        return entries[start:] + entries[:start]

    def _cool_down(self, entry: PoolEntry, retry_after: str | None) -> None:
        health = self._health[entry.id]
        health.rate_limit_streak += 1
        try:
            seconds = float(retry_after) if retry_after else 0.0
        except ValueError:
            seconds = 0.0
        if seconds <= 0:
            seconds = 2.0**health.rate_limit_streak
        health.cooldown_until = self._clock() + min(seconds, MAX_COOLDOWN_SECONDS)
        logger.warning(
            "llm rate limited - cooling down",
            extra={"context": {"entry": entry.id, "seconds": min(seconds, MAX_COOLDOWN_SECONDS)}},
        )

    def _record_failure(self, entry: PoolEntry, reason: str) -> None:
        health = self._health[entry.id]
        health.consecutive_failures += 1
        if health.consecutive_failures >= CIRCUIT_FAILURE_THRESHOLD:
            health.cooldown_until = self._clock() + CIRCUIT_OPEN_SECONDS
            health.consecutive_failures = 0
            logger.warning(
                "llm circuit open", extra={"context": {"entry": entry.id, "reason": reason}}
            )
        else:
            logger.warning(
                "llm call failed", extra={"context": {"entry": entry.id, "reason": reason}}
            )
