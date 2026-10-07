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
| `feature/score-validation` | block | High #5: the new validation still returns a 500 for a non-numeric score (changed after the first AI run, see below) |
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
| deterministic | 1.00 | 0.60 | 10 | 0 | 6 | 0.90 |
| ai | 1.00 | 0.47 | 7 | 0 | 8 | 1.00 |
| combined | 1.00 | 1.00 | 16 | 0 | 0 | 0.94 |

Per severity (combined):

| Severity | Findings | Precision | Expected | Recall |
|---|---|---|---|---|
| critical | 7 | 1.00 | 7 | 1.00 |
| high | 8 | 1.00 | 7 | 1.00 |
| medium | 1 | 1.00 | 1 | 1.00 |
| low | 0 | — | 0 | — |

Per PR (combined):

| PR | Verdict (truth) | Gate result | TP | FP | FN |
|---|---|---|---|---|---|
| `feature/lessons-pagination` | sound | pass | 0 | 0 | 0 |
| `feature/score-validation` | block | block | 1 | 0 | 0 |
| `fix/mobile-sync-visibility` | block | block | 1 | 0 | 0 |
| `feature/support-context` | block | block | 3 | 0 | 0 |
| `feature/email-reminders` | block | block | 4 | 0 | 0 |
| `feature/streaks` | block | block | 2 | 0 | 0 |
| `feature/analytics-archive` | block | block | 4 | 0 | 0 |
| `fix/progress-percentage` | block | block | 1 | 0 | 0 |
<!-- eval:results:end -->

## Failure analysis

Generated list (every false positive and false negative of the last run):

<!-- eval:failures:start -->
No false positives or false negatives.
<!-- eval:failures:end -->

Each entry below explains one item of the list. `python -m gate eval --check-analysis` fails while any item lacks its **Why** and **Change**.

> Status (2026-10-07): the combined run has **no** FP or FN (18/18). The entries below analyze the misses of the **deterministic-only** run; the AI pipeline found all six (`gemini-3.8-flash`, LOW thinking). Run them yourself: `python -m gate eval` vs `python -m gate eval --ai`.
>
> Why the AI's own recall is 0.47: by design it is told not to repeat what the scripts already reported, so on its own it only finds the remaining problems. Its value is the combined recall (0.60 → 1.00) at precision 1.00.

### Ground-truth change after the first AI run (decided 2026-10-07)
**Why:** on `feature/score-validation` the AI reported High `AGENTS#5` at `app/main.py:52`: the PR adds `score = int(payload.get("score", 0))`, which still returns a 500 for a non-numeric score. The first ground truth called the PR sound and listed this as *acceptable*. The finding is correct: the line is new, and AGENTS#5 requires a 4xx for bad input.
**Change:** the ground truth now expects it (`pr2-score-500`) and the PR's verdict is "block". This is the eval working as intended: the model surfaced a problem the human ground truth had under-rated, and the decision was made by a person, not by tuning the model to agree.

### Run-to-run stability (R14-B, fixed)
**Why:** with `temperature=0` alone, 3 identical reviews returned the same Critical findings but a High finding (unknown student id → 500) appeared in only some runs: a re-run could flip a PR between blocked and passing. Google's 3.8 Flash notes say temperature is no longer the knob it was.
**Change:** a fixed sampling `seed` in `gate/ai/config.py`. Three runs are now byte-identical (same findings, lines and output tokens); R14-B passes.

### R09-B AI test too strict (fixed)
**Why:** in CI (`gate-eval` on PR #9) the R09-B test failed: it required a Low style note on the variable `x2` next to the High logic bug. With the fixed seed the model consistently reports only the bug (correct, on the right line). Style notes are optional by design, so the test was wrong, not the gate.
**Change:** the test now requires the High B11 finding and only checks that any style note is Low. All 10 AI tests pass.

### Real environment check (PR #10, 2026-10-07)
**Why:** golden PR #4 (`feature/support-context`) opened against `develop` once the gate was merged. The gate ran from `develop`'s own copy and reported 2 Critical (`AGENTS#1` log via helper, scripts; `AGENTS#4` minimization, Gemini) and 2 High (`AGENTS#6` no tests; `AGENTS#20` docs), matching the ground truth (`AGENTS#20` is a process rule, not scored). Cost $0.028.
**Change:** none needed.

### fn-pr2-score-500
**Why:** `payload: dict` (the A7 trigger) is on an unchanged line, so A7 doesn't fire, and `int(...)` on untrusted input is not a pattern the scripts flag: whether a 500 is reachable depends on the input contract.
**Change:** none in Pipeline A; B7 owns business-level validation and found it. Candidate deterministic check for the backlog: `int()`/`float()` on request data outside a `try` in a route handler.

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

### Severity refinements after reviewing the live PRs (approved 2026-10-07)
**Why:** reviewing the gate's comments on PRs #10–#18 as an architect found three issues, none of them a false positive:
- #17: a copy of minors' personal data with no retention period was reported as High; it is S1 (Critical).
- #15: "no tests touched" (A9) and "0% changed-line coverage" (A10) were two High findings for one root cause.
- #14: the scripts and the AI flagged the same log call on neighbouring lines (59 and 60): two Critical comments for one problem.

**Change:** copies of personal data into stored collections are Critical (P2); A10 is dropped when A9 already reports the change as untested; an AI finding within 3 lines of a script finding with the same rule is merged into it (PR #19). Severity agreement 0.88 → 0.94 combined (scripts alone 0.82 → 0.90); precision and recall stay 1.00. The docs rule (AGENTS#20) stays High: it fired on all 8 PRs, and that is intended.

## Trust policy

Based on the runs above (deterministic, and AI with `gemini-3.8-flash`, LOW thinking, fixed seed):

| Severity | Source | Precision measured | Policy |
|----------|--------|--------------------|--------|
| Critical | Deterministic | 1.00 (4/4), 0 FP on the 2 sound PRs | **Block automatically** (fail + `quality-gate/critical`). |
| High | Deterministic | 1.00 (6/6) | **Block** with a request-changes review (`quality-gate/high`). |
| Medium / Low | Deterministic | 1.00 (1/1) / none | Comment only. |
| Critical | AI | 1.00 (3/3), identical across 3 runs (fixed seed) | **Block automatically** (team decision, AGENTS#14). |
| High | AI | 1.00 (4/4) | **Block** (request-changes review). |
| Medium / Low | AI | — (none produced) | Comment only, always. |

**Recommendation:** switch `GATE_MODE` to `enforce`: the combined gate's verdict matches the ground truth on all 8 PRs. Measured AI cost: $0.0027–$0.0041 per review (≈ 3.5–4.3k input tokens, 5–331 output, 0 thinking).

Every block can be lifted by a production approver with `/gate-override <reason>`, recorded on the PR (ADR-3).
