from typing import Any

from app.agents.base import AgentContext, AgentResult, AgentSpec, MemoryFact, generate
from app.agents.resume.prompt import SYSTEM_PROMPT
from app.agents.resume.schema import ResumeDraft


def _target_role(ctx: AgentContext) -> str:
    matches: list[dict[str, Any]] = (ctx.inputs.get("job_search") or {}).get("matches") or []
    if matches:
        return str(matches[0]["role"])
    roles = ctx.profile.get("target_roles") or []
    return str(roles[0]) if roles else "Software Engineer"


def _fallback(ctx: AgentContext) -> ResumeDraft:
    skills = [skill["name"] for skill in ctx.profile.get("skills") or []][:8]
    headline = ctx.profile.get("headline") or "Professional"
    return ResumeDraft(
        target_role=_target_role(ctx),
        summary=f"{headline} targeting {_target_role(ctx)} roles.",
        bullets=[
            f"Applied {skill} in production work (add a measurable result)." for skill in skills[:3]
        ],
        keywords=skills,
    )


async def run(ctx: AgentContext) -> AgentResult:
    output, used_llm = await generate(
        ctx, system=SYSTEM_PROMPT, schema=ResumeDraft, fallback=lambda: _fallback(ctx)
    )
    return AgentResult(
        output=output,
        summary=f"Drafted a resume tailored to {output.target_role}",
        facts=[MemoryFact("resume", f"Has a resume draft tailored to {output.target_role}")],
        used_llm=used_llm,
    )


SPEC = AgentSpec(
    id="resume",
    name="Resume Agent",
    description="Drafts an ATS-friendly resume, tailored to a role when one is known.",
    run=run,
    reads=("job_search",),
    keywords=("resume", "cv", "tailor", "rewrite"),
)
