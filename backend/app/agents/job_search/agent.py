from app.agents.base import AgentContext, AgentResult, AgentSpec, MemoryFact, generate
from app.agents.job_search.prompt import SYSTEM_PROMPT
from app.agents.job_search.schema import JobMatch, JobSearchOutput


def _fallback(ctx: AgentContext) -> JobSearchOutput:
    roles = ctx.profile.get("target_roles") or ["Software Engineer"]
    return JobSearchOutput(
        matches=[
            JobMatch(
                role=role,
                company="(connect a jobs data source)",
                location=ctx.profile.get("location") or "Remote",
                match_score=80 - index * 5,
                reason="Matches a target role in your profile.",
            )
            for index, role in enumerate(roles[:3])
        ]
    )


async def run(ctx: AgentContext) -> AgentResult:
    output, used_llm = await generate(
        ctx, system=SYSTEM_PROMPT, schema=JobSearchOutput, fallback=lambda: _fallback(ctx)
    )
    roles = sorted({match.role for match in output.matches})
    facts = [MemoryFact("interest", f"Exploring roles: {', '.join(roles)}")] if roles else []
    return AgentResult(
        output=output,
        summary=f"Found {len(output.matches)} matching roles",
        facts=facts,
        used_llm=used_llm,
    )


SPEC = AgentSpec(
    id="job_search",
    name="Job Search Agent",
    description="Finds roles that fit the user's skills, interests and goals.",
    run=run,
    keywords=("job", "jobs", "search", "find", "role", "roles", "opening", "hiring"),
)
