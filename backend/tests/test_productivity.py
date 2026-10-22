"""Productivity tracker: habits, check-ins, streaks, and the link to mock-test scores."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import httpx

from app.db.base import utcnow
from app.modules.productivity.service import _streak
from tests.conftest import Harness, make_settings, running_app
from tests.test_mock_tests import PROFILE, FakeLlm, _correct_index

TODAY = utcnow().date()


def test_daily_streak_survives_an_unfinished_today() -> None:
    days = {TODAY - timedelta(days=i) for i in (1, 2, 3)}  # yesterday and the 2 days before
    assert _streak(days, TODAY, 7) == (3, "days")
    assert _streak(days | {TODAY}, TODAY, 7) == (4, "days")
    assert _streak({TODAY - timedelta(days=2)}, TODAY, 7) == (0, "days")


def test_weekly_streak_counts_weeks_that_met_the_target() -> None:
    monday = date(2026, 10, 19)  # a Monday
    today = monday + timedelta(days=2)  # Wednesday
    last_week = {monday - timedelta(days=d) for d in (1, 3, 5)}  # 3 sessions
    two_weeks_ago = {monday - timedelta(days=d) for d in (8, 10, 12)}
    assert _streak(last_week | two_weeks_ago, today, 3) == (2, "weeks")  # this week in progress
    this_week = {monday, monday + timedelta(days=1), today}
    assert _streak(this_week | last_week | two_weeks_ago, today, 3) == (3, "weeks")
    assert _streak({monday - timedelta(days=1)}, today, 3) == (0, "weeks")


async def _signed_in(
    h: Harness, email: str, profile: dict[str, Any] | None = None
) -> dict[str, str]:
    session = await h.sign_up(email=email)
    headers = h.auth(session["token"])
    if profile:
        await h.client.patch("/api/profile", headers=headers, json=profile)
    return headers


async def _overview(h: Harness, headers: dict[str, str]) -> dict[str, Any]:
    response = await h.client.get(
        "/api/productivity/overview", params={"today": TODAY.isoformat()}, headers=headers
    )
    assert response.status_code == 200, response.text
    data: dict[str, Any] = response.json()["data"]
    return data


def _log_url(habit_id: str, day: date) -> str:
    return f"/api/productivity/habits/{habit_id}/logs/{day.isoformat()}?today={TODAY.isoformat()}"


async def test_habits_check_ins_and_overview(tmp_path: Any) -> None:
    async with running_app(make_settings(tmp_path)) as h:
        me = await _signed_in(h, "habits@example.com")
        gym = await h.client.post(
            "/api/productivity/habits",
            headers=me,
            json={"name": "Gym", "category": "fitness", "targetPerWeek": 3, "targetMinutes": 60},
        )
        assert gym.status_code == 201, gym.text
        gym_id = gym.json()["data"]["id"]
        cardio = await h.client.post(
            "/api/productivity/habits", headers=me, json={"name": "Cardio", "category": "fitness"}
        )
        cardio_id = cardio.json()["data"]["id"]

        for back in (0, 1, 2):  # cardio: today and the two days before
            day = TODAY - timedelta(days=back)
            response = await h.client.put(
                _log_url(cardio_id, day), headers=me, json={"minutes": 20}
            )
            assert response.status_code == 200, response.text
        await h.client.put(
            _log_url(gym_id, TODAY), headers=me, json={"minutes": 75, "note": "legs"}
        )
        # Checking in twice the same day updates, never duplicates.
        await h.client.put(_log_url(gym_id, TODAY), headers=me, json={"minutes": 80})

        data = await _overview(h, me)
        habits = {s["habit"]["name"]: s for s in data["habits"]}
        assert habits["Cardio"]["streak"] == 3 and habits["Cardio"]["streakUnit"] == "days"
        assert habits["Cardio"]["last7"][-3:] == [True, True, True]
        assert habits["Gym"]["doneToday"] is True and habits["Gym"]["minutesToday"] == 80
        assert habits["Gym"]["totalSessions"] == 1 and habits["Gym"]["streakUnit"] == "weeks"
        assert data["doneToday"] == 2
        assert len(data["heatmap"]) == 28 and data["heatmap"][-1]["completed"] == 2
        assert 0 < data["weekCompletion"] <= 100

        # Undo, archive, delete.
        await h.client.delete(_log_url(gym_id, TODAY), headers=me)
        habits = {s["habit"]["name"]: s for s in (await _overview(h, me))["habits"]}
        assert habits["Gym"]["doneToday"] is False
        await h.client.patch(
            f"/api/productivity/habits/{gym_id}", headers=me, json={"archived": True}
        )
        assert [s["habit"]["name"] for s in (await _overview(h, me))["habits"]] == ["Cardio"]
        deleted = await h.client.delete(f"/api/productivity/habits/{cardio_id}", headers=me)
        assert deleted.status_code == 200
        assert (await _overview(h, me))["habits"] == []


async def test_dates_and_ownership_are_checked(tmp_path: Any) -> None:
    async with running_app(make_settings(tmp_path)) as h:
        me = await _signed_in(h, "dates@example.com")
        habit_id = (
            await h.client.post("/api/productivity/habits", headers=me, json={"name": "Read"})
        ).json()["data"]["id"]

        future = await h.client.put(
            _log_url(habit_id, TODAY + timedelta(days=1)), headers=me, json={}
        )
        assert future.status_code == 400
        ancient = await h.client.put(
            _log_url(habit_id, TODAY - timedelta(days=90)), headers=me, json={}
        )
        assert ancient.status_code == 400
        wrong_today = await h.client.get(
            "/api/productivity/overview", params={"today": "2020-01-01"}, headers=me
        )
        assert wrong_today.status_code == 400

        stranger = await _signed_in(h, "stranger2@example.com")
        response = await h.client.put(_log_url(habit_id, TODAY), headers=stranger, json={})
        assert response.status_code == 404
        response = await h.client.delete(f"/api/productivity/habits/{habit_id}", headers=stranger)
        assert response.status_code == 404
        assert (await _overview(h, stranger))["habits"] == []


async def test_learning_is_linked_to_mock_test_scores(tmp_path: Any) -> None:
    settings = make_settings(tmp_path, groq_api_keys="gsk_test")
    async with running_app(settings, llm_transport=httpx.MockTransport(FakeLlm())) as h:
        me = await _signed_in(h, "learner@example.com", PROFILE)
        test = (
            await h.client.post("/api/interview/mock-tests", headers=me, json={"count": 5})
        ).json()["data"]
        attempts = f"/api/interview/mock-tests/{test['id']}/attempts"
        # Get every Payments-domain question wrong, everything else right.
        answers = [
            (_correct_index(q) + 1) % 4 if q["topic"] == "Payments domain" else _correct_index(q)
            for q in test["questions"]
        ]
        first = (await h.client.post(attempts, headers=me, json={"answers": answers})).json()

        learning = {t["topic"]: t for t in (await _overview(h, me))["learning"]}
        assert learning["Payments domain"]["latestPercent"] == 0
        assert learning["Payments domain"]["status"] == "untracked"
        assert "React" not in learning  # scored 100%: nothing to study

        # One tap: track the weak topic as a learning habit.
        created = await h.client.post(
            "/api/productivity/habits", headers=me, json={"linkedTopic": "Payments domain"}
        )
        assert created.status_code == 201
        habit = created.json()["data"]
        assert (habit["name"], habit["category"]) == ("Learn Payments domain", "learning")
        duplicate = await h.client.post(
            "/api/productivity/habits", headers=me, json={"linkedTopic": "payments  DOMAIN"}
        )
        assert duplicate.status_code == 409
        topic = {t["topic"]: t for t in (await _overview(h, me))["learning"]}["Payments domain"]
        assert topic["status"] == "not_started" and topic["habitId"] == habit["id"]

        await h.client.put(_log_url(habit["id"], TODAY), headers=me, json={"minutes": 100})
        topic = {t["topic"]: t for t in (await _overview(h, me))["learning"]}["Payments domain"]
        assert topic["status"] == "ready_to_retest"
        assert (topic["sessionsSinceTest"], topic["minutesSinceTest"]) == (1, 100)

        # Retake after studying: everything right.
        perfect = [_correct_index(q) for q in test["questions"]]
        second = (await h.client.post(attempts, headers=me, json={"answers": perfect})).json()
        data = await _overview(h, me)
        topic = {t["topic"]: t for t in data["learning"]}["Payments domain"]
        assert (topic["previousPercent"], topic["latestPercent"], topic["delta"]) == (0, 100, 100)
        assert topic["status"] == "improved"  # tracked, retested, better

        trend = data["scoreTrend"]
        assert [p["percent"] for p in trend] == [
            first["data"]["percent"],
            second["data"]["percent"],
        ]
        assert trend[0]["learningMinutesBefore"] == 0
        assert trend[1]["learningMinutesBefore"] == 100  # the study between the two attempts
        assert trend[1]["learningSessionsBefore"] == 1
