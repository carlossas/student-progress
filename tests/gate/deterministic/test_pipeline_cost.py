"""Per-run pipeline cost (AI + CI minutes), logged by the report job."""

from gate.report.cost import JobTime, billed_minutes, pipeline_cost, render

AI_META = {
    "model": "gemini-3.8-flash",
    "requests": 1,
    "cached": False,
    "cost": {"prompt_tokens": 4049, "output_tokens": 123, "thinking_tokens": 0, "total_usd": 0.003498},
}
JOBS = [JobTime("deterministic", 95), JobTime("smoke", 140), JobTime("ai", 30), JobTime("report", 12)]


def test_pipeline_cost():
    # GitHub bills each job rounded up to the minute: 2 + 3 + 1 + 1 = 7 runner-minutes.
    assert [billed_minutes(j.seconds) for j in JOBS] == [2, 3, 1, 1]
    cost = pipeline_cost(AI_META, JOBS, usd_per_minute=0.006)
    assert cost["ci_minutes"] == 7 and cost["ci_usd"] == 0.042
    assert cost["ai_usd"] == 0.003498 and cost["total_usd"] == 0.045498
    line = render(cost)
    assert line.startswith("Pipeline cost for this run: $0.0455")
    assert "AI $0.0035 (1 request(s), 4049 in / 123 out / 0 thinking tokens, gemini-3.8-flash)" in line
    assert "CI 7 runner-min $0.0420" in line

    # Re-run of an unchanged PR: the AI review comes from cache and costs nothing.
    cached = pipeline_cost({**AI_META, "cached": True}, JOBS, 0.006)
    assert cached["ai_usd"] == 0 and "AI served from cache $0" in render(cached)

    # PR into a feature branch: no AI job.
    no_ai = pipeline_cost(None, JOBS[:2] + JOBS[3:], 0.006)
    assert no_ai["ai_usd"] == 0 and no_ai["ci_minutes"] == 6 and "AI not run $0" in render(no_ai)
