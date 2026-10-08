# Running the quality gate

What each pipeline checks: [docs/PIPELINES.md](docs/PIPELINES.md). Rules: [AGENTS.md](AGENTS.md).

## Why it's bigger than a 4-5 hour script

It was built agentically, and it's built for a team where agents write a lot of the code:
- **The rules are the spec.** `AGENTS.md` is short, and every agent (and person) reads it before coding.
- **One rule → one task → one test.** `plans/tasks/` has one file per rule, and `tests/gate/` has a failing and a passing fixture for each. Agents implemented against those tests. I wrote the rules, the ground truth and the severity calls, and reviewed the results.
- **The gate is what makes agent speed safe.** The more code agents write, the less a human can read line by line. So the cheap checks run on every commit, and the LLM only judges what needs judgment.

Where to start reading: `gate/report/actions.py` (what blocks), `gate/deterministic/pii_flow.py` (the minors' privacy core), `gate/ai/prompts/` (what the AI is asked), `gate/eval/run_eval.py` (how it's measured).

## Setup (≈ 5 min)

Python 3.11+, git, and Node (only for the hooks).

```bash
python3 -m venv .venv && source .venv/bin/activate      # Windows: py -m venv .venv; .venv\Scripts\activate
pip install -r requirements.txt -r requirements-gate.txt
npm install                                             # pre-commit + pre-push hooks
```

- **pre-commit:** fast checks on staged files. Blocks on Critical/High.
- **pre-push:** tests + 85% changed-line coverage.

## One command

```bash
python -m gate all          # or: sh scripts/check-all.sh / .\scripts\check-all.ps1
```

Runs pre-commit checks, lint, tests + coverage, the script pipeline, and the AI pipeline (only if `GEMINI_API_KEY` is set and valid). Exit 0 = READY, 1 = BLOCKED. Flags: `--fix`, `--no-ai`, `--base origin/main`.

## Other commands

| Goal | Command |
|---|---|
| Both pipelines on committed changes | `python -m gate check --base main [--ai]` |
| Score the gate on the golden PRs | `python -m gate eval [--ai] [--reuse-ai] [--write]` |
| AI tests (cost credits) | `pytest -m ai` |

## On GitHub

One-time setup:
1. Secret `GEMINI_API_KEY`. Variable `GATE_MODE`: `shadow` (comment only, the default) or `enforce`.
2. `bash gate/setup/branch_protection.sh`: requires that branch's `quality-gate/<base>/critical` and `quality-gate/<base>/high` (e.g. `quality-gate/develop/critical`), plus 1 review, on `develop`/`main`.

Every PR gets:
- A summary comment with every finding and the run's cost.
- Inline comments with the fix.
- The two checks.

Override (admin/maintain only, logged): comment `/gate-override <reason>`.

## Cost

About $0.003 per AI review (measured), and $0 when re-running an unchanged PR (cache). Every run logs its AI + CI cost on the PR.

Estimate for a normal day: 5 developers × 2 medium PRs, 3 gate runs per PR (opened + 2 fix pushes), a conservative $0.01 of AI per run, 5 CI minutes per run.

| | Per PR | Per day | Per month (21 days) | From Jan 2027 (Gemini ×2) |
|---|---|---|---|---|
| AI (Gemini) | $0.03 | $0.30 | ≈ $6.30 | ≈ $12.60 |
| CI, this public repo | $0 | $0 | $0 | $0 |
| CI if private (list price) | $0.09 | $0.90 | ≈ $18.90 | ≈ $18.90 |

Formula: devs × PRs/day × runs/PR × days × $/run. At org scale, runner minutes cost more than the LLM (DECISIONS.md, scaling).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `python` opens the Microsoft Store | Use `py` or the scripts |
| Hooks don't run | `npm install` again |
| AI step skipped | Key missing or invalid; the script checks still ran |
| `hit the output cap` | Raise `GEMINI_MAX_OUTPUT_TOKENS` |
| Coverage fails with no failing test | Your changed lines aren't covered; the finding lists them |
