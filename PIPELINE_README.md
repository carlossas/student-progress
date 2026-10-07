# Running the quality gate

How to run every check on your machine and on GitHub. What the pipelines check and why: [docs/PIPELINES.md](docs/PIPELINES.md). The rules themselves: [AGENTS.md](AGENTS.md).

| | Locally | On GitHub |
|---|---|---|
| Pre-commit checks (fast, staged files) | automatic on `git commit` (husky), or in `check-all` | — |
| Lint (ruff) | `check-all` / `python -m gate lint` | `ci` workflow + gate |
| Tests + changed-line coverage | `check-all` / `pytest`, automatic on `git push` | every PR |
| Deterministic pipeline | `check-all` | every PR |
| AI pipeline (Gemini) | `check-all`, **only if `GEMINI_API_KEY` is set and valid**; otherwise skipped | PRs into `develop` / `main` |

## 1. One-time setup (≈ 5 minutes)

Python 3.11+, git, and Node (only for the git hooks).

**macOS / Linux**

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-gate.txt
npm install
```

**Windows (PowerShell)**

```powershell
py -m venv .venv; .venv\Scripts\activate
pip install -r requirements.txt -r requirements-gate.txt
npm install
```

`npm install` activates two git hooks:
- **pre-commit**: secrets, personal data, retention, validation, lint and TODO checks on the files you staged. Blocks the commit on Critical/High.
- **pre-push**: the test suite and the 85% changed-line coverage check.

## 2. Check everything with one command

```bash
sh scripts/check-all.sh            # macOS / Linux / Git Bash
.\scripts\check-all.ps1            # Windows PowerShell
python -m gate all                 # same thing, any shell (inside the venv)
```

It checks what your PR would contain (commits not yet on the base branch, staged and unstaged edits, new untracked files) and runs, in order:

1. **Pre-commit checks** on staged files (skipped if nothing is staged).
2. **Lint**: `ruff check` on the repo (same as CI) and the gate's format policy on changed files.
3. **Tests**: the whole suite, plus 85% coverage of the lines you changed.
4. **Deterministic pipeline**: every script check, as the PR would run it.
5. **AI pipeline**: the Gemini review, if a usable key is available (see section 3).

Then it prints every finding (severity, rule, file:line, suggested fix) and a summary:

```
Pre-commit checks (staged)     SKIPPED    0.0s  nothing staged
Lint (ruff)                    PASS       0.3s  clean
Tests + changed-line coverage  PASS      14.9s  32 passed, 10 deselected in 13.84s
Deterministic pipeline         PASS       0.6s  no findings
AI pipeline (Gemini)           SKIPPED    0.5s  GEMINI_API_KEY is not set (deterministic checks only)
========================================================================
RESULT: READY (AI skipped) — medium/low findings are comments, they don't block.
```

Exit code `0` means **READY** (a PR would pass). Exit code `1` means **BLOCKED**: a step failed or there are Critical/High findings.

Options:

| Option | Effect |
|---|---|
| `--fix` | Let ruff fix lint problems and format your changed files first |
| `--no-ai` | Skip the Gemini review even if a key is set |
| `--base origin/main` | The branch your PR targets. Default: `origin/develop`, else `origin/main`, else `main` |

## 3. The AI pipeline locally

The AI step runs only when `GEMINI_API_KEY` is set **and valid**. Before reviewing, the gate checks the key and model with a metadata request that costs no tokens. If the key is missing, invalid or Gemini is unreachable, the step is **skipped with the reason** and the deterministic checks decide on their own.

```bash
export GEMINI_API_KEY=...          # macOS / Linux (never commit it, AGENTS#8)
$env:GEMINI_API_KEY = "..."        # Windows PowerShell
```

Optional: `GEMINI_MODEL` (default `gemini-3.8-flash`), `GEMINI_THINKING_LEVEL` (`LOW`), `GEMINI_MAX_OUTPUT_TOKENS` (`2048`), `GEMINI_MAX_INPUT_TOKENS` (`30000`, input budget per request; larger PRs are split into several requests).

A typical review costs about a third of a cent ($0.0027–$0.0041 measured); a very large PR is split into several requests (this repo's 167-file gate branch: 5 requests, $0.13). Results are cached in `.gate-cache/ai/`, so re-running `check-all` on unchanged code costs nothing.

## 4. Individual commands

| Goal | Command |
|---|---|
| Fast checks on staged files (what pre-commit runs) | `python -m gate precommit` |
| Lint, or lint and fix | `python -m gate lint` / `python -m gate lint --fix` |
| Tests | `pytest` |
| Tests + changed-line coverage (what pre-push runs) | `python -m gate prepush` |
| Both pipelines on committed changes only | `python -m gate check --base main [--ai]` |
| AI tests (one per AI rule; costs credits) | `pytest -m ai` |
| Evaluate the gate on the 8 golden PRs | `python -m gate eval [--ai] [--write]` |

## 5. On GitHub

**One-time repository setup** (admin):

1. Settings → Secrets and variables → Actions:
   - secret `GEMINI_API_KEY`;
   - optional variables `GEMINI_MODEL`, `GEMINI_THINKING_LEVEL`, `GEMINI_MAX_OUTPUT_TOKENS`, `GEMINI_MAX_INPUT_TOKENS`, `GATE_ACTIONS_USD_PER_MINUTE` (for the cost line; default `0.006`);
   - variable `GATE_MODE`: `shadow` (comment only, the default) or `enforce` (block).
2. Protect `develop` and `main`: the gate's two checks and 1 approving review are required to merge:
   ```bash
   bash gate/setup/branch_protection.sh
   ```

**Every PR:**

1. Push your branch and open a PR (`gh pr create --base develop`).
2. The `quality-gate` workflow runs:
   - **deterministic** and **smoke** jobs on every PR;
   - an **ai** job for PRs into `develop`/`main`;
   - a **report** job that comments and sets the checks.
3. Read the results:
   - **Checks** `quality-gate/critical` and `quality-gate/high`: red means blocked.
   - **A summary comment** on the PR, updated on each push, with every finding and the cost of that run (AI + CI).
   - **Inline comments** with the suggested fix on the lines concerned.
4. Fix and push again; the gate re-runs. Watch it with `gh pr checks --watch`.

**Useful commands:**

| Goal | Command |
|---|---|
| Re-run a failed gate run (an unchanged PR reuses the cached AI review: $0) | `gh run rerun <run-id>` |
| Measure the gate (golden PRs + AI tests) | `gh workflow run gate-eval.yml` |
| Override a block (repo admin/maintain only, recorded on the PR) | comment `/gate-override <reason>` on the PR |

## 6. What it costs

**Logged on every run.** The `report` job computes the full cost of that gate run and logs it as a notice, in the job summary, in the PR's gate comment and in `cost.json` (run artifact):

```
Pipeline cost for this run: $0.0455 = AI $0.0035 (1 request(s), 4049 in / 123 out / 0 thinking tokens, gemini-3.8-flash) + CI 7 runner-min $0.0420
```

- **AI:** real token counts from every Gemini request of the run, priced per `gate/ai/pricing.py`. $0 when the review came from cache.
- **CI:** each job's duration rounded up to whole minutes (how GitHub bills) × the Linux runner rate (`GATE_ACTIONS_USD_PER_MINUTE`, default $0.006). Public repos and the minutes included in your GitHub plan don't pay this; the figure is the list-price value.
- **Locally,** `check-all` prints the AI spend of that check; local compute is free.

**Measured so far (2026-10-07, `gemini-3.8-flash`, promo prices):**

| What | AI cost | Detail |
|---|---|---|
| Small PR (the 8 golden PRs) | $0.0027–$0.0041 per review | 3.5k–4.3k input tokens, 5–331 output, ≈ 6 s |
| Very large PR (167 files) | $0.13 per review | split into 5 requests, 164.8k input tokens, 28 s |
| Re-run of an unchanged PR | $0 | served from cache |

First run on GitHub (PR #9, 2026-10-07): every job finished in under 30 s, so the run billed **4 runner-minutes ($0.024 at list price)**. The repository is public, so GitHub-hosted minutes are **free**; the CI column below is what the same usage would cost on a private repo.

**Estimate for a normal day:** 5 developers × 2 medium PRs per day, all into `develop`.

| Assumption | Value | Why |
|---|---|---|
| Gate runs per PR | 3 | Opened, then 2 pushes with fixes; each push changes the diff, so no cache hit |
| AI cost per run | ≈ $0.01 | A medium PR (≈ 10 files, ≈ 300 changed lines) is ≈ 10k input tokens, between the measured small and large PRs |
| CI minutes per run | ≈ 5 | Measured 4 on PR #9 (each job < 1 min, rounded up per job); +1 for a medium PR's larger test suite |

| | Per PR (3 runs) | Per day (10 PRs, 30 runs) | Per month (21 working days) | Per month from Jan 2027 (Gemini price ×2) |
|---|---|---|---|---|
| AI (Gemini) | $0.03 | $0.30 | ≈ $6.30 | ≈ $12.60 |
| CI, public repo (this one) | $0 | $0 | $0 | $0 |
| CI, if the repo were private (list price) | $0.09 | $0.90 | ≈ $18.90 (3,150 runner-min) | ≈ $18.90 |
| **Total, this repo** | **≈ $0.03** | **≈ $0.30** | **≈ $6.30** | **≈ $12.60** |
| Total if private | ≈ $0.12 | ≈ $1.20 | ≈ $25 | ≈ $32 |

How to read it:
- On this public repo the only real spend is Gemini: ≈ $6/month for the team today, ≈ $13/month after the January 2027 price change.
- On a private repo, CI would be about 3× the AI cost, but the plan's included minutes (2,000/month on Free, 3,000 on Team) would cover the whole 3,150-minute month or most of it.
- One AI review costs about as much as 2 CI minutes. Even at 2027 prices, the AI reviewer costs less per month than one hour of an engineer's time.

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `python` opens the Microsoft Store (Windows) | Use `py`, or the scripts above (they use `.venv` automatically) |
| Hooks don't run | Run `npm install` again; check `git config core.hooksPath` prints `.husky/_` |
| Want to skip the hooks with `--no-verify` | Don't: CI runs the same checks and will block the PR anyway |
| AI step skipped: `HTTP 400 … API key not valid` | Check the key in Google AI Studio; the deterministic checks still ran |
| AI step fails: `hit the output cap` | Raise `GEMINI_MAX_OUTPUT_TOKENS` (repo variable, or env var locally) |
| Log says `large PR: AI review split into N requests` | Expected for big PRs: each request stays under `GEMINI_MAX_INPUT_TOKENS`; cost grows with the PR |
| AI step fails: quota / `429` | Prepaid credits or rate limit; the message says which. Retry later or top up |
| `Tests + changed-line coverage` fails with no failing test | Your changed lines aren't covered: the finding lists the uncovered line numbers |
