"""Mock interview tests: generation is role/domain-specific, the key stays on the server,
grading is instant and deterministic, results feed memory and the next test."""

from __future__ import annotations

import json
import random
import uuid
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from app.agents.interview.mock_test import grade, validate_drafts
from app.agents.interview.schema import MockQuestion, MockTestDraft
from app.memory.store import SqlMemoryStore
from tests.conftest import Harness, make_settings, running_app

M = TypeVar("M", bound=BaseModel)


def q(question: str, options: list[str], answer: int, topic: str = "React") -> dict[str, Any]:
    return {
        "question": question,
        "options": options,
        "answer_index": answer,
        "explanation": f"Because {options[answer] if 0 <= answer < len(options) else '?'}.",
        "topic": topic,
        "difficulty": "medium",
    }


DRAFT = {
    "questions": [
        q(
            "Which hook memoises an expensive computed value?",
            ["useMemo", "useRef", "useId", "useEffect"],
            0,
        ),
        q(
            "What does a ledger entry pair in double-entry bookkeeping?",
            ["Debit and credit", "Two users", "Two currencies", "A refund and fee"],
            0,
            "Payments domain",
        ),
        q(
            "Best first step when a teammate's PR breaks checkout?",
            ["Revert and talk to them", "Ignore it", "Rewrite it alone", "Escalate to the CEO"],
            0,
            "Behavioural",
        ),
        q(
            "Which HTTP status means a resource was created?",
            ["201", "200", "204", "301"],
            0,
            "APIs",
        ),
        q(
            "PCI DSS mainly protects which data?",
            ["Cardholder data", "Source code", "Logs only", "Marketing emails"],
            0,
            "Payments domain",
        ),
        # Malformed items the validator must drop:
        q("Only three options here, so it's invalid?", ["a", "b", "c"], 0),
        q("Duplicate options are not allowed here?", ["x", "X", "y", "z"], 0),
        q("Which is right? (banned option style)", ["a", "b", "c", "All of the above"], 3),
        q("Answer index out of range is invalid?", ["a", "b", "c", "d"], 7),
        q("Which hook memoises an expensive computed value?", ["useMemo", "a", "b", "c"], 0),  # dup
    ]
}


# ── Pure logic ──────────────────────────────────────────────────────────────


def test_validator_drops_bad_items_and_shuffles_without_losing_the_key() -> None:
    questions = validate_drafts(MockTestDraft.model_validate(DRAFT), count=10, rng=random.Random(7))  # noqa: S311
    assert len(questions) == 5  # five malformed / duplicate items dropped
    for question, source in zip(questions, DRAFT["questions"], strict=False):
        assert question.options[question.answer_index] == source["options"][0]
    # With every source key at index 0, shuffling must move at least one.
    assert any(question.answer_index != 0 for question in questions)
    assert len(validate_drafts(MockTestDraft.model_validate(DRAFT), count=2)) == 2


def test_grading_scores_topics_and_flags_weak_ones() -> None:
    def mq(topic: str, answer: int) -> MockQuestion:
        return MockQuestion(
            question=f"{topic} question {answer}?",
            options=["a", "b", "c", "d"],
            answer_index=answer,
            explanation="",
            topic=topic,
            difficulty="easy",
        )

    questions = [mq("React", 0), mq("React", 1), mq("SQL", 2), mq("SQL", 3), mq("Behavioural", 0)]
    result = grade(questions, [0, 1, 0])  # 2 right, 1 wrong, 2 skipped (padded with None)
    assert (result.score, result.total, result.percent) == (2, 5, 40)
    assert result.correct == [True, True, False, False, False]
    assert result.label == "Needs practice"
    assert [(t.topic, t.correct, t.total) for t in result.topics] == [
        ("SQL", 0, 2),
        ("Behavioural", 0, 1),
        ("React", 2, 2),
    ]
    assert result.weak_topics == ["SQL", "Behavioural"]
    assert grade(questions, [0, 1, 2, 3, 0]).label == "Interview-ready"


TABLE_QUESTION = (
    "You need to render a table of 10,000 transaction records on a dashboard. "
    "Which technique keeps scrolling smooth?"
)
TABLE_REWORDED = (
    "Your product needs to render a table of 10,000 recent transactions on a dashboard. "
    "Which technique keeps scrolling smooth?"
)
TABLE_OPTIONS = ["Virtualise rows with react-window", "Render all rows", "Use a table tag", "CSS"]


