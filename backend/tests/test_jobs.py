"""Live job search: the job-board clients (Adzuna, Jobicy, Remotive), and the
Job Search agent ranking REAL postings."""

from __future__ import annotations

import json
from typing import Any, TypeVar

import httpx
import pytest
from pydantic import BaseModel

from app.agents.base import AgentContext, JobBoardUnavailable, JobListing
from app.agents.job_search import agent as job_agent
from app.core.logging import redact
from app.jobs.adzuna import AdzunaJobBoard

M = TypeVar("M", bound=BaseModel)

ADZUNA_RESULTS = {
    "results": [
        {
            "id": "4001",
            "title": "Senior <strong>React</strong> Developer",
            "description": "Build UIs with React &amp; TypeScript for a fintech product.",
            "created": "2026-10-10T09:00:00Z",
            "redirect_url": "https://www.adzuna.in/land/ad/4001",
            "company": {"display_name": "Acme Fintech"},
            "location": {"display_name": "Chennai, Tamil Nadu"},
            "salary_min": 1800000,
            "salary_max": 2600000,
            "salary_is_predicted": "0",
            "contract_time": "full_time",
        },
        {
            "id": "4002",
            "title": "Frontend Engineer",
            "description": "Angular and Java.",
            "created": "2026-10-09T09:00:00Z",
            "redirect_url": "https://www.adzuna.in/land/ad/4002",
            "company": {"display_name": "Globex"},
            "location": {"display_name": "Chennai"},
        },
        {"id": "4003", "title": "No link", "redirect_url": ""},  # unusable: dropped
    ]
}


# ── Adzuna client ───────────────────────────────────────────────────────────


async def test_adzuna_request_and_parsing() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=ADZUNA_RESULTS)

    board = AdzunaJobBoard(
        app_id="id-1", app_key="secret-key", country="in", transport=httpx.MockTransport(handler)
    )
    listings = await board.search("react developer", "Chennai", limit=10)

    request = seen[0]
    assert request.url.host == "api.adzuna.com"
    assert request.url.path == "/v1/api/jobs/in/search/1"
    assert request.url.params["what"] == "react developer"
    assert request.url.params["where"] == "Chennai"
    assert request.url.params["results_per_page"] == "10"
    assert request.url.params["app_id"] == "id-1"

    assert [job.id for job in listings] == ["4001", "4002"]  # the link-less one is dropped
    first = listings[0]
    assert first.title == "Senior React Developer"  # tags stripped
    assert first.company == "Acme Fintech" and first.location == "Chennai, Tamil Nadu"
    assert first.description.startswith("Build UIs with React & TypeScript")
    assert first.apply_url == "https://www.adzuna.in/land/ad/4001"
    assert first.posted_at == "2026-10-10T09:00:00Z"
    assert first.salary == "₹1,800,000 - ₹2,600,000"
    assert listings[1].salary is None
    await board.aclose()


async def test_adzuna_caches_identical_searches() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=ADZUNA_RESULTS)

    board = AdzunaJobBoard(app_id="a", app_key="b", transport=httpx.MockTransport(handler))
    await board.search("react developer", "Chennai")
    await board.search("React Developer ", "chennai")  # same search, different spelling
    assert calls == 1
    await board.aclose()


async def test_adzuna_errors_never_leak_the_key() -> None:
    board = AdzunaJobBoard(
        app_id="a",
        app_key="super-secret-key",
        transport=httpx.MockTransport(lambda _: httpx.Response(401, json={"error": "bad key"})),
    )
    with pytest.raises(JobBoardUnavailable) as error:
        await board.search("anything", "")
    assert "super-secret-key" not in str(error.value)
    assert "app_key=[REDACTED]" in redact("GET https://x/?app_id=a&app_key=super-secret-key&what=y")
    await board.aclose()


# ── The agent ───────────────────────────────────────────────────────────────

PROFILE = {
    "headline": "Frontend engineer",
    "location": "Chennai",
    "work_preference": "Hybrid",
    "target_roles": ["Senior Frontend Engineer"],
    "skills": [{"name": "React"}, {"name": "TypeScript"}],
}

LISTINGS = [
    JobListing(
        id="1",
        title="Senior React Developer",
        company="Acme Fintech",
        location="Chennai",
        description="React, TypeScript and Redux",
        apply_url="https://jobs.example/1",
        posted_at="2026-10-10T09:00:00Z",
        salary="₹18,00,000",
        source="adzuna",
    ),
    JobListing(
        id="2",
        title="Java Backend Engineer",
        company="Globex",
        location="Chennai",
        description="Spring Boot",
        apply_url="https://jobs.example/2",
        source="adzuna",
    ),
]


