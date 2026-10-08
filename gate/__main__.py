"""Quality gate CLI.

    python -m gate all [--fix] [--no-ai]          # everything a developer needs, one final verdict
    python -m gate lint [--fix]                   # ruff (repo config + gate format policy)
python -m gate check --base main [--ai]       # everything, locally, against a base branch
python -m gate precommit                      # husky pre-commit: fast checks on staged files
python -m gate prepush [--base origin/develop]  # husky pre-push: tests + changed-line coverage
python -m gate deterministic|smoke|ai|report|override   # CI steps (see quality-gate.yml)
python -m gate eval [--ai]                    # golden-set evaluation -> EVAL.md
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from gate.config import SEVERITIES
from gate.diff import DiffContext, default_base
from gate.report.actions import decide, render_summary
from gate.report.finding import Finding, read_findings, read_signals, sort_findings, write_json
from gate.report.merge import dedupe

log = logging.getLogger("gate")
COLOR = {"critical": "\033[91m", "high": "\033[31m", "medium": "\033[33m", "low": "\033[36m"}


def print_findings(findings: list[Finding], stream=sys.stdout) -> None:
    color = stream.isatty() and os.environ.get("NO_COLOR") is None
    for f in sort_findings(findings):
        sev = f"{COLOR[f.severity]}{f.severity:8}\033[0m" if color else f"{f.severity:8}"
        stream.write(
            f"{sev} {f.rule:10} {f.location}\n         {f.message}\n         fix: {f.suggestion.splitlines()[0]}\n"
        )
    counts = ", ".join(f"{sum(f.severity == s for f in findings)} {s}" for s in SEVERITIES)
    stream.write(f"quality gate: {counts}\n")


def _pr_meta() -> dict:
    return {"pr_title": os.environ.get("PR_TITLE", ""), "pr_body": os.environ.get("PR_BODY", "")}


def _write_errors(out: Path, name: str, errors: list[str]) -> None:
    (out / f"errors-{name}.json").write_text(json.dumps(errors, indent=2), encoding="utf-8")


# --- commands -------------------------------------------------------------------------


def cmd_deterministic(args) -> int:
    from gate.deterministic import runner

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ctx = DiffContext.from_refs(Path(args.repo), args.base, args.head, **_pr_meta())
    result = runner.run(ctx, with_tests=not args.no_tests, out_dir=out / "tests")
    write_json(out / "findings-deterministic.json", result.findings)
    write_json(out / "signals.json", result.signals)
    _write_errors(out, "deterministic", result.errors)
    print_findings(result.findings)
    for error in result.errors:
        print(f"::error::gate check crashed: {error}")
    return 0


def cmd_smoke(args) -> int:
    from gate.deterministic import readme_smoke

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    findings = readme_smoke.run(Path(args.repo))
    write_json(out / "findings-smoke.json", findings)
    print_findings(findings)
    return 0


def _ai_cache_dir(args) -> Path | None:
    value = getattr(args, "cache_dir", None) or os.environ.get("GATE_AI_CACHE_DIR", "")
    return Path(value) if value else None


def cmd_ai(args) -> int:
    from gate.ai.review import review, review_key

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    source = Path(args.inputs)
    deterministic = (
        read_findings(source / "findings-deterministic.json")
        if (source / "findings-deterministic.json").exists()
        else []
    )
    ctx = DiffContext.from_refs(Path(args.repo), args.base, args.head, **_pr_meta())
    signals = read_signals(source / "signals.json")
    if args.key_only:
        print(review_key(ctx, deterministic, signals))
        return 0
    try:
        result = review(ctx, deterministic, signals, cache_dir=_ai_cache_dir(args))
    except Exception as e:  # noqa: BLE001 - becomes a blocking gate error in the report
        _write_errors(out, "ai", [f"AI review failed: {e}"])
        print(f"::error::AI review failed: {e}")
        return 1
    write_json(out / "findings-ai.json", result.findings)
    meta = {
        "model": result.model,
        "cost": result.cost,
        "cached": result.cached,
        "cache_key": result.cache_key,
        "requests": result.requests,
        "dropped": [{"item": i, "reason": r} for i, r in result.dropped],
    }
    (out / "ai-meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    _write_errors(out, "ai", [])
    print_findings(result.findings)
    print(_cost_line(result.model, result.cost, result.cached, len(result.dropped)))
    return 0


def _cost_line(model: str, cost: dict, cached: bool, dropped: int) -> str:
    if cached:
        return f"AI review: `{model}` · served from cache (unchanged PR) · $0 (first run cost ${cost.get('original_total_usd', 0):.4f}) · {dropped} invalid AI finding(s) dropped"
    approx = "" if cost.get("rate_known") else " (approximate rate)"
    return (
        f"AI review: `{model}` · {cost['prompt_tokens']} in ({cost['cached_tokens']} from prompt cache) / "
        f"{cost['output_tokens']} out / {cost['thinking_tokens']} thinking tokens · ${cost['total_usd']:.4f}{approx} · "
        f"{dropped} invalid AI finding(s) dropped"
    )


def _collect(source: Path, needs: dict) -> tuple[list[Finding], list[str], list[str]]:
    findings, errors, extra = [], [], []
    for name in ("deterministic", "smoke", "ai"):
        path = source / f"findings-{name}.json"
        if path.exists():
            findings += read_findings(path)
        error_file = source / f"errors-{name}.json"
        if error_file.exists():
            errors += json.loads(error_file.read_text(encoding="utf-8"))
    for job, info in needs.items():
        result = (info or {}).get("result")
        if result in ("failure", "cancelled") and not any(job in e or "AI review" in e for e in errors):
            errors.append(f"job `{job}` {result} before reporting its findings")
    meta = source / "ai-meta.json"
    if meta.exists():
        data = json.loads(meta.read_text(encoding="utf-8"))
        line = _cost_line(data["model"], data["cost"], data.get("cached", False), len(data["dropped"]))
        extra.append(f"<sub>{line}</sub>")
    elif (needs.get("ai") or {}).get("result") == "skipped":
        extra.append("<sub>AI review skipped: it runs only for PRs into `develop` and `main`.</sub>")
    return dedupe(findings), errors, extra


def _run_cost(source: Path, publish: bool) -> dict:
    """Cost of this gate run (AI + CI minutes), logged and saved as cost.json."""
    from gate.report import cost as costs

    meta_file = source / "ai-meta.json"
    ai_meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else None
    jobs: list[costs.JobTime] = []
    run_id = os.environ.get("GITHUB_RUN_ID")
    if publish and run_id:
        from gate.report.github import GitHub, GitHubError

        try:
            jobs = costs.jobs_from_github(GitHub(), run_id)
        except GitHubError as e:  # cost is informational: log it, never block on it
            log.warning("could not read job timings for the cost line: %s", e)
    result = costs.pipeline_cost(ai_meta, jobs, costs.actions_usd_per_minute())
    (source / "cost.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    line = costs.render(result)
    print(line)
    print(f"::notice title=Quality gate cost::{line}")
    return result


def cmd_report(args) -> int:
    from gate.report.cost import render

    source = Path(args.inputs)
    needs = json.loads(args.needs) if args.needs else {}
    findings, errors, extra = _collect(source, needs)
    extra.append(f"<sub>{render(_run_cost(source, args.publish))}</sub>")
    base = args.base_ref or os.environ.get("GITHUB_BASE_REF", "") or "develop"
    decision = decide(findings, mode=args.mode, gate_errors=errors, base=base)
    run_url = os.environ.get("GITHUB_RUN_URL")
    summary = render_summary(
        findings, decision, args.mode, extra + ([f"<sub>[Run logs]({run_url})</sub>"] if run_url else [])
    )
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write(summary + "\n")
    for f in findings:
        if f.severity == "critical":
            loc = f"file={f.file}" + (f",line={f.line}" if f.line else "")
            print(f"::error {loc},title={f.rule} critical::{f.message}")
    for e in errors:
        print(f"::error title=quality gate error::{e}")
    print_findings(findings)
    if args.publish:
        from gate.report.github import GitHub, publish

        publish(GitHub(), args.pr, args.sha, findings, decision, summary, run_url)
    return decision.exit_code


def cmd_override(args) -> int:
    from gate.report.github import GitHub
    from gate.report.override import handle

    body = Path(args.body_file).read_text(encoding="utf-8")
    result = handle(GitHub(), args.pr, args.user, body, os.environ.get("GITHUB_RUN_URL"))
    print(result.message)
    return 0 if result.accepted else 1


def _local_exit(findings: list[Finding], errors: list[str]) -> int:
    for e in errors:
        print(f"gate error: {e}", file=sys.stderr)
    return 1 if errors or any(f.severity in ("critical", "high") for f in findings) else 0


def cmd_precommit(args) -> int:
    from gate.deterministic import runner

    ctx = DiffContext.from_staged(Path(args.repo))
    if not ctx.files():
        return 0
    result = runner.run(ctx, fast_only=True, with_tests=False)
    if result.findings:
        print_findings(result.findings)
    code = _local_exit(result.findings, result.errors)
    if code:
        print("pre-commit blocked: fix the critical/high findings above (AGENTS.md).", file=sys.stderr)
    return code


def cmd_prepush(args) -> int:
    from gate.deterministic import tests_runner

    repo = Path(args.repo)
    base = args.base or default_base(repo)
    findings = tests_runner.run(DiffContext.from_refs(repo, base))
    if findings:
        print_findings(findings)
    return _local_exit(findings, [])


def cmd_check(args) -> int:
    from gate.deterministic import runner

    ctx = DiffContext.from_refs(Path(args.repo), args.base, args.head)
    result = runner.run(ctx, with_tests=not args.no_tests)
    findings, errors = result.findings, result.errors
    if args.ai:
        from gate.ai.review import review

        ai = review(ctx, findings, result.signals, cache_dir=Path(args.repo) / ".gate-cache" / "ai")
        findings = dedupe(findings + ai.findings)
        print(_cost_line(ai.model, ai.cost, ai.cached, len(ai.dropped)))
    print_findings(findings)
    return _local_exit(findings, errors)


def cmd_all(args) -> int:
    from gate.local import main_all

    return main_all(args)


def cmd_lint(args) -> int:
    from gate.local import main_lint

    return main_lint(args)


def cmd_eval(args) -> int:
    from gate.eval.run_eval import main

    return main(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m gate", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def repo_args(p, base_required=True):
        p.add_argument("--repo", default=".", help="checkout to analyze (default: .)")
        p.add_argument("--base", required=base_required, help="base ref (e.g. main or a SHA)")
        p.add_argument("--head", default="HEAD")

    p = sub.add_parser("all", help="pre-commit + lint + tests + both pipelines, one final verdict")
    p.add_argument("--repo", default=".")
    p.add_argument("--base", default="", help="branch your PR targets (default: origin/develop, origin/main, main)")
    p.add_argument("--fix", action="store_true", help="let ruff fix lint and formatting first")
    p.add_argument("--no-ai", action="store_true", help="skip the Gemini review even if a key is set")
    p.set_defaults(fn=cmd_all)

    p = sub.add_parser("lint", help="ruff check (repo config) + format check on changed files")
    p.add_argument("--repo", default=".")
    p.add_argument("--base", default="")
    p.add_argument("--fix", action="store_true")
    p.set_defaults(fn=cmd_lint)

    p = sub.add_parser("check", help="run the gate locally against a base branch")
    repo_args(p)
    p.add_argument("--ai", action="store_true", help="also run the Gemini review (costs credits)")
    p.add_argument("--no-tests", action="store_true")
    p.set_defaults(fn=cmd_check)

    p = sub.add_parser("deterministic", help="CI: Pipeline A")
    repo_args(p)
    p.add_argument("--out", default="gate-out")
    p.add_argument("--no-tests", action="store_true")
    p.set_defaults(fn=cmd_deterministic)

    p = sub.add_parser("smoke", help="CI: README smoke test (A15)")
    p.add_argument("--repo", default=".")
    p.add_argument("--out", default="gate-out")
    p.set_defaults(fn=cmd_smoke)

    p = sub.add_parser("ai", help="CI: Pipeline B (Gemini)")
    repo_args(p)
    p.add_argument("--in", dest="inputs", default="gate-out")
    p.add_argument("--out", default="gate-out")
    p.add_argument("--cache-dir", default="", help="AI result cache (default: $GATE_AI_CACHE_DIR; none if unset)")
    p.add_argument("--key-only", action="store_true", help="print the cache key and exit (no API call)")
    p.set_defaults(fn=cmd_ai)

    p = sub.add_parser("report", help="CI: merge findings, apply the severity policy, publish")
    p.add_argument("--in", dest="inputs", default="gate-out")
    p.add_argument("--mode", default=os.environ.get("GATE_MODE") or "shadow", choices=["enforce", "shadow"])
    p.add_argument("--needs", default="", help="toJSON(needs) from the workflow")
    p.add_argument(
        "--base-ref", default="", help="the PR's base branch; names the status checks (default: $GITHUB_BASE_REF)"
    )
    p.add_argument("--publish", action="store_true")
    p.add_argument("--pr", type=int)
    p.add_argument("--sha")
    p.set_defaults(fn=cmd_report)

    p = sub.add_parser("override", help="CI: handle a /gate-override comment")
    p.add_argument("--pr", type=int, required=True)
    p.add_argument("--user", required=True)
    p.add_argument("--body-file", required=True)
    p.set_defaults(fn=cmd_override)

    p = sub.add_parser("precommit", help="hook: fast checks on staged files")
    p.add_argument("--repo", default=".")
    p.set_defaults(fn=cmd_precommit)

    p = sub.add_parser("prepush", help="hook: tests + changed-line coverage")
    p.add_argument("--repo", default=".")
    p.add_argument("--base", default="")
    p.set_defaults(fn=cmd_prepush)

    p = sub.add_parser("eval", help="evaluate the gate on the golden PRs")
    p.add_argument("--ai", action="store_true", help="run the Gemini review too (costs credits)")
    p.add_argument("--reuse-ai", action="store_true", help="reuse cached AI results in eval/results/")
    p.add_argument(
        "--variants",
        type=int,
        default=1,
        help="with --ai: N prompt variants (shuffled order) to measure verdict stability",
    )
    p.add_argument("--base", default="main")
    p.add_argument("--write", action="store_true", help="update the generated sections of EVAL.md")
    p.add_argument("--check-analysis", action="store_true", help="fail if a FP/FN in EVAL.md lacks its analysis")
    p.set_defaults(fn=cmd_eval)
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(name)s %(levelname)s %(message)s")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    if getattr(args, "command", "") == "report" and args.publish and not (args.pr and args.sha):
        raise SystemExit("--publish needs --pr and --sha")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
