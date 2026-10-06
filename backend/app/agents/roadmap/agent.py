from app.agents.base import AgentContext, AgentResult, AgentSpec, generate
from app.agents.roadmap.prompt import SYSTEM_PROMPT
from app.agents.roadmap.schema import Milestone, RoadmapOutput


def _fallback(ctx: AgentContext) -> RoadmapOutput:
    goal = (ctx.profile.get("goals") or ["Your next career step"])[0]
    return RoadmapOutput(
        goal=goal,
        milestones=[
            Milestone(
                title="Close the top skill gap",
                when="Weeks 1-3",
                note="Pick the gap the validation flagged first.",
            ),
            Milestone(
                title="Ship a portfolio piece",
                when="Weeks 4-6",
                note="Show the new skill on real work.",
            ),
            Milestone(
                title="Apply and interview",
                when="Weeks 7-10",
                note="Target roles from the job search.",
            ),
        ],
    )


async def run(ctx: AgentContext) -> AgentResult:
    output, used_llm = await generate(
        ctx, system=SYSTEM_PROMPT, schema=RoadmapOutput, fallback=lambda: _fallback(ctx)
    )
    return AgentResult(
        output=output,
        summary=f"{len(output.milestones)} milestones toward: {output.goal}",
        used_llm=used_llm,
    )


SPEC = AgentSpec(
    id="roadmap",
    name="Personalized Roadmap",
    description="Sequences skills and milestones from the current position to the goal.",
    run=run,
    reads=("validation",),
    keywords=("roadmap", "plan", "path", "learn", "milestone", "milestones", "skills"),
)