class FakeBoard:
    name = "fake"

    def __init__(self, listings: list[JobListing] | None = None, fail: bool = False) -> None:
        self.listings = LISTINGS if listings is None else listings
        self.fail = fail
        self.queries: list[tuple[str, str]] = []

    async def search(self, query: str, location: str, *, limit: int = 10) -> list[JobListing]:
        self.queries.append((query, location))
        if self.fail:
            raise JobBoardUnavailable("down")
        return self.listings


class ScriptedLlm:
    available = True

    def __init__(self, ranking: dict[str, Any]) -> None:
        self.ranking = ranking
        self.calls: list[str] = []

    async def complete_json(
        self, *, system: str, user: str, schema: type[M], tier: str = "large"
    ) -> M:
        self.calls.append(schema.__name__)
        if schema.__name__ == "SearchPlan":
            return schema.model_validate({"queries": ["react developer"], "location": "Chennai"})
        if schema.__name__ == "Ranking":
            assert "[0] Senior React Developer" in user and "[1] Java Backend Engineer" in user
            return schema.model_validate(self.ranking)
        # Suggestion mode: the model tries to sneak in a fake link.
        return schema.model_validate(
            {
                "matches": [
                    {
                        "role": "React Developer",
                        "company": "Various employers",
                        "location": "Chennai",
                        "match_score": 80,
                        "reason": "fits",
                        "apply_url": "https://made-up.example",
                    }
                ]
            }
        )


class NoLlm:
    available = False

    async def complete_json(self, **_: Any) -> Any:
        raise AssertionError("not called")


def context(llm: Any, board: Any) -> AgentContext:
    return AgentContext(
        request="Find me jobs",
        profile=PROFILE,
        memories=[],
        inputs={},
        recent_messages=[],
        rendered=json.dumps(PROFILE),
        llm=llm,
        job_board=board,
    )


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """Recency adjustments are relative to "now"; pin it so scores are deterministic."""
    from datetime import UTC, datetime

    monkeypatch.setattr(job_agent, "_now", lambda: datetime(2026, 10, 12, tzinfo=UTC))


def assessment(index: int, *fits: int, **extra: Any) -> dict[str, Any]:
    skills, experience, location, goals = fits
    return {
        "index": index,
        "skills_fit": skills,
        "experience_fit": experience,
        "location_fit": location,
        "goals_fit": goals,
        "reason": f"reason {index}",
        **extra,
    }


async def test_live_results_come_from_postings_not_the_model() -> None:
    llm = ScriptedLlm(
        {
            "picks": [
                # Listed first by the model, but scores lower → ranked second by code.
                assessment(1, 20, 60, 100, 30, eligibility="eligible"),
                assessment(
                    0,
                    90,
                    80,
                    100,
                    80,
                    eligibility="eligible",
                    matched_skills=["react", "TypeScript", "GraphQL"],  # GraphQL: not on profile
                    missing_skills=["Redux", "Kubernetes"],  # Kubernetes: not in the posting
                    next_step="Lead with your dashboard project.",
                ),
                assessment(7, 100, 100, 100, 100),  # doesn't exist
                assessment(0, 10, 10, 10, 10),  # duplicate
            ]
        }
    )
    board = FakeBoard()
    result = await job_agent.run(context(llm, board))
    output = result.output.model_dump()

    assert output["mode"] == "live" and output["query"] == "react developer in Chennai"
    assert output["ranking"] == "ai" and output["considered"] == 2
    assert board.queries == [("react developer", "Chennai")]
    assert [m["company"] for m in output["matches"]] == ["Acme Fintech", "Globex"]
    top = output["matches"][0]
    assert top["apply_url"] == "https://jobs.example/1"  # from the posting
    assert top["posted_at"] == "2026-10-10T09:00:00Z" and top["salary"] == "₹18,00,000"
    # 0.40*90 + 0.25*80 + 0.20*100 + 0.15*80 = 88, +3 for a posting 2 days old.
    assert top["match_score"] == 91
    assert top["fit"] == {"skills": 90, "experience": 80, "location": 100, "goals": 80}
    assert top["matched_skills"] == ["React", "TypeScript"]  # profile spelling, no inventions
    assert top["missing_skills"] == ["Redux"]
    assert top["eligibility"] == "eligible"
    assert top["next_step"] == "Lead with your dashboard project."
    assert output["matches"][1]["match_score"] == 48  # no date → no recency adjustment
    assert llm.calls == ["SearchPlan", "Ranking"]
    assert result.used_llm and result.summary.startswith("Found 2 live postings")


