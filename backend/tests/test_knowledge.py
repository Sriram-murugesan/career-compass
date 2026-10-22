"""Shared knowledge graph: normalisation, privacy threshold, postings, paths, agents' view."""

from __future__ import annotations

import uuid
from typing import Any

from app.knowledge.normalize import (
    company_key,
    current_role_from_headline,
    role_key,
    role_label,
    skill_key,
)
from app.knowledge.store import SqlKnowledgeGraph
from tests.conftest import Harness, make_settings, running_app


def test_normalisation_merges_spellings() -> None:
    assert skill_key(" ReactJS ") == skill_key("react.js") == "react"
    assert skill_key("Tailwind") == "tailwind css"
    assert role_label("Senior Frontend Engineer - UK") == "Frontend Engineer"
    assert role_key("Sr. Lead Backend Developer (Contract)") == "backend developer"
    assert company_key("Acme Pvt Ltd") == "acme"
    assert current_role_from_headline("Frontend developer, 3 years") == "Frontend developer"
    assert current_role_from_headline("5 years building things") == ""


async def _user(h: Harness, email: str, **profile: Any) -> dict[str, str]:
    session = await h.sign_up(email=email)
    headers = h.auth(session["token"])
    USER_IDS[email] = session["user"]["id"]
    response = await h.client.patch("/api/profile", headers=headers, json=profile)
    assert response.status_code == 200, response.text
    return headers


async def _me(h: Harness, headers: dict[str, str]) -> dict[str, Any]:
    response = await h.client.get("/api/graph/me", headers=headers)
    assert response.status_code == 200, response.text
    data: dict[str, Any] = response.json()["data"]
    return data


USER_IDS: dict[str, str] = {}

FRONTEND = {
    "targetRoles": ["Frontend Engineer"],
    "skills": [{"name": "React"}, {"name": "TypeScript"}],
}


async def test_profile_edges_are_shared_only_above_the_threshold(tmp_path: Any) -> None:
    async with running_app(make_settings(tmp_path, graph_min_users=3)) as h:
        alice = await _user(h, "alice@example.com", **FRONTEND)
        await _user(h, "bob@example.com", **FRONTEND)

        mine = await _me(h, alice)
        relations = {(link["relation"], link["node"]["label"]) for link in mine["links"]}
        assert ("has_skill", "React") in relations  # your own links: always visible to you
        assert mine["roles"][0]["role"]["key"] == "frontend engineer"
        assert mine["roles"][0]["skills"] == []  # only 2 users so far: below the threshold
        assert mine["minUsers"] == 3

        await _user(h, "carol@example.com", targetRoles=["Senior Frontend Engineer"],
                    skills=[{"name": "reactjs"}, {"name": "GraphQL"}])  # fmt: skip
        skills = {s["node"]["key"]: s for s in (await _me(h, alice))["roles"][0]["skills"]}
        assert skills["react"]["users"] == 3  # "reactjs" and seniority merged into one edge
        assert skills["react"]["yours"] is True
        assert "typescript" not in skills  # 2 users: still private
        assert "graphql" not in skills

        node = await h.client.get("/api/graph/nodes/role/Frontend Engineer", headers=alice)
        assert node.status_code == 200
        assert [s["node"]["key"] for s in node.json()["data"]["groups"]["skills"]] == ["react"]


async def test_one_users_data_never_reaches_another(tmp_path: Any) -> None:
    async with running_app(make_settings(tmp_path, graph_min_users=2)) as h:
        await _user(h, "dana@example.com", targetRoles=["Quantum Gardener"],
                    skills=[{"name": "SecretLang"}, {"name": "React"}])  # fmt: skip
        eve = await _user(h, "eve@example.com", **FRONTEND)

        search = await h.client.get("/api/graph/search", params={"q": "secret"}, headers=eve)
        assert search.json()["data"] == []
        hidden = await h.client.get("/api/graph/nodes/skill/SecretLang", headers=eve)
        assert hidden.status_code == 404  # unknown and private look the same
        assert "SecretLang" not in str(await _me(h, eve))
        unauthenticated = await h.client.get("/api/graph/me")
        assert unauthenticated.status_code == 401


async def test_editing_a_profile_withdraws_its_contribution(tmp_path: Any) -> None:
    async with running_app(make_settings(tmp_path, graph_min_users=2)) as h:
        frank = await _user(h, "frank@example.com", **FRONTEND)
        grace = await _user(h, "grace@example.com", **FRONTEND)
        assert [s["node"]["key"] for s in (await _me(h, frank))["roles"][0]["skills"]] == [
            "react",
            "typescript",
        ]
        await h.client.patch("/api/profile", headers=grace, json={"skills": [{"name": "Go"}]})
        assert (await _me(h, frank))["roles"][0]["skills"] == []  # back below the threshold


async def test_postings_teach_the_graph_and_hide_small_user_counts(tmp_path: Any) -> None:
    async with running_app(make_settings(tmp_path, graph_min_users=3)) as h:
        henry = await _user(h, "henry@example.com", **FRONTEND)
        graph = SqlKnowledgeGraph(h.app.state.db, min_users=3)
        recorded = await graph.record_postings(
            {
                "mode": "live",
                "matches": [
                    {
                        "role": "Senior Frontend Engineer - UK",
                        "company": "Acme Inc",
                        "apply_url": "https://jobs.example/1",
                        "matched_skills": ["React"],
                        "missing_skills": ["Redux"],
                    },
                    {"role": "No link", "company": "X", "apply_url": ""},  # ignored
                ],
            }
        )
        assert recorded == 1
        assert await graph.record_postings({"mode": "suggested", "matches": []}) == 0

        role = (await _me(h, henry))["roles"][0]
        skills = {s["node"]["key"]: s for s in role["skills"]}
        assert skills["react"]["postings"] == 1
        assert skills["react"]["users"] == 0  # henry backs it too, but 1 < 3 is never shown
        assert skills["redux"]["yours"] is False  # a gap for henry
        assert [c["node"]["label"] for c in role["companies"]] == ["Acme Inc"]

        text = await graph.insights_text(uuid.UUID(USER_IDS["henry@example.com"]), {})
        assert "Redux (1 posting, GAP)" in text and "Acme Inc" in text


async def test_career_paths_follow_leads_to_recursively(tmp_path: Any) -> None:
    async with running_app(make_settings(tmp_path, graph_min_users=1)) as h:
        viewer = await _user(h, "ivy@example.com", headline="Developer, 2 years",
                             targetRoles=["Frontend Engineer"])  # fmt: skip
        await _user(h, "jack@example.com", headline="Frontend Engineer at Acme",
                    targetRoles=["Engineering Manager", "Developer"])  # fmt: skip
        response = await h.client.get(
            "/api/graph/paths", params={"role": "Developer"}, headers=viewer
        )
        paths = [[n["label"] for n in path] for path in response.json()["data"]["paths"]]
        # Developer → Frontend Engineer → Engineering Manager; the cycle back to Developer
        # is cut, and the shorter prefix path is folded into the longer one.
        assert paths == [["Developer", "Frontend Engineer", "Engineering Manager"]]


def test_agents_get_the_graph_in_their_context() -> None:
    from app.agents.registry import REGISTRY
    from app.memory.context import ContextBuilder

    context = ContextBuilder(6000).build(
        REGISTRY["job_search"],
        request="Find jobs",
        profile={},
        memories=[],
        agent_outputs={},
        history=[],
        llm=None,  # type: ignore[arg-type]
        graph_insights="- Frontend Engineer: skills most associated — React (3 users)",
    )
    assert "## Shared career graph\n- Frontend Engineer" in context.rendered
