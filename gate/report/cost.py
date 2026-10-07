"""Full cost of one gate run on a PR: Gemini spend + GitHub Actions runner minutes.

AI: real token counts from every Gemini request of the run (ai-meta.json), priced with
gate/ai/pricing.py; $0 when the review was served from cache.
CI: each job's wall time, rounded up to whole minutes per job (how GitHub bills), times the
Linux 2-core rate. Public repositories and the plan's included minutes don't pay this; the
figure is the list-price value of the compute.
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

log = logging.getLogger("gate.cost")

# GitHub-hosted Linux 2-core x64, per minute, 2026 list price (all-in, including the platform charge).
DEFAULT_ACTIONS_USD_PER_MINUTE = 0.006


@dataclass(frozen=True)
class JobTime:
    name: str
    seconds: float


def actions_usd_per_minute() -> float:
    return float(os.environ.get("GATE_ACTIONS_USD_PER_MINUTE", "").strip() or DEFAULT_ACTIONS_USD_PER_MINUTE)


def billed_minutes(seconds: float) -> int:
    return math.ceil(seconds / 60) if seconds > 0 else 0


def pipeline_cost(ai_meta: dict | None, jobs: list[JobTime], usd_per_minute: float) -> dict:
    """Pure: the cost breakdown of one run."""
    ai = (ai_meta or {}).get("cost", {})
    cached = bool((ai_meta or {}).get("cached"))
    ai_usd = 0.0 if cached else float(ai.get("total_usd", 0.0))
    minutes = sum(billed_minutes(j.seconds) for j in jobs)
    ci_usd = minutes * usd_per_minute
    return {
        "ai_ran": ai_meta is not None,
        "ai_model": (ai_meta or {}).get("model", ""),
        "ai_requests": int((ai_meta or {}).get("requests", 1 if ai_meta else 0)),
        "ai_cached": cached,
        "ai_input_tokens": int(ai.get("prompt_tokens", 0)),
        "ai_output_tokens": int(ai.get("output_tokens", 0)),
        "ai_thinking_tokens": int(ai.get("thinking_tokens", 0)),
        "ai_usd": round(ai_usd, 6),
        "ci_minutes": minutes,
        "ci_usd_per_minute": usd_per_minute,
        "ci_usd": round(ci_usd, 6),
        "jobs": [asdict(j) for j in jobs],
        "total_usd": round(ai_usd + ci_usd, 6),
    }


def render(cost: dict) -> str:
    if not cost["ai_ran"]:
        ai = "AI not run $0"
    elif cost["ai_cached"]:
        ai = "AI served from cache $0"
    else:
        ai = (
            f"AI ${cost['ai_usd']:.4f} ({cost['ai_requests']} request(s), {cost['ai_input_tokens']} in / "
            f"{cost['ai_output_tokens']} out / {cost['ai_thinking_tokens']} thinking tokens, {cost['ai_model']})"
        )
    ci = f"CI {cost['ci_minutes']} runner-min ${cost['ci_usd']:.4f}" if cost["jobs"] else "CI time n/a"
    return f"Pipeline cost for this run: ${cost['total_usd']:.4f} = {ai} + {ci}"


def _seconds(job: dict, now: datetime) -> float:
    start = job.get("started_at")
    if not start:
        return 0.0
    end = job.get("completed_at")
    parse = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))  # noqa: E731
    return max((parse(end) if end else now) - parse(start), now - now).total_seconds()


def jobs_from_github(gh, run_id: str) -> list[JobTime]:
    """Wall time of every job of this workflow run (the running report job counts up to now)."""
    data = gh.request("GET", f"/repos/{gh.repo}/actions/runs/{run_id}/jobs?per_page=100") or {}
    now = datetime.now(UTC)
    return [JobTime(j["name"], round(_seconds(j, now), 1)) for j in data.get("jobs", []) if j.get("started_at")]