async def test_region_locked_postings_are_capped_and_weak_ones_dropped() -> None:
    llm = ScriptedLlm(
        {
            "picks": [
                assessment(0, 100, 100, 10, 100, eligibility="unlikely"),
                assessment(1, 10, 10, 10, 10, eligibility="eligible"),  # 10 < MIN_SCORE
            ]
        }
    )
    output = (await job_agent.run(context(llm, FakeBoard()))).output.model_dump()
    assert [m["company"] for m in output["matches"]] == ["Acme Fintech"]
    assert output["matches"][0]["match_score"] == job_agent.UNLIKELY_CAP
    assert "outside your region" in output["notice"]


async def test_model_sees_the_most_relevant_postings_not_arrival_order() -> None:
    noise = [
        JobListing(
            id=f"n{i}",
            title="Store Associate",
            company=f"Shop {i}",
            location="Chennai",
            description="Retail floor work",
            apply_url=f"https://jobs.example/n{i}",
        )
        for i in range(40)
    ]
    relevant = LISTINGS[0]  # arrives last
    prompts: list[str] = []

    class Recorder(ScriptedLlm):
        async def complete_json(
            self, *, system: str, user: str, schema: type[M], tier: str = "large"
        ) -> M:
            if schema.__name__ == "Ranking":
                prompts.append(user)
                return schema.model_validate({"picks": [assessment(0, 90, 90, 90, 90)]})
            return await super().complete_json(system=system, user=user, schema=schema, tier=tier)

    board = FakeBoard(listings=[*noise, relevant])
    output = (await job_agent.run(context(Recorder({}), board))).output.model_dump()

    table = prompts[0].split("## Job postings")[1]
    assert f"[{job_agent.MAX_CANDIDATES - 1}]" in table
    assert f"[{job_agent.MAX_CANDIDATES}]" not in table  # capped
    assert "[0] Senior React Developer" in table  # pre-ranked to the top
    assert output["considered"] == 41
    assert output["matches"][0]["company"] == "Acme Fintech"


async def test_without_llm_postings_are_ranked_by_keywords() -> None:
    result = await job_agent.run(context(NoLlm(), FakeBoard()))
    output = result.output.model_dump()
    assert output["mode"] == "live"
    assert output["matches"][0]["company"] == "Acme Fintech"  # mentions React + TypeScript
    assert output["matches"][0]["matched_skills"] == ["React", "TypeScript"]
    assert output["ranking"] == "keyword"
    assert "keyword" in output["notice"]
    assert FakeBoard().listings[0].apply_url == output["matches"][0]["apply_url"]


async def test_no_postings_found_is_reported_honestly() -> None:
    result = await job_agent.run(context(NoLlm(), FakeBoard(listings=[])))
    output = result.output.model_dump()
    assert output["mode"] == "live" and output["matches"] == []
    assert "No live postings" in output["notice"]


@pytest.mark.parametrize("board", [None, FakeBoard(fail=True)], ids=["no-board", "board-down"])
async def test_suggestions_are_labelled_and_never_carry_links(board: Any) -> None:
    result = await job_agent.run(context(ScriptedLlm({"picks": []}), board))
    output = result.output.model_dump()
    assert output["mode"] == "suggested"
    assert output["notice"]  # tells the user these aren't live postings
    assert all(
        m["apply_url"] is None for m in output["matches"]
    )  # the model's fake link is removed
    assert result.summary.startswith("Suggested")


# ── Through the real API ────────────────────────────────────────────────────


