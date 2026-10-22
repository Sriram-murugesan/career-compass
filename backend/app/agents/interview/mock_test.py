"""Mock interview test: multiple-choice questions written by the LLM for ONE role and
domain, validated and shuffled in code, graded by code (instantly, no LLM).

    generate_mock_test()   parallel LLM batches (large) → validated, de-duplicated questions
    grade()                answers → score, per-topic breakdown, weakest topics

The answer key is returned to the caller (the interview module stores it); only the
caller decides what the browser sees.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import zip_longest

from app.agents.base import LlmClient
from app.agents.interview.prompt import MOCK_TEST_PROMPT
from app.agents.interview.schema import MockQuestion, MockTestDraft
from app.llm.errors import LlmError

logger = logging.getLogger("app.agents.interview")

_BANNED_OPTIONS = ("all of the above", "none of the above", "both a and b", "all of these")
_DIFFICULTIES = {"easy", "medium", "hard"}
_WORD = re.compile(r"[a-z0-9+#.]{3,}")
NEAR_DUPLICATE = 0.5  # word-overlap (Jaccard) above which two questions test the same thing


def _words(text: str) -> frozenset[str]:
    return frozenset(_WORD.findall(text.lower()))


def _similar(a: frozenset[str], b: frozenset[str]) -> bool:
    return bool(a and b) and len(a & b) / len(a | b) >= NEAR_DUPLICATE


class MockTestUnavailable(Exception):
    """No usable test could be produced (no LLM keys, provider down, or bad output)."""


def _valid(draft_options: Sequence[str]) -> list[str] | None:
    options = [" ".join(str(o).split())[:200] for o in draft_options]
    if len(options) != 4 or any(not o for o in options):
        return None
    if len({o.casefold() for o in options}) != 4:
        return None
    if any(o.casefold().rstrip(".") in _BANNED_OPTIONS for o in options):
        return None
    return options


def validate_drafts(
    draft: MockTestDraft,
    *,
    count: int,
    rng: random.Random | None = None,
    seen: list[frozenset[str]] | None = None,
) -> list[MockQuestion]:
    """Keep well-formed, distinct questions; shuffle options (models favour A/B for the key).

    `seen` is shared across batches so two batches can't contribute the same question,
    or two near-identical ones ("render 10,000 transactions…" written twice).
    """
    rng = rng or random.Random()  # noqa: S311 - shuffling quiz options, not security
    seen = [] if seen is None else seen
    questions: list[MockQuestion] = []
    for item in draft.questions:
        text = " ".join(item.question.split())
        options = _valid(item.options)
        if not options or not 10 <= len(text) <= 600 or not 0 <= item.answer_index < 4:
            continue
        words = _words(f"{text} {' '.join(options)}")
        if any(_similar(words, other) for other in seen):
            continue
        seen.append(words)
        correct = options[item.answer_index]
        rng.shuffle(options)
        difficulty = (
            item.difficulty.lower() if item.difficulty.lower() in _DIFFICULTIES else "medium"
        )
        questions.append(
            MockQuestion(
                question=text,
                options=options,
                answer_index=options.index(correct),
                explanation=" ".join(item.explanation.split())[:500],
                topic=(" ".join(item.topic.split()) or "General")[:60],
                difficulty=difficulty,
            )
        )
        if len(questions) == count:
            break
    return questions


# ── Batches: written in parallel, so a 20-question test takes as long as 4 questions ──

BATCH_SIZE = 4


@dataclass(frozen=True)
class Batch:
    kind: str  # core | domain | judgement
    count: int
    focus: str


def _split(total: int) -> list[int]:
    """7 → [4, 3]; 8 → [4, 4]; 9 → [3, 3, 3]: even batches of at most BATCH_SIZE."""
    if total <= 0:
        return []
    parts = math.ceil(total / BATCH_SIZE)
    return [total // parts + (1 if i < total % parts else 0) for i in range(parts)]


def plan_batches(count: int, domain: str, skills: Sequence[str]) -> list[Batch]:
    """~50% core knowledge, ~30% domain scenarios, ~20% judgement; skills spread over the
    core batches so they don't all test the same thing."""
    core = math.ceil(count * 0.5)
    applied = round(count * 0.3)
    judgement = count - core - applied
    core_parts = _split(core)
    batches: list[Batch] = []
    for i, n in enumerate(core_parts):
        share = [s for j, s in enumerate(skills) if j % len(core_parts) == i]
        focus = (
            f"core technical knowledge for the role, centred on: {', '.join(share)}"
            if share
            else "core technical knowledge for the role"
        )
        batches.append(Batch("core", n, focus))
    place = f"set in the {domain} domain" if domain else "from real products this role ships"
    batches += [Batch("domain", n, f"applied scenarios {place}") for n in _split(applied)]
    batches += [
        Batch("judgement", n, "problem-solving and behavioural situational judgement")
        for n in _split(judgement)
    ]
    return batches


