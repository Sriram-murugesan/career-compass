"""app/endpoints.py must list exactly the routes the app serves — no more, no less."""

from __future__ import annotations

from app.endpoints import ENDPOINTS
from tests.conftest import Harness


async def test_endpoints_file_matches_the_running_app(harness: Harness) -> None:
    # The OpenAPI schema is the public, stable list of every route the app serves.
    paths: dict[str, dict[str, object]] = harness.app.openapi()["paths"]
    served = {(method.upper(), path) for path, operations in paths.items() for method in operations}
    declared = {(endpoint.method, endpoint.url) for endpoint in ENDPOINTS}

    assert served - declared == set(), "served but missing from app/endpoints.py"
    assert declared - served == set(), "listed in app/endpoints.py but not served"


async def test_protected_endpoints_reject_anonymous_calls(harness: Harness) -> None:
    for endpoint in ENDPOINTS:
        if endpoint.auth != "bearer":
            continue
        url = endpoint.url.replace("{conversation_id}", "00000000-0000-0000-0000-000000000000")
        response = await harness.client.request(endpoint.method, url, json={})
        assert response.status_code == 401, (endpoint.method, endpoint.url)