async def test_orchestrate_returns_live_postings_with_apply_links(tmp_path: Any) -> None:
    from tests.conftest import make_settings, parse_sse, running_app

    settings = make_settings(tmp_path, adzuna_app_id="id", adzuna_app_key="key")
    adzuna = httpx.MockTransport(lambda _: httpx.Response(200, json=ADZUNA_RESULTS))
    async with running_app(settings, jobs_transport=adzuna) as h:
        health = (await h.client.get("/api/health")).json()["data"]
        assert health["jobBoard"] == "adzuna"

        token = (await h.sign_up(email="jobs@example.com"))["token"]
        headers = h.auth(token)
        await h.client.patch(
            "/api/profile",
            headers=headers,
            json={
                "targetRoles": ["React Developer"],
                "location": "Chennai",
                "skills": [{"name": "React"}, {"name": "TypeScript"}],
            },
        )
        response = await h.client.post(
            "/api/chat/orchestrate",
            headers=headers,
            json={"message": "Find me jobs", "agents": ["job_search"]},
        )
        answer = next(e for e in parse_sse(response.text) if e["type"] == "answer")
        output = answer["agentOutputs"]["job_search"]
        assert output["mode"] == "live"
        assert output["query"] == "React Developer in Chennai"  # rule plan (no LLM in tests)
        top = output["matches"][0]
        assert top["company"] == "Acme Fintech"
        assert top["applyUrl"] == "https://www.adzuna.in/land/ad/4001"  # camelCase for the UI
        assert top["postedAt"] == "2026-10-10T09:00:00Z"
        assert "app_key" not in h.logs.getvalue() or "app_key=[REDACTED]" in h.logs.getvalue()


# ── Free, keyless boards: Jobicy + Remotive ────────────────────────────────

JOBICY_RESULTS = {
    "jobs": [
        {
            "id": 155084,
            "url": "https://jobicy.com/jobs/155084-senior-web-developer",
            "jobTitle": "Senior Web Developer",
            "companyName": "UpGuard",
            "jobGeo": "APAC",
            "jobType": ["Full-Time"],
            "pubDate": "2026-10-12T06:59:53+00:00",
            "jobExcerpt": "Build &amp; ship <b>React</b> apps.",
            "annualSalaryMin": 90000,
            "annualSalaryMax": 120000,
            "salaryCurrency": "USD",
        },
        {"id": 1, "jobTitle": "No link", "companyName": "X"},  # unusable: dropped
    ]
}

REMOTIVE_RESULTS = {
    "jobs": [
        {
            "id": 11,
            "url": "https://remotive.com/remote-jobs/sales/inside-sales-11",
            "title": "Inside Sales Contractor",
            "company_name": "Credit Co",
            "category": "Sales",
            "tags": ["CRM"],
            "job_type": "full_time",
            "publication_date": "2026-10-08T21:47:32",
            "candidate_required_location": "Worldwide",
            "salary": "",
        },
        {
            "id": 12,
            "url": "https://remotive.com/remote-jobs/software-development/react-12",
            "title": "Senior React Full-stack Developer",
            "company_name": "Lemon.io",
            "category": "Software Development",
            "tags": ["react", "node.js", "typescript"],
            "job_type": "full_time",
            "publication_date": "2026-10-02T13:30:06",
            "candidate_required_location": "Europe, USA, Canada, APAC",
            "salary": "$80k - $150k",
        },
        {
            "id": 13,
            "url": "https://remotive.com/remote-jobs/software-development/backend-13",
            "title": "Backend Engineer",
            "company_name": "Acme",
            "category": "Software Development",
            "tags": ["python", "react"],
            "job_type": "contract",
            "publication_date": "2026-10-01T10:00:00",
            "candidate_required_location": "India",
            "salary": "",
        },
    ]
}


async def test_jobicy_request_and_parsing() -> None:
    from app.jobs.jobicy import JobicyJobBoard

    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=JOBICY_RESULTS)

    board = JobicyJobBoard(transport=httpx.MockTransport(handler))
    listings = await board.search("react developer", "Chennai", limit=8)
    await board.search("React Developer ", "Mumbai", limit=8)  # cached: location isn't sent

    assert len(seen) == 1
    assert seen[0].url.host == "jobicy.com"
    assert seen[0].url.params["tag"] == "react developer"
    assert seen[0].url.params["count"] == "8"
    assert "geo" not in seen[0].url.params
    assert [job.id for job in listings] == ["jobicy-155084"]
    job = listings[0]
    assert job.company == "UpGuard" and job.location == "Remote · APAC"
    assert job.description == "Build & ship React apps."
    assert job.apply_url == "https://jobicy.com/jobs/155084-senior-web-developer"
    assert job.salary == "USD 90,000 - 120,000 / year"
    assert job.source == "jobicy"
    await board.aclose()