def test_near_duplicates_across_batches_are_dropped() -> None:
    first = MockTestDraft.model_validate(
        {"questions": [q(TABLE_QUESTION, TABLE_OPTIONS, 0, "Performance")]}
    )
    second = MockTestDraft.model_validate(
        {
            "questions": [
                q(TABLE_REWORDED, TABLE_OPTIONS, 0, "Performance"),
                q(
                    "Which HTTP status means a resource was created?",
                    ["201", "200", "204", "301"],
                    0,
                    "APIs",
                ),
            ]
        }
    )
    seen: list[frozenset[str]] = []
    assert len(validate_drafts(first, count=4, seen=seen)) == 1
    kept = validate_drafts(second, count=4, seen=seen)
    assert [x.topic for x in kept] == ["APIs"]  # the reworded table question is a repeat


def test_batches_mix_the_test_and_spread_skills() -> None:
    from app.agents.interview.mock_test import plan_batches

    batches = plan_batches(10, "Fintech", ["React", "TypeScript", "Next.js", "GraphQL"])
    assert [(b.kind, b.count) for b in batches] == [
        ("core", 3),
        ("core", 2),
        ("domain", 3),
        ("judgement", 2),
    ]
    assert "React, Next.js" in batches[0].focus and "TypeScript, GraphQL" in batches[1].focus
    assert "Fintech" in batches[2].focus
    assert sum(b.count for b in plan_batches(20, "", [])) == 20
    assert all(b.count <= 4 for b in plan_batches(20, "", []))


async def test_one_failed_batch_does_not_sink_the_test() -> None:
    from app.agents.interview.mock_test import MockTestUnavailable, generate_mock_test
    from app.llm.errors import LlmUnavailable

    class StubLlm:
        available = True

        def __init__(self, fail_kind: str) -> None:
            self.fail_kind = fail_kind

        async def complete_json(
            self, *, system: str, user: str, schema: type[M], tier: Any = "large"
        ) -> M:
            if self.fail_kind in user:
                raise LlmUnavailable("down")
            return schema.model_validate(DRAFT)

    questions = await generate_mock_test(
        StubLlm("situational"), role="Frontend Engineer", domain="", difficulty="mixed",
        count=5, context="",
    )  # fmt: skip
    assert 3 <= len(questions) <= 5
    assert len({q.question for q in questions}) == len(questions)  # no cross-batch duplicates

    try:
        await generate_mock_test(
            StubLlm("Role:"), role="X", domain="", difficulty="mixed", count=5, context=""
        )
    except MockTestUnavailable as exc:
        assert "couldn't write" in str(exc)
    else:
        raise AssertionError("expected MockTestUnavailable")


# ── Through the API ─────────────────────────────────────────────────────────


class FakeLlm:
    """OpenAI-compatible endpoint that returns DRAFT and records every prompt."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        self.prompts.append("\n".join(m["content"] for m in body["messages"]))
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps(DRAFT)}}], "usage": {}},
        )


PROFILE = {
    "headline": "Frontend developer, 3 years",
    "experienceLevel": "Mid-level",
    "targetRoles": ["Frontend Engineer"],
    "interests": ["Fintech"],
    "skills": [{"name": "React", "level": "Advanced"}, {"name": "TypeScript"}],
}


async def _signed_in(h: Harness, email: str, profile: dict[str, Any]) -> dict[str, str]:
    session = await h.sign_up(email=email)
    headers = h.auth(session["token"])
    response = await h.client.patch("/api/profile", headers=headers, json=profile)
    assert response.status_code == 200
    return headers


def _correct_index(question: dict[str, Any]) -> int:
    """The test knows DRAFT's keys (always option 0 before shuffling)."""
    source = next(d for d in DRAFT["questions"] if d["question"] == question["question"])
    return int(question["options"].index(source["options"][0]))


