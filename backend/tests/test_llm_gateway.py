"""Round-robin gateway: rotation, cooldown on 429, key disabling, circuit breaker."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from pydantic import BaseModel

from app.llm.errors import LlmBadOutput, LlmBadRequest, LlmUnavailable
from app.llm.gateway import LlmGateway
from app.llm.pool import ProviderConfig, build_pool, providers_from_settings
from tests.conftest import make_settings


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def completion(content: str) -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 5}},
    )


def make_gateway(
    handler: httpx.MockTransport, keys: list[str], clock: FakeClock | None = None
) -> LlmGateway:
    provider = ProviderConfig(
        name="groq",
        base_url="https://llm.test/v1",
        api_keys=keys,
        large_model="big",
        fast_model="small",
    )
    return LlmGateway(build_pool([provider]), transport=handler, clock=clock or FakeClock())


def key_of(request: httpx.Request) -> str:
    return request.headers["authorization"].removeprefix("Bearer ")


MESSAGES = [{"role": "user", "content": "hi"}]


async def test_rotates_round_robin_across_keys() -> None:
    used: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        used.append(key_of(request))
        assert json.loads(request.content)["model"] == "big"
        return completion("ok")

    gateway = make_gateway(httpx.MockTransport(handler), ["k1", "k2", "k3"])
    for _ in range(6):
        assert await gateway.complete(MESSAGES) == "ok"
    assert used == ["k1", "k2", "k3", "k1", "k2", "k3"]


async def test_429_cools_the_key_and_fails_over_immediately() -> None:
    clock = FakeClock()
    used: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        used.append(key_of(request))
        if key_of(request) == "k1":
            return httpx.Response(429, headers={"retry-after": "30"})
        return completion("from k2")

    gateway = make_gateway(httpx.MockTransport(handler), ["k1", "k2"], clock)
    assert await gateway.complete(MESSAGES) == "from k2"  # k1 → 429 → k2, same call
    assert await gateway.complete(MESSAGES) == "from k2"
    assert await gateway.complete(MESSAGES) == "from k2"
    assert used == ["k1", "k2", "k2", "k2"]  # k1 skipped while cooling down

    clock.now += 31  # cooldown over: k1 is back in the rotation
    used.clear()
    await gateway.complete(MESSAGES)
    await gateway.complete(MESSAGES)
    assert "k1" in used


async def test_rejected_key_is_disabled() -> None:
    used: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        used.append(key_of(request))
        return httpx.Response(401) if key_of(request) == "bad" else completion("ok")

    gateway = make_gateway(httpx.MockTransport(handler), ["bad", "good"])
    for _ in range(4):
        await gateway.complete(MESSAGES)
    assert used.count("bad") == 1
    assert [entry["healthy"] for entry in gateway.status() if entry["id"] == "groq-1-large"] == [
        False
    ]


async def test_server_errors_open_the_circuit_then_report_unavailable() -> None:
    clock = FakeClock()
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    gateway = make_gateway(httpx.MockTransport(handler), ["k1"], clock)
    for _ in range(3):
        with pytest.raises(LlmUnavailable):
            await gateway.complete(MESSAGES)
    assert calls == 3
    with pytest.raises(LlmUnavailable):  # circuit open: no request is even sent
        await gateway.complete(MESSAGES)
    assert calls == 3

    clock.now += 31
    with pytest.raises(LlmUnavailable):
        await gateway.complete(MESSAGES)
    assert calls == 4


async def test_bad_request_is_not_retried() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(400, json={"error": "bad"})

    gateway = make_gateway(httpx.MockTransport(handler), ["k1", "k2"])
    with pytest.raises(LlmBadRequest):
        await gateway.complete(MESSAGES)
    assert calls == 1


async def test_no_keys_means_unavailable() -> None:
    gateway = make_gateway(httpx.MockTransport(lambda _: completion("x")), [])
    assert gateway.available is False
    with pytest.raises(LlmUnavailable):
        await gateway.complete(MESSAGES)


class Answer(BaseModel):
    value: int


async def test_complete_json_validates_and_retries_once() -> None:
    replies = iter(['{"value": "not a number"}', '{"value": 42}'])
    gateway = make_gateway(httpx.MockTransport(lambda _: completion(next(replies))), ["k1", "k2"])
    assert (await gateway.complete_json(system="s", user="u", schema=Answer)).value == 42

    always_bad = make_gateway(httpx.MockTransport(lambda _: completion("nope")), ["k1"])
    with pytest.raises(LlmBadOutput):
        await always_bad.complete_json(system="s", user="u", schema=Answer)


async def test_status_never_exposes_keys() -> None:
    gateway = make_gateway(httpx.MockTransport(lambda _: completion("x")), ["gsk_secret123"])
    assert "gsk_secret123" not in json.dumps(gateway.status())
    assert "gsk_secret123" not in repr(gateway._pool)


# ── Multiple providers (Groq + OpenRouter) ──────────────────────────────────

GROQ = ProviderConfig("groq", "https://groq.test/v1", ["g1", "g2"], "g-big", "g-small")
OPENROUTER = ProviderConfig(
    "openrouter",
    "https://openrouter.test/api/v1",
    ["o1"],
    "o-big",
    "o-small",
    extra_headers={"X-Title": "Career Compass"},
)


def test_providers_are_interleaved_so_rotation_alternates_them() -> None:
    large = [entry for entry in build_pool([GROQ, OPENROUTER]) if entry.tier == "large"]
    assert [e.id for e in large] == ["groq-1-large", "openrouter-1-large", "groq-2-large"]
    assert [e.model for e in large] == ["g-big", "o-big", "g-big"]


async def test_each_provider_gets_its_own_url_model_and_headers() -> None:
    seen: list[tuple[str, str, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        model = json.loads(request.content)["model"]
        seen.append((request.url.host, model, request.headers.get("x-title")))
        return completion("ok")

    gateway = LlmGateway(build_pool([GROQ, OPENROUTER]), transport=httpx.MockTransport(handler))
    for _ in range(3):
        await gateway.complete(MESSAGES)
    assert seen == [
        ("groq.test", "g-big", None),
        ("openrouter.test", "o-big", "Career Compass"),
        ("groq.test", "g-big", None),
    ]


async def test_rate_limited_provider_fails_over_to_the_other() -> None:
    hosts: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host)
        if request.url.host == "groq.test":
            return httpx.Response(429, headers={"retry-after": "60"})
        return completion("from openrouter")

    gateway = LlmGateway(build_pool([GROQ, OPENROUTER]), transport=httpx.MockTransport(handler))
    assert await gateway.complete(MESSAGES) == "from openrouter"
    assert await gateway.complete(MESSAGES) == "from openrouter"
    assert hosts.count("openrouter.test") == 2


def test_providers_from_settings_only_includes_providers_with_keys(tmp_path: Path) -> None:
    only_openrouter = make_settings(
        tmp_path,
        openrouter_api_keys="sk-or-v1-aaa,sk-or-v1-bbb",
        openrouter_site_url="https://careercompass.test",
    )
    [provider] = providers_from_settings(only_openrouter)
    assert provider.name == "openrouter"
    assert provider.api_keys == ["sk-or-v1-aaa", "sk-or-v1-bbb"]
    assert provider.extra_headers == {
        "X-Title": "Career Compass",
        "HTTP-Referer": "https://careercompass.test",
    }
    both = make_settings(tmp_path, groq_api_keys="gsk_a", openrouter_api_keys="sk-or-v1-a")
    assert [p.name for p in providers_from_settings(both)] == ["groq", "openrouter"]
    assert providers_from_settings(make_settings(tmp_path)) == []