async def test_remotive_fetches_feed_once_and_filters_locally() -> None:
    import asyncio

    from app.jobs.remotive import RemotiveJobBoard

    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=REMOTIVE_RESULTS)

    board = RemotiveJobBoard(transport=httpx.MockTransport(handler))
    react, backend = await asyncio.gather(
        board.search("React Developer", "Chennai"), board.search("backend python", "")
    )
    nothing = await board.search("pastry chef", "")

    assert len(calls) == 1  # parallel searches share one fetch; Remotive asks for few calls
    assert calls[0].url.path == "/api/remote-jobs"
    # Title matches outrank tag-only matches; unrelated jobs are filtered out.
    assert [job.id for job in react] == ["remotive-12", "remotive-13"]
    assert [job.id for job in backend] == ["remotive-13"]
    assert nothing == []
    top = react[0]
    assert top.location == "Remote · Europe, USA, Canada, APAC"
    assert top.salary == "$80k - $150k"
    assert top.contract == "full time"
    assert top.source == "remotive"
    assert react[1].salary is None
    await board.aclose()


async def test_multi_board_merges_dedupes_and_survives_one_failure() -> None:
    from app.jobs.multi import MultiJobBoard

    class Board:
        def __init__(self, name: str, jobs: list[JobListing] | None) -> None:
            self.name, self.jobs, self.closed = name, jobs, False

        async def search(self, query: str, location: str, *, limit: int = 10) -> list[JobListing]:
            if self.jobs is None:
                raise JobBoardUnavailable("down")
            return self.jobs[:limit]

        async def aclose(self) -> None:
            self.closed = True

    def job(n: str, title: str, company: str) -> JobListing:
        return JobListing(
            id=n, title=title, company=company, location="", description="", apply_url=f"u{n}"
        )

    a = Board("a", [job("a1", "Dev", "Acme"), job("a2", "QA", "Acme")])
    b = Board("b", [job("b1", "dev", "ACME"), job("b2", "PM", "Globex")])  # b1 duplicates a1
    down = Board("down", None)
    multi = MultiJobBoard([a, down, b])

    assert multi.name == "a+down+b"
    assert [j.id for j in await multi.search("dev", "")] == ["a1", "a2", "b2"]
    assert [j.id for j in await multi.search("dev", "", limit=2)] == ["a1", "a2"]

    with pytest.raises(JobBoardUnavailable):
        await MultiJobBoard([down, Board("down2", None)]).search("dev", "")
    await multi.aclose()
    assert a.closed
    assert b.closed
    assert down.closed


def test_factory_defaults_to_free_boards_and_adds_adzuna_when_keyed(tmp_path: Any) -> None:
    from app.jobs.factory import build_job_board
    from tests.conftest import make_settings

    free = build_job_board(make_settings(tmp_path, job_boards="jobicy,remotive"))
    assert free is not None
    assert free.name == "jobicy+remotive"
    keyed = make_settings(tmp_path, job_boards="jobicy", adzuna_app_id="i", adzuna_app_key="k")
    board = build_job_board(keyed)
    assert board is not None
    assert board.name == "adzuna+jobicy"
    assert build_job_board(make_settings(tmp_path, job_boards="")) is None


async def test_orchestrate_with_free_boards(tmp_path: Any) -> None:
    from tests.conftest import make_settings, parse_sse, running_app

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "jobicy.com":
            return httpx.Response(200, json=JOBICY_RESULTS)
        if request.url.host == "remotive.com":
            return httpx.Response(200, json=REMOTIVE_RESULTS)
        return httpx.Response(404)

    settings = make_settings(tmp_path, job_boards="jobicy,remotive")
    async with running_app(settings, jobs_transport=httpx.MockTransport(handler)) as h:
        health = (await h.client.get("/api/health")).json()["data"]
        assert health["jobBoard"] == "jobicy+remotive"

        token = (await h.sign_up(email="free-jobs@example.com"))["token"]
        headers = h.auth(token)
        await h.client.patch(
            "/api/profile",
            headers=headers,
            json={"targetRoles": ["React Developer"], "skills": [{"name": "React"}]},
        )
        response = await h.client.post(
            "/api/chat/orchestrate",
            headers=headers,
            json={"message": "Find me jobs", "agents": ["job_search"]},
        )
        answer = next(e for e in parse_sse(response.text) if e["type"] == "answer")
        output = answer["agentOutputs"]["job_search"]
        assert output["mode"] == "live"
        assert {m["source"] for m in output["matches"]} == {"jobicy", "remotive"}
        assert {m["applyUrl"] for m in output["matches"]} <= {
            "https://jobicy.com/jobs/155084-senior-web-developer",
            "https://remotive.com/remote-jobs/software-development/react-12",
            "https://remotive.com/remote-jobs/software-development/backend-13",
        }
