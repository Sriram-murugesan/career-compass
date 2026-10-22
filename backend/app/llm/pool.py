"""The key pool: every (provider, key, model) entry the gateway may rotate across.

Any OpenAI-compatible provider works (Groq, OpenRouter, …): each entry carries
its own base URL, key, model and extra headers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import zip_longest
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from app.core.config import Settings

Tier = Literal["large", "fast"]


@dataclass(frozen=True)
class PoolEntry:
    id: str  # "groq-1-large", "openrouter-2-fast" — safe to log
    provider: str
    base_url: str
    model: str
    tier: Tier
    api_key: str = field(repr=False)  # never printed, logged or returned by an endpoint
    extra_headers: dict[str, str] = field(default_factory=dict, compare=False)


@dataclass(frozen=True)
class ProviderConfig:
    name: str  # "groq" | "openrouter"
    base_url: str
    api_keys: list[str] = field(repr=False)
    large_model: str
    fast_model: str
    extra_headers: dict[str, str] = field(default_factory=dict)


def providers_from_settings(settings: Settings) -> list[ProviderConfig]:
    """Every provider that has at least one key in backend/.env."""
    openrouter_headers = {"X-Title": settings.openrouter_app_name}
    if settings.openrouter_site_url:
        openrouter_headers["HTTP-Referer"] = settings.openrouter_site_url

    providers = [
        ProviderConfig(
            name="groq",
            base_url=settings.groq_base_url,
            api_keys=[key.get_secret_value() for key in settings.groq_api_keys],
            large_model=settings.llm_model_large,
            fast_model=settings.llm_model_fast,
        ),
        ProviderConfig(
            name="openrouter",
            base_url=settings.openrouter_base_url,
            api_keys=[key.get_secret_value() for key in settings.openrouter_api_keys],
            large_model=settings.openrouter_model_large,
            fast_model=settings.openrouter_model_fast,
            extra_headers=openrouter_headers,
        ),
    ]
    return [provider for provider in providers if provider.api_keys]


def build_pool(providers: list[ProviderConfig]) -> list[PoolEntry]:
    """Every key serves both tiers; agents ask for a tier, the gateway picks the key.

    Providers are interleaved key by key (groq-1, openrouter-1, groq-2, …), so
    round-robin rotation alternates providers and a provider outage costs at
    most one failed attempt before the next call lands elsewhere.
    """
    per_provider = [
        [(provider, index, key) for index, key in enumerate(provider.api_keys, start=1)]
        for provider in providers
    ]
    pool: list[PoolEntry] = []
    for row in zip_longest(*per_provider):
        for item in row:
            if item is None:
                continue
            provider, index, key = item
            tiers: tuple[tuple[Tier, str], ...] = (
                ("large", provider.large_model),
                ("fast", provider.fast_model),
            )
            for tier, model in tiers:
                pool.append(
                    PoolEntry(
                        id=f"{provider.name}-{index}-{tier}",
                        provider=provider.name,
                        base_url=provider.base_url.rstrip("/"),
                        model=model,
                        tier=tier,
                        api_key=key,
                        extra_headers=dict(provider.extra_headers),
                    )
                )
    return pool
