"""Pipeline B: one Gemini call per PR covering every AI check (B1-B12)."""

from __future__ import annotations

from dataclasses import dataclass, field

from gate.ai.client import GeminiClient
from gate.ai.config import GeminiSettings
from gate.ai.prompt_builder import response_schema, system_prompt, user_prompt
from gate.ai.validate import validate_ai_output
from gate.config import valid_rules
from gate.diff import DiffContext
from gate.report.finding import Finding, Signal


@dataclass
class AIResult:
    findings: list[Finding]
    dropped: list[tuple[dict, str]] = field(default_factory=list)
    cost: dict = field(default_factory=dict)
    model: str = ""


def review(
    ctx: DiffContext, deterministic: list[Finding] | None = None, signals: list[Signal] | None = None, client=None
) -> AIResult:
    client = client or GeminiClient(GeminiSettings.from_env())
    raw, model, usage = client.generate_json(
        system_prompt(), user_prompt(ctx, deterministic or [], signals or []), response_schema()
    )
    findings, dropped = validate_ai_output(raw, ctx, valid_rules())
    return AIResult(findings=findings, dropped=dropped, cost=usage.cost(), model=model)
