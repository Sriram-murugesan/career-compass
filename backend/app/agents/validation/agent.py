import re
from typing import Any

from app.agents.base import AgentContext, AgentResult, AgentSpec, generate
from app.agents.validation.prompt import SYSTEM_PROMPT
from app.agents.validation.schema import ValidationCheck, ValidationOutput


def _fallback(ctx: AgentContext) -> ValidationOutput:
    """Rule-based audit, used when no LLM is configured."""
    resume: dict[str, Any] | None = ctx.inputs.get("resume")
    if not resume:
        return ValidationOutput(
            ats_score=0,
            checks=[
                ValidationCheck(
                    label="Resume draft", state="fail", note="No resume to validate yet"
                )
            ],
        )
    bullets: list[str] = resume.get("bullets") or []
    checks = [
        ValidationCheck(
            label="Summary present",
            state="pass" if resume.get("summary") else "fail",
            note="Opens with a targeted summary" if resume.get("summary") else "Add a summary",
        ),
        ValidationCheck(
            label="Enough impact bullets",
            state="pass" if len(bullets) >= 3 else "warn",
            note=f"{len(bullets)} bullets (aim for 3+)",
        ),
        ValidationCheck(
            label="Measurable results",
            state="pass" if any(re.search(r"\d", b) for b in bullets) else "warn",
            note="Add numbers: %, time saved, users, revenue",
        ),
        ValidationCheck(
            label="Keywords for target role",
            state="pass" if len(resume.get("keywords") or []) >= 5 else "warn",
            note=f"{len(resume.get('keywords') or [])} keywords found",
        ),
    ]
    score = round(100 * sum(c.state == "pass" for c in checks) / len(checks))
    return ValidationOutput(ats_score=score, checks=checks)


async def run(ctx: AgentContext) -> AgentResult:
    output, used_llm = await generate(
        ctx,
        system=SYSTEM_PROMPT,
        schema=ValidationOutput,
        fallback=lambda: _fallback(ctx),
        tier="fast",
    )
    issues = sum(check.state != "pass" for check in output.checks)
    return AgentResult(
        output=output,
        summary=f"ATS score {output.ats_score}, {issues} item(s) to review",
        used_llm=used_llm,
    )


SPEC = AgentSpec(
    id="validation",
    name="Validation Agent",
    description="Audits a resume draft for ATS readiness and lists what to fix.",
    run=run,
    reads=("resume",),
    keywords=("validate", "validation", "check", "ats", "audit", "review"),
)
