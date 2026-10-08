"""Runs the gate on every golden PR and scores it against eval/ground_truth.yaml.

python -m gate eval                  # deterministic pipeline only (free)
python -m gate eval --ai             # + Gemini (costs credits; results cached in eval/results/)
python -m gate eval --ai --reuse-ai  # re-score cached AI results without calling Gemini
python -m gate eval --write          # update the generated sections of EVAL.md
python -m gate eval --check-analysis # fail if any FP/FN lacks its written analysis
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from gate.config import GATE_ROOT, SEVERITIES
from gate.diff import DiffContext, git
from gate.report.baseline import demote_preexisting
from gate.report.finding import Finding, read_findings, write_json
from gate.report.merge import dedupe

EVAL_DIR = GATE_ROOT / "eval"
RESULTS_DIR = EVAL_DIR / "results"
EVAL_MD = GATE_ROOT / "EVAL.md"
PIPELINES = ("deterministic", "ai", "combined")


# --- scoring (pure) ---------------------------------------------------------------------


def _matches(item: dict, f: Finding, window: int) -> bool:
    if f.rule != item["rule"]:
        return False
    if item.get("severity") and item.get("kind") == "acceptable" and f.severity != item["severity"]:
        return False
    if item.get("file") and f.file != item["file"]:
        return False
    lines = item.get("lines")
    if not lines or f.line is None:
        return True
    return lines[0] - window <= f.line <= lines[1] + window


@dataclass
class Score:
    tp: list[tuple[Finding, str]] = field(default_factory=list)  # (finding, ground-truth id)
    fp: list[Finding] = field(default_factory=list)
    fn: list[dict] = field(default_factory=list)
    ignored: list[Finding] = field(default_factory=list)

    @property
    def precision(self) -> float | None:
        total = len(self.tp) + len(self.fp)
        return len(self.tp) / total if total else None

    def recall(self, expected: int) -> float | None:
        found = len({gid for _, gid in self.tp})
        return found / expected if expected else None


def score_pr(pr: dict, findings: list[Finding], truth: dict) -> Score:
    window = truth.get("line_window", 3)
    scope = set(truth["scope_rules"])
    expected = pr.get("expected") or []
    acceptable = [
        {**a, "kind": "acceptable"} for a in (pr.get("acceptable") or []) + (truth.get("acceptable_everywhere") or [])
    ]
    score = Score()
    for f in findings:
        if f.rule not in scope:
            continue
        hit = next((e for e in expected if _matches(e, f, window)), None)
        if hit is not None:
            score.tp.append((f, hit["id"]))
        elif any(_matches(a, f, window) for a in acceptable):
            score.ignored.append(f)
        else:
            score.fp.append(f)
    matched = {gid for _, gid in score.tp}
    score.fn = [e for e in expected if e["id"] not in matched]
    return score


def metrics(truth: dict, findings_by_pr: dict[str, list[Finding]]) -> dict:
    """Precision/recall overall and per severity, plus severity agreement on true positives."""
    scores = {pr["branch"]: score_pr(pr, findings_by_pr.get(pr["branch"], []), truth) for pr in truth["prs"]}
    expected = [e for pr in truth["prs"] for e in pr.get("expected") or []]
    tp = [t for s in scores.values() for t in s.tp]
    fp = [f for s in scores.values() for f in s.fp]
    recalled = {gid for _, gid in tp}
    sev_of = {e["id"]: e["severity"] for e in expected}

    def ratio(a: int, b: int) -> float | None:
        return round(a / b, 3) if b else None

    per_severity = {}
    for sev in SEVERITIES:
        sev_tp = [f for f, _ in tp if f.severity == sev]
        sev_fp = [f for f in fp if f.severity == sev]
        sev_expected = [e for e in expected if e["severity"] == sev]
        per_severity[sev] = {
            "findings": len(sev_tp) + len(sev_fp),
            "precision": ratio(len(sev_tp), len(sev_tp) + len(sev_fp)),
            "expected": len(sev_expected),
            "recall": ratio(len([e for e in sev_expected if e["id"] in recalled]), len(sev_expected)),
        }
    return {
        "precision": ratio(len(tp), len(tp) + len(fp)),
        "recall": ratio(len(recalled), len(expected)),
        "tp": len(tp),
        "fp": len(fp),
        "fn": len(expected) - len(recalled),
        "expected": len(expected),
        "severity_agreement": ratio(sum(1 for f, gid in tp if f.severity == sev_of[gid]), len(tp)),
        "per_severity": per_severity,
        "scores": scores,
    }


def gate_blocks(findings: list[Finding]) -> bool:
    """What the PR author actually sees: any Critical/High blocks, whatever rule it comes from."""
    return any(f.severity in ("critical", "high") for f in findings)


def verdicts(truth: dict, findings_by_pr: dict[str, list[Finding]]) -> dict:
    """Merge decision per PR vs the truth. Counts every finding, process rules included:
    precision/recall only score AGENTS#1-9, so a process rule that blocks a sound PR
    would otherwise be invisible (it was, until PR #12)."""
    rows = []
    for pr in truth["prs"]:
        blocked = gate_blocks(findings_by_pr.get(pr["branch"], []))
        expected = pr["verdict"] == "block"
        rows.append({"branch": pr["branch"], "truth": pr["verdict"], "blocked": blocked, "ok": blocked == expected})
    correct = sum(r["ok"] for r in rows)
    false_blocks = sum(1 for r in rows if r["blocked"] and r["truth"] != "block")
    missed_blocks = sum(1 for r in rows if not r["blocked"] and r["truth"] == "block")
    return {
        "rows": rows,
        "correct": correct,
        "total": len(rows),
        "false_blocks": false_blocks,
        "missed_blocks": missed_blocks,
    }


def failure_ids(truth: dict, findings_by_pr: dict[str, list[Finding]]) -> list[dict]:
    """Every FP and FN with a stable id and the facts needed to analyze it."""
    out = []
    for pr in truth["prs"]:
        branch = pr["branch"]
        score = score_pr(pr, findings_by_pr.get(branch, []), truth)
        slug = branch.replace("/", "-")
        for f in score.fp:
            out.append(
                {
                    "id": f"fp-{slug}-{f.rule.split('#')[1]}-{Path(f.file).stem}-{f.line or 0}",
                    "kind": "FP",
                    "pr": branch,
                    "rule": f.rule,
                    "severity": f.severity,
                    "source": f.source,
                    "location": f.location,
                    "text": f.message,
                }
            )
        for e in score.fn:
            out.append(
                {
                    "id": f"fn-{e['id']}",
                    "kind": "FN",
                    "pr": branch,
                    "rule": e["rule"],
                    "severity": e["severity"],
                    "source": "-",
                    "location": f"{e.get('file', '(any file)')}" + (f":{e['lines'][0]}" if e.get("lines") else ""),
                    "text": e.get("why", ""),
                }
            )
    return out


def missing_analysis(eval_md: str, ids: list[str]) -> list[str]:
    """Ids without a `### <id>` entry whose **Why:** and **Change:** are both filled in."""
    missing = []
    for fid in ids:
        match = re.search(rf"^### {re.escape(fid)}\s*$(.*?)(?=^### |^## |\Z)", eval_md, flags=re.M | re.S)
        body = match.group(1) if match else ""
        why = re.search(r"\*\*Why:\*\*[ \t]*(\S.*)", body)
        change = re.search(r"\*\*Change:\*\*[ \t]*(\S.*)", body)
        if not (why and change):
            missing.append(fid)
    return missing


# --- running the gate on the golden PRs ------------------------------------------------


def _resolve(repo: Path, branch: str) -> str:
    for ref in (branch, f"origin/{branch}"):
        try:
            git(repo, "rev-parse", "--verify", "--quiet", ref)
            return ref
        except RuntimeError:
            continue
    raise RuntimeError(f"branch {branch} not found locally or on origin")


def pr_head(repo: Path, pr: dict) -> str:
    """The pinned commit when the ground truth has one, else the branch tip.

    A golden PR must not move: if someone merges the base into the branch (GitHub's
    "Update branch"), its diff suddenly contains the base's changes and the eval scores
    a different PR than the one the ground truth describes.
    """
    if pr.get("head"):
        git(repo, "rev-parse", "--verify", "--quiet", f"{pr['head']}^{{commit}}")
        return pr["head"]
    return _resolve(repo, pr["branch"])


def _slug(branch: str) -> str:
    return branch.replace("/", "-")


def run_pr(pr: dict, base: str, use_ai: bool, reuse_ai: bool) -> dict:
    from gate.deterministic import runner

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    head = pr_head(GATE_ROOT, pr)
    tmp = Path(tempfile.mkdtemp(prefix="gate-eval-"))
    worktree = tmp / "wt"
    git(GATE_ROOT, "worktree", "add", "--detach", "--quiet", str(worktree), head)
    try:
        ctx = DiffContext.from_refs(worktree, base, "HEAD", pr_title=pr.get("title", ""), pr_body=pr.get("body", ""))
        result = runner.run(ctx, with_tests=True)
        write_json(RESULTS_DIR / f"{_slug(pr['branch'])}.deterministic.json", result.findings)
        ai_path = RESULTS_DIR / f"{_slug(pr['branch'])}.ai.json"
        ai_findings: list[Finding] = []
        if use_ai and reuse_ai and ai_path.exists():
            ai_findings = demote_preexisting(read_findings(ai_path), ctx)  # cached before the policy existed
        elif use_ai:
            from gate.ai.review import review

            ai = review(ctx, result.findings, result.signals, cache_dir=GATE_ROOT / ".gate-cache" / "ai")
            ai_findings = ai.findings
            write_json(ai_path, ai_findings)
            (RESULTS_DIR / f"{_slug(pr['branch'])}.ai-meta.json").write_text(
                json.dumps({"model": ai.model, "cost": ai.cost, "dropped": [r for _, r in ai.dropped]}, indent=2),
                encoding="utf-8",
            )
        return {"deterministic": result.findings, "ai": ai_findings, "errors": result.errors}
    finally:
        git(GATE_ROOT, "worktree", "remove", "--force", str(worktree))
        shutil.rmtree(tmp, ignore_errors=True)


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def render_results(truth: dict, by_pipeline: dict[str, dict[str, list[Finding]]], ai_ran: bool) -> str:
    lines = [
        "| Pipeline | Merge verdict correct | False blocks | Missed blocks | Precision | Recall | TP | FP | FN | Severity agreement |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, findings in by_pipeline.items():
        if name != "deterministic" and not ai_ran:
            continue
        m, v = metrics(truth, findings), verdicts(truth, findings)
        lines.append(
            f"| {name} | {v['correct']}/{v['total']} | {v['false_blocks']} | {v['missed_blocks']} | {_fmt(m['precision'])} | {_fmt(m['recall'])} | {m['tp']} | {m['fp']} | {m['fn']} | {_fmt(m['severity_agreement'])} |"
        )
    shown = "combined" if ai_ran else "deterministic"
    m = metrics(truth, by_pipeline[shown])
    lines += [
        "",
        f"Per severity ({shown}):",
        "",
        "| Severity | Findings | Precision | Expected | Recall |",
        "|---|---|---|---|---|",
    ]
    for sev, s in m["per_severity"].items():
        lines.append(f"| {sev} | {s['findings']} | {_fmt(s['precision'])} | {s['expected']} | {_fmt(s['recall'])} |")
    lines += [
        "",
        f"Per PR ({shown}):",
        "",
        "| PR | Verdict (truth) | Gate result | TP | FP | FN |",
        "|---|---|---|---|---|---|",
    ]
    for pr in truth["prs"]:
        found = by_pipeline[shown].get(pr["branch"], [])
        s = score_pr(pr, found, truth)
        lines.append(
            f"| `{pr['branch']}` | {pr['verdict']} | {'block' if gate_blocks(found) else 'pass'} | {len(s.tp)} | {len(s.fp)} | {len(s.fn)} |"
        )
    if not ai_ran:
        lines += ["", "_AI pipeline not run (no GEMINI_API_KEY or `--ai` not passed)._"]
    return "\n".join(lines)


def render_failures(failures: list[dict]) -> str:
    if not failures:
        return "No false positives or false negatives."
    lines = [
        "| Id | Kind | PR | Rule | Severity | Source | Location | Finding / expected |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for f in failures:
        text = f["text"].replace("|", "\\|")[:140]
        lines.append(
            f"| `{f['id']}` | {f['kind']} | `{f['pr']}` | {f['rule']} | {f['severity']} | {f['source']} | `{f['location']}` | {text} |"
        )
    return "\n".join(lines)


def replace_section(text: str, name: str, content: str) -> str:
    start, end = f"<!-- eval:{name}:start -->", f"<!-- eval:{name}:end -->"
    pattern = re.compile(rf"{re.escape(start)}.*?{re.escape(end)}", re.S)
    if not pattern.search(text):
        raise RuntimeError(f"EVAL.md is missing the {start} ... {end} markers")
    return pattern.sub(lambda _: f"{start}\n{content}\n{end}", text)


def main(args) -> int:
    truth = yaml.safe_load((EVAL_DIR / "ground_truth.yaml").read_text(encoding="utf-8"))
    by_pipeline: dict[str, dict[str, list[Finding]]] = {p: {} for p in PIPELINES}
    errors = []
    for pr in truth["prs"]:
        print(f"evaluating {pr['branch']} ...", flush=True)
        out = run_pr(pr, args.base, args.ai, args.reuse_ai)
        errors += [f"{pr['branch']}: {e}" for e in out["errors"]]
        by_pipeline["deterministic"][pr["branch"]] = out["deterministic"]
        by_pipeline["ai"][pr["branch"]] = out["ai"]
        by_pipeline["combined"][pr["branch"]] = dedupe(out["deterministic"] + out["ai"])

    shown = "combined" if args.ai else "deterministic"
    results = render_results(truth, by_pipeline, args.ai)
    failures = failure_ids(truth, by_pipeline[shown])
    print(results)
    print()
    print(render_failures(failures))
    for e in errors:
        print(f"gate error: {e}")

    if args.write:
        text = EVAL_MD.read_text(encoding="utf-8")
        text = replace_section(text, "results", results)
        text = replace_section(text, "failures", render_failures(failures))
        EVAL_MD.write_text(text, encoding="utf-8")
        print(f"updated {EVAL_MD.name}")
    if args.check_analysis:
        missing = missing_analysis(EVAL_MD.read_text(encoding="utf-8"), [f["id"] for f in failures])
        if missing:
            print("missing failure analysis in EVAL.md for: " + ", ".join(missing))
            return 1
    return 1 if errors else 0