async def generate_mock_test(
    llm: LlmClient,
    *,
    role: str,
    domain: str,
    difficulty: str,
    count: int,
    context: str,
    skills: Sequence[str] = (),
) -> list[MockQuestion]:
    if not llm.available:
        raise MockTestUnavailable("Mock tests need the AI service: add an LLM key in backend/.env")
    header = (
        f"Role: {role}\nDomain: {domain or 'general / not specified'}\n"
        f"Difficulty: {difficulty}\nNumber of questions: {count}\n\n{context}"
    )
    batches = plan_batches(count, domain, skills)

    async def write(batch: Batch) -> MockTestDraft | None:
        request = (
            f"{header}\n\n## This batch\nIgnore the overall mix above. Write exactly "
            f"{batch.count + 1} questions, all of this kind: {batch.focus}."
        )
        try:
            return await llm.complete_json(
                system=MOCK_TEST_PROMPT, user=request, schema=MockTestDraft, tier="large"
            )
        except LlmError as exc:
            logger.warning(
                "mock test batch failed",
                extra={"context": {"kind": batch.kind, "error": type(exc).__name__}},
            )
            return None  # the other batches still count

    drafts = await asyncio.gather(*(write(batch) for batch in batches))
    seen: list[frozenset[str]] = []
    per_batch = [
        validate_drafts(draft, count=batch.count, seen=seen) if draft else []
        for batch, draft in zip(batches, drafts, strict=True)
    ]
    # One top-up round for any batch that came back short (slow/failed call, dropped
    # duplicates), so the test keeps its size and its core/domain/judgement balance.
    short = [
        (i, Batch(b.kind, b.count - len(kept), b.focus))
        for i, (b, kept) in enumerate(zip(batches, per_batch, strict=True))
        if len(kept) < b.count
    ]
    if short:
        refills = await asyncio.gather(*(write(batch) for _, batch in short))
        for (i, batch), draft in zip(short, refills, strict=True):
            if draft:
                per_batch[i] += validate_drafts(draft, count=batch.count, seen=seen)
    logger.info(
        "mock test batches",
        extra={
            "context": {
                "batches": [
                    {
                        "kind": b.kind,
                        "wanted": b.count,
                        "written": len(d.questions) if d else None,
                        "kept": len(kept),
                    }
                    for b, d, kept in zip(batches, drafts, per_batch, strict=True)
                ]
            }
        },
    )
    # Interleave (core, domain, judgement, core, …) so the test doesn't come in blocks.
    questions = [q for group in zip_longest(*per_batch) for q in group if q is not None]
    if len(questions) < max(3, math.ceil(count * 0.6)):
        if all(draft is None for draft in drafts):
            raise MockTestUnavailable("The AI service couldn't write a test right now")
        raise MockTestUnavailable("The AI returned too few usable questions; please try again")
    return questions[:count]


# ── Grading (pure, instant) ─────────────────────────────────────────────────


@dataclass(frozen=True)
class TopicScore:
    topic: str
    correct: int
    total: int

    @property
    def percent(self) -> int:
        return round(100 * self.correct / self.total) if self.total else 0


@dataclass
class Grade:
    correct: list[bool]
    score: int
    total: int
    percent: int
    label: str
    topics: list[TopicScore] = field(default_factory=list)
    weak_topics: list[str] = field(default_factory=list)


def grade_label(percent: int) -> str:
    if percent >= 85:
        return "Interview-ready"
    if percent >= 70:
        return "Strong"
    if percent >= 50:
        return "Developing"
    return "Needs practice"


def grade(questions: Sequence[MockQuestion], answers: Sequence[int | None]) -> Grade:
    padded = list(answers[: len(questions)]) + [None] * (len(questions) - len(answers))
    correct = [a == q.answer_index for q, a in zip(questions, padded, strict=True)]
    score, total = sum(correct), len(questions)
    percent = round(100 * score / total) if total else 0

    by_topic: dict[str, list[bool]] = {}
    for question, ok in zip(questions, correct, strict=True):
        by_topic.setdefault(question.topic, []).append(ok)
    topics = [TopicScore(t, sum(oks), len(oks)) for t, oks in by_topic.items()]
    topics.sort(key=lambda t: (t.percent, -t.total, t.topic))
    weak = [t.topic for t in topics if t.percent < 60][:3]
    return Grade(correct, score, total, percent, grade_label(percent), topics, weak)
