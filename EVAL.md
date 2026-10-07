# Evaluation

The 8 open PRs are the golden set. The gate is treated as a system to measure (AGENTS#12–14).

- **Ground truth:** [eval/ground_truth.yaml](eval/ground_truth.yaml), written by reading each diff against AGENTS.md.
- **Harness:** `python -m gate eval [--ai] --write` runs the real gate on each PR branch (in a temporary worktree, tests included) and scores it. Code: [gate/eval/run_eval.py](gate/eval/run_eval.py).
- **Matching:** same rule, same file, line within ±3 of the expected range (file-level findings match any line). Debatable findings listed as `acceptable` are neither rewarded nor penalized. Severity is not part of the match; it is reported separately as *severity agreement*.
- **Scored rules:** AGENTS#1–9 (the team standards). Process rules (#16 README, #18 records, #20 docs) fire on every pre-gate branch by construction and are excluded from the score.

## Ground truth

| PR | Verdict | Expected problems |
|----|---------|-------------------|
| `feature/lessons-pagination` | sound | — |
| `feature/score-validation` | sound | — (non-numeric score → 500 is a pre-existing gap: acceptable) |
| `fix/mobile-sync-visibility` | block | Critical #1: `full_name` + `email` logged in plain text |
| `feature/support-context` | block | Critical #1: name/email/birthdate logged through a helper · Critical #4: support context not minimized · High #6: no tests |
| `feature/email-reminders` | block | Critical #8: SendGrid key committed · Critical #1: recipient email logged · Medium #7: TODO without ticket · High #6: no tests |
| `feature/streaks` | block | High #9: streak starts yesterday (today never counts) · High #6: tests can't fail (`isinstance`, `>= 0`) |
| `feature/analytics-archive` | block | Critical #3: minors' personal data copied, kept indefinitely, no retention · Critical #4: not minimized · High #6: no tests |
| `fix/progress-percentage` | block | High #9: `int()` truncates and an empty catalog reports 100% |

## Results

<!-- eval:results:start -->
| Pipeline | Precision | Recall | TP | FP | FN | Severity agreement |
|---|---|---|---|---|---|---|
| deterministic | 1.00 | 0.64 | 11 | 0 | 5 | 0.82 |

Per severity (deterministic):

| Severity | Findings | Precision | Expected | Recall |
|---|---|---|---|---|
| critical | 4 | 1.00 | 7 | 0.71 |
| high | 6 | 1.00 | 6 | 0.50 |
| medium | 1 | 1.00 | 1 | 1.00 |
| low | 0 | — | 0 | — |

Per PR (deterministic):

| PR | Verdict (truth) | Gate result | TP | FP | FN |
|---|---|---|---|---|---|
| `feature/lessons-pagination` | sound | pass | 0 | 0 | 0 |
| `feature/score-validation` | sound | pass | 0 | 0 | 0 |
| `fix/mobile-sync-visibility` | block | block | 1 | 0 | 0 |
| `feature/support-context` | block | block | 2 | 0 | 1 |
| `feature/email-reminders` | block | block | 5 | 0 | 0 |
| `feature/streaks` | block | pass | 0 | 0 | 2 |
| `feature/analytics-archive` | block | block | 3 | 0 | 1 |
| `fix/progress-percentage` | block | pass | 0 | 0 | 1 |

_AI pipeline not run (no GEMINI_API_KEY or `--ai` not passed)._
<!-- eval:results:end -->

## Failure analysis

Generated list (every false positive and false negative of the last run):

<!-- eval:failures:start -->
| Id | Kind | PR | Rule | Severity | Source | Location | Finding / expected |
|---|---|---|---|---|---|---|---|
| `fn-pr4-not-minimized` | FN | `feature/support-context` | AGENTS#4 | critical | - | `app/support.py:4` | support context carries name/email/birthdate where student_id would do |
| `fn-pr6-streak-bug` | FN | `feature/streaks` | AGENTS#9 | high | - | `app/streaks.py:5` | starts counting yesterday: today's activity never counts (docstring says ending today) |
| `fn-pr6-weak-tests` | FN | `feature/streaks` | AGENTS#6 | high | - | `tests/test_streaks.py:1` | isinstance / >= 0 assertions can't detect a regression |
| `fn-pr7-not-minimized` | FN | `feature/analytics-archive` | AGENTS#4 | critical | - | `app/archive.py:11` | copies full_name, birthdate, is_minor for analytics |
| `fn-pr8-wrong-percentage` | FN | `fix/progress-percentage` | AGENTS#9 | high | - | `app/main.py:38` | int() truncates (2/3 -> 66) and an empty catalog reports 100% complete |
<!-- eval:failures:end -->

Each entry below explains one item of the list. `python -m gate eval --check-analysis` fails while any item lacks its **Why** and **Change**.

> Status: the entries below analyze the **deterministic-only** run. The AI run (`python -m gate eval --ai --write`) is pending the Gemini key; it will regenerate the list, and every new FP/FN (including the first AI false positive) gets its entry here.

### fn-pr4-not-minimized
**Why:** Minimization depends on purpose ("does support need the birthdate?"), which no static rule can judge. Pipeline A did catch the same PR's log exposure (Critical #1) through the helper summary, so the PR is blocked anyway.
**Change:** None in Pipeline A, by design: B6 in the AI prompt owns minimization. Verify in the AI run that B6 reports it on `app/support.py`.

### fn-pr6-streak-bug
**Why:** The bug (counting starts yesterday, contradicting the docstring "ending today") is semantic. The code is covered by tests, lint-clean and touches no personal data, so every deterministic check passes.
**Change:** None in Pipeline A. The AI prompt (B11) explicitly asks to compare behavior with docstrings and business rules; this FN is the main reason the AI pipeline exists.

### fn-pr6-weak-tests
**Why:** A10 measures that changed lines execute, not that assertions can fail; `isinstance(...)` and `>= 0` reach 100% coverage while asserting nothing.
**Change:** Considered a deterministic "weak assertion" heuristic (flag tests whose only asserts are `isinstance`/`>= 0`/`True`); left to B8 for now because the heuristic would be easy to game and noisy on legitimate type checks. Revisit if the AI misses it.

### fn-pr7-not-minimized
**Why:** Same as `fn-pr4-not-minimized`: whether `full_name`/`birthdate` are needed for cohort analytics is a purpose question. Pipeline A did block the PR on the copy itself (#3, retention).
**Change:** None in Pipeline A; covered by B6.

### fn-pr8-wrong-percentage
**Why:** `int()` vs `round()` and `else 100` are valid code with a passing test; the test even asserts the wrong 100%. Only domain knowledge (BR-4 in the API docs) says it is wrong.
**Change:** The AI prompt receives `docs/API-AND-BUSINESS-RULES.md` as context so B11 can compare against BR-4. A mutation-style check (fail when a PR changes a documented business rule without changing its BR row) is in the backlog.

### Severity disagreement (not an FP/FN)
`feature/analytics-archive` was matched, but at **High** (A4 dataset without retention, P2 copy into a collection) while the ground truth says **Critical**: the copy holds minors' personal data kept indefinitely. The PR is still blocked (High blocks), so the outcome is right, but the severity under-states the risk. Backlog item 5 in DECISIONS.md: escalate to Critical when the copied payload contains personal fields.

## Trust policy

Based on the deterministic run above (AI rows to be added after the AI run):

| Severity | Source | Precision measured | Policy |
|----------|--------|--------------------|--------|
| Critical | Deterministic | 1.00 (4/4), 0 FP on the 2 sound PRs | **Block automatically** (fail + `quality-gate/critical`). |
| High | Deterministic | 1.00 (6/6) | **Block** with a request-changes review (`quality-gate/high`). |
| Medium / Low | Deterministic | 1.00 (1/1) / none | Comment only. |
| Critical / High | AI | pending | Blocks by team decision (AGENTS#14), but `GATE_MODE` stays `shadow` until the AI run shows ≥ 0.9 precision on Critical and no blocking finding on the 2 sound PRs. If it falls short, AI Criticals are demoted to High (dismissable review) until prompts improve. |
| Medium / Low | AI | pending | Comment only, always. |

Every block can be lifted by a production approver with `/gate-override <reason>`, recorded on the PR (ADR-3).
