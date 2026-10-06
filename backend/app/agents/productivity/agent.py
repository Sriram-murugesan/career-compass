from app.agents.base import AgentContext, AgentResult, AgentSpec, generate
from app.agents.productivity.prompt import SYSTEM_PROMPT
from app.agents.productivity.schema import ProductivityOutput


def _fallback(ctx: AgentContext) -> ProductivityOutput:
    goals = ctx.profile.get("goals") or ["land your next role"]
    return ProductivityOutput(
        focus_this_week=f"Make steady progress toward: {goals[0]}",
        suggestions=[
            "Send 5 targeted applications",
            "Do 2 mock interview sessions",
            "Update one resume bullet with a measurable result",
        ],
    )


async def run(ctx: AgentContext) -> AgentResult:
    output, used_llm = await generate(
        ctx,
        system=SYSTEM_PROMPT,
        schema=ProductivityOutput,
        fallback=lambda: _fallback(ctx),
        tier="fast",
    )
    return AgentResult(
        output=output, summary=f"Weekly focus: {output.focus_this_week}", used_llm=used_llm
    )


SPEC = AgentSpec(
    id="productivity",
    name="Productivity Tracker",
    description="Sets a weekly focus and small concrete actions from goals and activity.",
    run=run,
    keywords=("progress", "streak", "productivity", "track", "week", "weekly"),
)