async def test_mock_test_end_to_end(tmp_path: Any) -> None:
    llm = FakeLlm()
    settings = make_settings(tmp_path, groq_api_keys="gsk_test")
    async with running_app(settings, llm_transport=httpx.MockTransport(llm)) as h:
        headers = await _signed_in(h, "mock@example.com", PROFILE)

        created = await h.client.post(
            "/api/interview/mock-tests", headers=headers, json={"count": 5}
        )
        assert created.status_code == 201, created.text
        test = created.json()["data"]
        # Defaults come from the profile: first target role + first interested domain.
        assert (test["role"], test["domain"]) == ("Frontend Engineer", "Fintech")
        assert len(test["questions"]) == 5
        # The browser never sees the key.
        assert "answerIndex" not in created.text and "explanation" not in created.text

        prompt = llm.prompts[0]
        assert "Role: Frontend Engineer" in prompt and "Domain: Fintech" in prompt
        assert "React (Advanced)" in prompt and "Mid-level" in prompt

        # Answer 3 right, 1 wrong, 1 skipped.
        questions = test["questions"]
        answers: list[int | None] = [_correct_index(x) for x in questions[:3]]
        answers.append((_correct_index(questions[3]) + 1) % 4)
        answers.append(None)
        url = f"/api/interview/mock-tests/{test['id']}/attempts"
        graded = await h.client.post(
            url, headers=headers, json={"answers": answers, "timeTakenSeconds": 95}
        )
        assert graded.status_code == 201, graded.text
        result = graded.json()["data"]
        assert (result["score"], result["total"], result["percent"]) == (3, 5, 60)
        assert result["grade"] == "Developing"
        assert [r["correct"] for r in result["results"]] == [True, True, True, False, False]
        assert result["results"][4]["yourAnswer"] is None
        assert result["results"][0]["explanation"].startswith("Because")
        assert result["attemptNumber"] == 1 and result["timeTakenSeconds"] == 95
        assert {t["topic"] for t in result["topics"]} >= {"React", "Payments domain"}

        # Retake: everything right.
        perfect = [_correct_index(x) for x in questions]
        again = (await h.client.post(url, headers=headers, json={"answers": perfect})).json()
        assert again["data"]["percent"] == 100 and again["data"]["attemptNumber"] == 2
        assert again["data"]["bestPercent"] == 100

        listing = (await h.client.get("/api/interview/mock-tests", headers=headers)).json()
        summary = listing["data"][0]
        assert (summary["attempts"], summary["bestPercent"], summary["lastPercent"]) == (
            2,
            100,
            100,
        )
        detail = await h.client.get(f"/api/interview/mock-tests/{test['id']}", headers=headers)
        assert [a["percent"] for a in detail.json()["data"]["attempts"]] == [60, 100]
        assert "answerIndex" not in detail.text

        # Other agents learn the result through long-term memory.
        session = (await h.client.get("/api/auth/session", headers=headers)).json()
        user_id = uuid.UUID(session["data"]["user"]["id"])
        memories = await SqlMemoryStore(h.app.state.db).recall(user_id, "mock test", 5)
        assert any("Mock test for Frontend Engineer, Fintech: 3/5 (60%)" in m for m in memories)

        # Explicit role/domain override the profile; past weak topics steer the next test.
        await h.client.post(
            "/api/interview/mock-tests",
            headers=headers,
            json={"role": "Data Analyst", "domain": "Healthcare", "difficulty": "hard", "count": 5},
        )
        assert "Role: Data Analyst" in llm.prompts[-1] and "Domain: Healthcare" in llm.prompts[-1]
        assert "Difficulty: hard" in llm.prompts[-1]
        assert "Got these wrong in recent mock tests" in llm.prompts[-1]


async def test_tests_are_private_and_input_is_checked(tmp_path: Any) -> None:
    settings = make_settings(tmp_path, groq_api_keys="gsk_test")
    async with running_app(settings, llm_transport=httpx.MockTransport(FakeLlm())) as h:
        owner = await _signed_in(h, "owner@example.com", PROFILE)
        test = (
            await h.client.post("/api/interview/mock-tests", headers=owner, json={"count": 5})
        ).json()["data"]
        url = f"/api/interview/mock-tests/{test['id']}"

        stranger = await _signed_in(h, "stranger@example.com", PROFILE)
        assert (await h.client.get(url, headers=stranger)).status_code == 404
        response = await h.client.post(f"{url}/attempts", headers=stranger, json={"answers": []})
        assert response.status_code == 404

        bad = await h.client.post(f"{url}/attempts", headers=owner, json={"answers": [9]})
        assert bad.status_code == 400
        too_many = await h.client.post(f"{url}/attempts", headers=owner, json={"answers": [0] * 6})
        assert too_many.status_code == 400

        no_role = await _signed_in(h, "norole@example.com", {"skills": [{"name": "Excel"}]})
        response = await h.client.post("/api/interview/mock-tests", headers=no_role, json={})
        assert response.status_code == 400
        assert "target role" in response.json()["error"]["message"]


async def test_without_llm_keys_the_api_says_so(tmp_path: Any) -> None:
    async with running_app(make_settings(tmp_path)) as h:
        headers = await _signed_in(h, "nokeys@example.com", PROFILE)
        response = await h.client.post("/api/interview/mock-tests", headers=headers, json={})
        assert response.status_code == 503
        assert "LLM key" in response.json()["error"]["message"]
