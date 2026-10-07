"""Developer commands: `python -m gate all` (everything, one verdict) and `python -m gate lint`.

`all` checks what a PR from this checkout would contain: commits not on the base branch,
staged and unstaged edits, and untracked files. The AI step runs only when GEMINI_API_KEY is
set and valid (checked without spending tokens); otherwise it is skipped and the deterministic
checks decide on their own.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from gate.config import RUFF_CONFIG, SEVERITIES
from gate.diff import DiffContext, default_base
from gate.report.finding import Finding
from gate.report.merge import dedupe
from gate.tools import run_module

BLOCKING = ("critical", "high")


@dataclass
class Step:
    name: str
    status: str = "pass"  # pass | fail | skipped
    detail: str = ""
    findings: list[Finding] = field(default_factory=list)
    seconds: float = 0.0


def _counts(findings: list[Finding]) -> str:
    parts = [
        f"{sum(f.severity == s for f in findings)} {s}" for s in SEVERITIES if any(f.severity == s for f in findings)
    ]
    return ", ".join(parts) or "no findings"


def _status(findings: list[Finding], errors: list[str]) -> str:
    return "fail" if errors or any(f.severity in BLOCKING for f in findings) else "pass"


def _timed(step: Step, fn) -> Step:
    start = time.monotonic()
    try:
        fn(step)
    except Exception as e:  # noqa: BLE001 - shown as a failed step, never hidden
        step.status, step.detail = "fail", f"error: {e}"
    step.seconds = time.monotonic() - start
    return step


def lint(repo: Path, fix: bool = False, ctx: DiffContext | None = None) -> tuple[bool, str]:
    """Repo-wide `ruff check` (same as CI), plus the gate's format policy on changed Python files."""
    check_args = ["check", ".", *(["--fix"] if fix else [])]
    check = run_module("ruff", check_args, repo, ok=(0, 1))
    files = [p for p in (ctx.files() if ctx else []) if p.endswith(".py")]
    fmt_ok, fmt_out = True, ""
    if files:
        fmt_args = ["format", "--config", str(RUFF_CONFIG), *([] if fix else ["--check"]), *files]
        fmt = run_module("ruff", fmt_args, repo, ok=(0, 1))
        fmt_ok, fmt_out = fmt.returncode == 0, fmt.stdout.strip()
    output = "\n".join(x for x in (check.stdout.strip(), fmt_out) if x)
    return check.returncode == 0 and fmt_ok, output


def run_all(repo: Path, base: str | None, fix: bool = False, skip_ai: bool = False) -> int:
    from gate.__main__ import print_findings
    from gate.deterministic import runner, tests_runner

    repo = Path(repo).resolve()
    base = base or default_base(repo)
    ctx = DiffContext.from_worktree(repo, base)
    print(f"Checking {len(ctx.files())} changed file(s) against {base} (commits + uncommitted + untracked)\n")
    steps: list[Step] = []
    signals = []
    spend: list[float] = []  # AI dollars of this run

    def precommit(step: Step) -> None:
        staged = DiffContext.from_staged(repo)
        if not staged.files():
            step.status, step.detail = "skipped", "nothing staged"
            return
        result = runner.run(staged, fast_only=True, with_tests=False)
        step.findings, step.status = result.findings, _status(result.findings, result.errors)
        step.detail = "; ".join(result.errors) or _counts(result.findings)

    def linter(step: Step) -> None:
        ok, output = lint(repo, fix=fix, ctx=ctx)
        step.status = "pass" if ok else "fail"
        step.detail = ("fixed what ruff could; " if fix else "") + (
            "clean" if ok else "run `python -m gate lint --fix`"
        )
        if output and not ok:
            print(output)

    def tests(step: Step) -> None:
        findings, summary = tests_runner.execute(ctx, always=True)
        step.findings, step.status, step.detail = findings, _status(findings, []), summary

    def deterministic(step: Step) -> None:
        result = runner.run(ctx, with_tests=False)
        signals.extend(result.signals)
        step.findings, step.status = result.findings, _status(result.findings, result.errors)
        step.detail = "; ".join(f"crashed: {e}" for e in result.errors) or _counts(result.findings)

    def ai(step: Step) -> None:
        from gate.ai.client import probe
        from gate.ai.config import GeminiSettings
        from gate.ai.review import review

        if skip_ai:
            step.status, step.detail = "skipped", "--no-ai"
            return
        settings = GeminiSettings.from_env(require_key=False)
        usable, reason = probe(settings)
        if not usable:
            step.status, step.detail = "skipped", f"{reason} (deterministic checks only)"
            return
        previous = [f for s in steps for f in s.findings]
        result = review(ctx, previous, signals, cache_dir=repo / ".gate-cache" / "ai", settings=settings)
        step.findings, step.status = result.findings, _status(result.findings, [])
        cost = "cached, $0" if result.cached else f"${result.cost['total_usd']:.4f}"
        step.detail = f"{_counts(result.findings)} · {result.model} · {cost} · {result.requests} request(s)"
        spend.append(0.0 if result.cached else result.cost["total_usd"])

    plan = [
        ("Pre-commit checks (staged)", precommit),
        ("Lint (ruff)", linter),
        ("Tests + changed-line coverage", tests),
        ("Deterministic pipeline", deterministic),
        ("AI pipeline (Gemini)", ai),
    ]
    for number, (name, fn) in enumerate(plan, start=1):
        print(f"[{number}/{len(plan)}] {name} ...", flush=True)
        steps.append(_timed(Step(name), fn))
        print(f"      {steps[-1].status.upper()}: {steps[-1].detail}")

    findings = dedupe([f for s in steps for f in s.findings])
    print("\n" + "=" * 72)
    if findings:
        print_findings(findings)
        print("-" * 72)
    width = max(len(s.name) for s in steps)
    for s in steps:
        print(f"{s.name:<{width}}  {s.status.upper():<8} {s.seconds:5.1f}s  {s.detail}")
    blocked = any(s.status == "fail" for s in steps)
    print(f"Cost of this check: AI ${sum(spend):.4f} · local compute $0")
    print("=" * 72)
    if blocked:
        print("RESULT: BLOCKED — fix the failed steps / critical and high findings before opening a PR.")
    else:
        note = " (AI skipped)" if any(s.name.startswith("AI") and s.status == "skipped" for s in steps) else ""
        print(f"RESULT: READY{note} — medium/low findings are comments, they don't block.")
    return 1 if blocked else 0


def main_all(args) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    return run_all(Path(args.repo), args.base or None, fix=args.fix, skip_ai=args.no_ai)


def main_lint(args) -> int:
    repo = Path(args.repo).resolve()
    ctx = DiffContext.from_worktree(repo, args.base or default_base(repo))
    ok, output = lint(repo, fix=args.fix, ctx=ctx)
    if output:
        print(output)
    print("lint: clean" if ok else "lint: problems found" + ("" if args.fix else " — try `python -m gate lint --fix`"))
    return 0 if ok else 1
