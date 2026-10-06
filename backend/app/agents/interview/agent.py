from typing import Any

from app.agents.base import AgentContext, AgentResult, AgentSpec, generate
from app.agents.interview.prompt import SYSTEM_PROMPT
from app.agents.interview.schema import InterviewOutput


def _fallback(ctx: AgentContext) -> InterviewOutput:
    matches: list[dict[str, Any]] = (ctx.inputs.get("job_search") or {}).get("matches") or []
    role = (
        matches[0]["role"]
        if matches
        else (ctx.profile.get("target_roles") or ["your target role"])[0]
    )
    return InterviewOutput(
        focus=str(role),
        questions=[
            "Walk me through a project you are proud of, end to end.",
            "Tell me about a time you disagreed with a teammate. What happened?",
            f"What would your first 90 days as a {role} look like?",
        ],
    )


async def run(ctx: AgentContext) -> AgentResult:
    output, used_llm = await generate(
        ctx,
        system=SYSTEM_PROMPT,
        schema=InterviewOutput,
        fallback=lambda: _fallback(ctx),
        tier="fast",
    )
    return AgentResult(
        output=output,
        summary=f"{len(output.questions)} practice questions for {output.focus}",
        used_llm=used_llm,
    )


SPEC = AgentSpec(
    id="interview",
    name="Interview Preparation",
    description="Writes practice interview questions for the target role.",
    run=run,
    reads=("job_search", "resume"),
    keywords=("interview", "mock", "practice", "questions"),
)
