"""Job Search agent.

With a job board configured (Jobicy + Remotive by default, optionally Adzuna):
  1. plan      — request + profile → 1-2 job-title queries + a location   (LLM, fast; rule fallback)
  2. retrieve  — a wide pool of real postings, de-duplicated
  3. pre-rank  — code scores every posting on keyword relevance + freshness and keeps the
                 best MAX_CANDIDATES, so the model reads the strongest pool, not arrival order
  4. re-rank   — the LLM scores each strong candidate on a rubric (skills, experience,
                 location, goals) BY NUMBER only; code computes the final score from it
                 (weights + recency), checks skills against the real profile/posting, and
                 keeps the top 5                         (LLM, large; keyword fallback)
  5. return    — company, location, salary, date and apply link come from the posting itself,
                 so the model can't invent an employer or a link
Without a board (or if it's down): role-type suggestions, clearly marked "suggested".
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import UTC, datetime

from app.agents.base import (
    AgentContext,
    AgentResult,
    AgentSpec,
    JobBoardUnavailable,
    JobListing,
    MemoryFact,
    generate,
)
from app.agents.job_search.prompt import RANKING_PROMPT, SEARCH_PLAN_PROMPT, SUGGESTION_PROMPT
from app.agents.job_search.schema import (
    FitBreakdown,
    JobAssessment,
    JobMatch,
    JobSearchOutput,
    Ranking,
    SearchPlan,
)
from app.llm.errors import LlmError

PER_QUERY = 20  # postings requested per query (per board)
MAX_CANDIDATES = 25  # best pre-ranked postings shown to the re-ranking model
TOP_MATCHES = 5
MIN_SCORE = 35  # weaker picks are dropped, unless nothing else is left

# Final score = weighted rubric. Skills matter most; location is a hard-ish constraint.
WEIGHTS = {"skills": 0.40, "experience": 0.25, "location": 0.20, "goals": 0.15}
UNLIKELY_CAP = 45  # can't apply from the user's region → never ranks as a strong match

_WORD = re.compile(r"[a-z0-9+#.]+")
_GENERIC = {"and", "or", "the", "of", "in", "for", "to", "with", "a", "an", "remote"}
_NO_PLACE = {"remote", "anywhere", "worldwide", "global", "any", "flexible"}


def _now() -> datetime:
    return datetime.now(UTC)


def _words(text: str) -> set[str]:
    words = (word.strip(".") for word in _WORD.findall(text.lower()))
    return {word for word in words if len(word) > 1 and word not in _GENERIC}


def _skill_names(ctx: AgentContext) -> list[str]:
    return [str(s["name"]) for s in ctx.profile.get("skills") or [] if s.get("name")]


# ── 1. Plan the search ──────────────────────────────────────────────────────


def _rule_plan(ctx: AgentContext) -> SearchPlan:
    profile = ctx.profile
    roles = [r for r in profile.get("target_roles") or [] if r][:2]
    if not roles and profile.get("headline"):
        roles = [str(profile["headline"]).split(",")[0][:60]]
    location = (
        "" if profile.get("work_preference") == "Remote" else str(profile.get("location") or "")
    )
    return SearchPlan(queries=roles or ["software developer"], location=location)


async def _plan(ctx: AgentContext) -> tuple[SearchPlan, bool]:
    if not ctx.llm.available:
        return _rule_plan(ctx), False
    try:
        plan = await ctx.llm.complete_json(
            system=SEARCH_PLAN_PROMPT, user=ctx.rendered, schema=SearchPlan, tier="fast"
        )
        queries = [q.strip() for q in plan.queries if q.strip()]
        location = plan.location.strip()
        if location.lower() in _NO_PLACE:
            location = ""  # "Remote" is a work mode, not a place to search
        if queries:
            return SearchPlan(queries=queries[:2], location=location), True
    except LlmError:
        pass
    return _rule_plan(ctx), False


# ── 3. Pre-rank (code) ──────────────────────────────────────────────────────


def _age_days(job: JobListing) -> int | None:
    if not job.posted_at:
        return None
    try:
        posted = datetime.fromisoformat(job.posted_at.replace("Z", "+00:00"))
    except ValueError:
        return None
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=UTC)
    return max(0, (_now() - posted).days)


def _recency_adjustment(job: JobListing) -> int:
    """Fresh postings get a nudge; stale ones (often filled) a penalty."""
    days = _age_days(job)
    if days is None:
        return 0
    if days <= 3:
        return 3
    if days <= 14:
        return 0
    if days <= 30:
        return -3
    return -8


@dataclass(frozen=True)
class _Relevance:
    score: float
    skill_hits: list[str]


def _relevance(ctx: AgentContext, job: JobListing, query_words: set[str]) -> _Relevance:
    title = _words(job.title)
    body = f"{job.title} {job.description}".lower()
    skill_hits = [name for name in _skill_names(ctx) if name.lower() in body]
    score = 3 * len(query_words & title) + 2 * len(skill_hits) + _recency_adjustment(job) / 3
    return _Relevance(score=score, skill_hits=skill_hits)


def _pre_rank(
    ctx: AgentContext, listings: list[JobListing], plan: SearchPlan
) -> list[tuple[JobListing, _Relevance]]:
    query_words: set[str] = set()
    for text in [*plan.queries, *(ctx.profile.get("target_roles") or [])]:
        query_words |= _words(str(text))
    scored = [(job, _relevance(ctx, job, query_words)) for job in listings]
    # Stable sort: equal relevance keeps the boards' own order.
    scored.sort(key=lambda row: row[1].score, reverse=True)
    return scored[:MAX_CANDIDATES]


# ── 4. Re-rank (LLM rubric → score computed in code) ────────────────────────


def _listing_table(listings: list[JobListing]) -> str:
    rows = []
    for i, job in enumerate(listings):
        parts = [f"[{i}] {job.title} — {job.company} — {job.location or 'location n/a'}"]
        days = _age_days(job)
        if days is not None:
            parts.append(f"posted {days}d ago")
        if job.salary:
            parts.append(f"salary {job.salary}")
        if job.contract:
            parts.append(job.contract)
        rows.append(" | ".join(parts) + f"\n    {job.description[:400]}")
    return "\n".join(rows)


def _final_score(fit: FitBreakdown, job: JobListing, eligibility: str) -> int:
    values = fit.model_dump()
    weighted = sum(float(values[dimension]) * weight for dimension, weight in WEIGHTS.items())
    score = round(weighted) + _recency_adjustment(job)
    if eligibility == "unlikely":
        score = min(score, UNLIKELY_CAP)
    return max(0, min(100, score))


def _clean_skills(
    ctx: AgentContext, job: JobListing, pick: JobAssessment
) -> tuple[list[str], list[str]]:
    """Keep only skills that are really on the profile / really in the posting."""
    posting = f"{job.title} {job.description}".lower()
    profile_skills = {name.lower(): name for name in _skill_names(ctx)}

    matched: list[str] = []
    for raw in pick.matched_skills:
        key = raw.strip().lower()
        if not key or key not in posting:  # must be asked for in the posting the model saw
            continue
        # With skills on the profile, it must also be one of them (in the profile's spelling).
        name = profile_skills.get(key) if profile_skills else raw.strip()
        if name and name not in matched:
            matched.append(name)

    missing: list[str] = []
    for raw in pick.missing_skills:
        skill = raw.strip()
        key = skill.lower()
        if skill and key in posting and key not in profile_skills and skill not in missing:
            missing.append(skill[:40])
    return matched[:6], missing[:4]


def _match(job: JobListing, **detail: object) -> JobMatch:
    return JobMatch.model_validate(
        {
            "role": job.title,
            "company": job.company,
            "location": job.location,
            "apply_url": job.apply_url,
            "posted_at": job.posted_at,
            "salary": job.salary,
            "source": job.source,
            **detail,
        }
    )


def _keyword_rank(
    ctx: AgentContext, candidates: list[tuple[JobListing, _Relevance]]
) -> list[JobMatch]:
    """No-LLM fallback: the pre-rank order, explained by the skills each posting mentions."""
    matches = []
    for job, relevance in candidates[:TOP_MATCHES]:
        hits = relevance.skill_hits
        matches.append(
            _match(
                job,
                match_score=max(0, min(95, 50 + 10 * len(hits) + _recency_adjustment(job))),
                reason=f"Mentions {', '.join(hits[:4])}." if hits else "Matches your search.",
                matched_skills=hits[:6],
            )
        )
    return matches


async def _rerank(
    ctx: AgentContext, candidates: list[tuple[JobListing, _Relevance]]
) -> tuple[list[JobMatch], bool]:
    listings = [job for job, _ in candidates]
    if ctx.llm.available:
        try:
            ranking = await ctx.llm.complete_json(
                system=RANKING_PROMPT,
                user=f"{ctx.rendered}\n\n## Job postings\n{_listing_table(listings)}",
                schema=Ranking,
                tier="large",
            )
            scored: list[tuple[int, int, JobMatch]] = []
            seen: set[int] = set()
            for order, pick in enumerate(ranking.picks):
                # Only numbers that exist, each once: the model can't add a posting.
                if not 0 <= pick.index < len(listings) or pick.index in seen:
                    continue
                seen.add(pick.index)
                job = listings[pick.index]
                fit = FitBreakdown(
                    skills=pick.skills_fit,
                    experience=pick.experience_fit,
                    location=pick.location_fit,
                    goals=pick.goals_fit,
                )
                matched, missing = _clean_skills(ctx, job, pick)
                score = _final_score(fit, job, pick.eligibility)
                match = _match(
                    job,
                    match_score=score,
                    reason=pick.reason.strip()[:300] or "Fits your profile.",
                    fit=fit,
                    eligibility=pick.eligibility,
                    matched_skills=matched,
                    missing_skills=missing,
                    next_step=pick.next_step.strip()[:200],
                )
                scored.append((score, -order, match))
            if scored:
                scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
                strong = [m for score, _, m in scored if score >= MIN_SCORE]
                return (strong or [scored[0][2]])[:TOP_MATCHES], True
        except LlmError:
            pass
    return _keyword_rank(ctx, candidates), False


# ── Suggestions (no live data) ──────────────────────────────────────────────


def _suggestion_fallback(ctx: AgentContext) -> JobSearchOutput:
    plan = _rule_plan(ctx)
    return JobSearchOutput(
        matches=[
            JobMatch(
                role=role,
                company="Various employers",
                location=plan.location or "Remote / flexible",
                match_score=80 - i * 5,
                reason="Matches a target role in your profile.",
            )
            for i, role in enumerate(plan.queries)
        ]
    )


async def _suggest(ctx: AgentContext, notice: str) -> tuple[JobSearchOutput, bool]:
    output, used_llm = await generate(
        ctx,
        system=SUGGESTION_PROMPT,
        schema=JobSearchOutput,
        fallback=lambda: _suggestion_fallback(ctx),
    )
    # Whatever the model returned, these are suggestions — never present them as postings.
    output.mode = "suggested"
    output.notice = notice
    output.ranking = ""
    output.considered = 0
    for match in output.matches:
        match.apply_url = match.posted_at = match.source = None
        match.fit = match.eligibility = None  # no posting to assess
    return output, used_llm


# ── The agent ───────────────────────────────────────────────────────────────


async def _search_live(ctx: AgentContext) -> tuple[JobSearchOutput, bool]:
    board = ctx.job_board
    if board is None:
        raise JobBoardUnavailable("No job board configured")
    plan, planned_with_llm = await _plan(ctx)
    query_text = " / ".join(plan.queries) + (f" in {plan.location}" if plan.location else "")

    batches = await asyncio.gather(
        *(board.search(q, plan.location, limit=PER_QUERY) for q in plan.queries)
    )
    listings: list[JobListing] = []
    seen: set[str] = set()
    for batch in batches:
        for job in batch:
            key = job.apply_url or job.id
            if key not in seen:
                seen.add(key)
                listings.append(job)

    if not listings:
        return (
            JobSearchOutput(
                mode="live",
                query=query_text,
                notice="No live postings matched. Try a broader role or another location.",
            ),
            planned_with_llm,
        )

    candidates = _pre_rank(ctx, listings, plan)
    matches, ranked_with_llm = await _rerank(ctx, candidates)
    notice = ""
    if not ranked_with_llm:
        notice = "Ranked by keyword match (the AI ranker was unavailable)."
    elif matches and all(m.eligibility == "unlikely" for m in matches):
        notice = "These postings hire mostly outside your region. Try a broader search."
    elif len(matches) < 3:
        notice = (
            f"Only {len(matches)} of {len(listings)} postings fit your profile well. "
            "Try a broader role, or check back later."
        )
    output = JobSearchOutput(
        mode="live",
        query=query_text,
        notice=notice,
        ranking="ai" if ranked_with_llm else "keyword",
        considered=len(listings),
        matches=matches,
    )
    return output, planned_with_llm or ranked_with_llm


async def run(ctx: AgentContext) -> AgentResult:
    if ctx.job_board is None:
        output, used_llm = await _suggest(
            ctx, "Role suggestions only — no job-listings service is connected."
        )
    else:
        try:
            output, used_llm = await _search_live(ctx)
        except JobBoardUnavailable:
            output, used_llm = await _suggest(
                ctx, "Live job search is unavailable right now — showing role suggestions instead."
            )

    roles = sorted({m.role for m in output.matches})[:5]
    facts = [MemoryFact("interest", f"Exploring roles: {', '.join(roles)}")] if roles else []
    count = len(output.matches)
    summary = (
        f"Found {count} live posting{'s' if count != 1 else ''} for {output.query}"
        if output.mode == "live"
        else f"Suggested {count} role type{'s' if count != 1 else ''} (no live listings)"
    )
    return AgentResult(output=output, summary=summary, facts=facts, used_llm=used_llm)


SPEC = AgentSpec(
    id="job_search",
    name="Job Search Agent",
    description=(
        "Searches live job postings (when a job board is connected), re-ranks them against "
        "the user's skills, experience, location and goals, and explains each fit, with "
        "apply links."
    ),
    run=run,
    keywords=("job", "jobs", "search", "find", "role", "roles", "opening", "hiring"),
)
