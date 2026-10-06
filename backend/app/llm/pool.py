"""The key pool: every (key, model) pair the gateway may rotate across."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Tier = Literal["large", "fast"]


@dataclass(frozen=True)
class PoolEntry:
    id: str  # "groq-1-large" — safe to log
    base_url: str
    model: str
    tier: Tier
    api_key: str = field(repr=False)  # never printed, logged or returned by an endpoint


def build_pool(
    api_keys: list[str], *, base_url: str, large_model: str, fast_model: str
) -> list[PoolEntry]:
    """Every key serves both tiers; agents ask for a tier, the gateway picks the key."""
    pool: list[PoolEntry] = []
    for index, key in enumerate(api_keys, start=1):
        pool.append(PoolEntry(f"groq-{index}-large", base_url, large_model, "large", key))
        pool.append(PoolEntry(f"groq-{index}-fast", base_url, fast_model, "fast", key))
    return pool
