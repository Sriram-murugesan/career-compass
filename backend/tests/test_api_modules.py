"""Profile and chat modules through the real HTTP API."""

from __future__ import annotations

from tests.conftest import Harness, parse_sse


async def test_profile_requires_auth_and_round_trips(harness: Harness) -> None:
    assert (await harness.client.get("/api/profile")).status_code == 401

    token = (await harness.sign_up(email="profile@example.com"))["token"]
    initial = await harness.client.get("/api/profile", headers=harness.auth(token))
    assert initial.status_code == 200
    assert initial.json()["data"]["targetRoles"] == []

    updated = await harness.client.patch(
        "/api/profile",
        headers=harness.auth(token),
        json={
            "headline": "Full-stack engineer",
            "targetRoles": [" Senior Frontend Engineer ", "Senior Frontend Engineer", ""],
            "skills": [{"name": "TypeScript", "category": "Technical", "level": "Expert"}],
        },
    )
    data = updated.json()["data"]
    assert data["targetRoles"] == ["Senior Frontend Engineer"]  # trimmed, deduped, blanks dropped
    assert data["skills"][0]["name"] == "TypeScript"
    assert data["aiPreferences"]["tone"] == "Professional"

    bad = await harness.client.patch(
        "/api/profile",
        headers=harness.auth(token),
        json={"skills": [{"name": "X", "level": "God"}]},
    )
    assert bad.status_code == 400


async def test_orchestrate_streams_steps_and_saves_the_conversation(harness: Harness) -> None:
    token = (await harness.sign_up(email="chat@example.com"))["token"]
    headers = harness.auth(token)
    await harness.client.patch(
        "/api/profile", headers=headers, json={"targetRoles": ["Data Engineer"]}
    )

    response = await harness.client.post(
        "/api/chat/orchestrate", headers=headers, json={"message": "find jobs for me"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(response.text)
    types = [event["type"] for event in events]
    assert types[0] == "conversation" and types[-1] == "done"
    assert {"plan", "step", "answer", "memory"} <= set(types)

    answer = next(e for e in events if e["type"] == "answer")
    assert answer["agentOutputs"]["job_search"]["matches"][0]["role"] == "Data Engineer"
    assert "matchScore" in answer["agentOutputs"]["job_search"]["matches"][0]  # camelCase out

    conversation_id = events[0]["conversationId"]
    detail = await harness.client.get(f"/api/chat/conversations/{conversation_id}", headers=headers)
    messages = detail.json()["data"]["messages"]
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[1]["payload"]["steps"][0]["agentId"] == "job_search"

    # Continue the same conversation
    again = await harness.client.post(
        "/api/chat/orchestrate",
        headers=headers,
        json={"message": "practice interview questions", "conversationId": conversation_id},
    )
    assert parse_sse(again.text)[0]["conversationId"] == conversation_id
    listed = await harness.client.get("/api/chat/conversations", headers=headers)
    assert len(listed.json()["data"]) == 1


async def test_conversations_are_private(harness: Harness) -> None:
    owner = (await harness.sign_up(email="owner@example.com"))["token"]
    stranger = (await harness.sign_up(email="stranger@example.com"))["token"]
    created = await harness.client.post(
        "/api/chat/conversations", headers=harness.auth(owner), json={"title": "Mine"}
    )
    conversation_id = created.json()["data"]["id"]

    peek = await harness.client.get(
        f"/api/chat/conversations/{conversation_id}", headers=harness.auth(stranger)
    )
    assert peek.status_code == 404
    hijack = await harness.client.post(
        "/api/chat/orchestrate",
        headers=harness.auth(stranger),
        json={"message": "hi", "conversationId": conversation_id},
    )
    assert hijack.status_code == 404


async def test_agents_catalogue(harness: Harness) -> None:
    token = (await harness.sign_up(email="agents@example.com"))["token"]
    response = await harness.client.get("/api/agents", headers=harness.auth(token))
    agents = {agent["id"]: agent for agent in response.json()["data"]}
    assert len(agents) == 7
    assert agents["validation"]["reads"] == ["resume"]
