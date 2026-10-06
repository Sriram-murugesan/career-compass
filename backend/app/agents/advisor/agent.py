from app.agents.advisor.prompt import SYSTEM_PROMPT
from app.agents.advisor.schema import AdvisorOutput
from app.agents.base import AgentContext, AgentResult, AgentSpec, generate


def _fallback(ctx: AgentContext) -> AdvisorOutput:
    known = ", ".join(sorted(ctx.inputs)) or "your profile"
    return AdvisorOutput(
        answer=f"Based on {known}: focus on one target role at a time and tailor each application.",
        next_steps=[
            "Confirm your top target role",
            "Tailor your resume to it",
            "Practise its interview questions",
        ],
    )


async def run(ctx: AgentContext) -> AgentResult:
    output, used_llm = await generate(
        ctx, system=SYSTEM_PROMPT, schema=AdvisorOutput, fallback=lambda: _fallback(ctx)
    )
    return AgentResult(output=output, summary="Answered with next steps", used_llm=used_llm)


SPEC = AgentSpec(
    id="advisor",
    name="Career Advisor",
    description="Answers open career questions using everything the other agents found.",
    run=run,
    reads=("job_search", "resume", "validation", "roadmap", "interview", "productivity"),
    keywords=("advice", "advise", "should", "career", "decide", "help"),
)
