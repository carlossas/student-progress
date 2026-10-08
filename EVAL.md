# Evaluation

Golden set = the 8 open PRs. Ground truth: [eval/ground_truth.yaml](eval/ground_truth.yaml). Run it with `python -m gate eval [--ai] --write`.

What I measure:
1. **Merge verdict per PR** (headline). Counts every finding, process rules included.
2. **Precision / recall** on AGENTS#1-9. Match = same rule + file, line ±3. Severity is reported apart.

## Ground truth

| PR | Verdict | Expected |
|----|---------|----------|
| `lessons-pagination` | sound | none |
| `score-validation` | comment | Medium #5: non-numeric score → 500 (pre-existing line, only moved) |
| `mobile-sync-visibility` | block | Critical #1: name + email logged |
| `support-context` | block | Critical #1: PII logged via helper · Critical #4: not minimized · High #6: no tests |
| `email-reminders` | block | Critical #8: SendGrid key · Critical #1: email logged · High #2: minors' emails to SendGrid · High #6 · Medium #7 TODO |
| `streaks` | block | High #9: today never counts · High #6: tests can't fail |
| `analytics-archive` | block | Critical #3: no retention · Critical #4: not minimized · Critical #2: minors' records to analytics · High #6 |
| `progress-percentage` | block | High #9: `int()` truncates, empty catalog = 100% |

I changed the truth in two passes after seeing results. Every change is in the YAML with the reason. Two of them lowered my own numbers (the two #2 minors cases).

## Results

<!-- eval:results:start -->
| Pipeline | Merge verdict correct | False blocks | Missed blocks | Precision | Recall | TP | FP | FN | Severity agreement |
|---|---|---|---|---|---|---|---|---|---|
| deterministic | 6/8 | 0 | 2 | 1.00 | 0.59 | 11 | 0 | 7 | 0.91 |
| ai | 7/8 | 0 | 1 | 1.00 | 0.41 | 7 | 0 | 10 | 1.00 |
| combined | 8/8 | 0 | 0 | 1.00 | 0.94 | 17 | 0 | 1 | 0.94 |

Per severity (combined):

| Severity | Findings | Precision | Expected | Recall |
|---|---|---|---|---|
| critical | 7 | 1.00 | 8 | 0.88 |
| high | 8 | 1.00 | 7 | 1.00 |
| medium | 2 | 1.00 | 2 | 1.00 |
| low | 0 | — | 0 | — |

Per PR (combined):

| PR | Verdict (truth) | Gate result | TP | FP | FN |
|---|---|---|---|---|---|
| `feature/lessons-pagination` | sound | pass | 0 | 0 | 0 |
| `feature/score-validation` | comment | pass | 1 | 0 | 0 |
| `fix/mobile-sync-visibility` | block | block | 1 | 0 | 0 |
| `feature/support-context` | block | block | 3 | 0 | 0 |
| `feature/email-reminders` | block | block | 5 | 0 | 0 |
| `feature/streaks` | block | block | 2 | 0 | 0 |
| `feature/analytics-archive` | block | block | 4 | 0 | 1 |
| `fix/progress-percentage` | block | block | 1 | 0 | 0 |
<!-- eval:results:end -->

- Right merge call on 8/8, now measured with **fresh** Gemini calls (no cache) in 3 prompt variants (next section). Neither pipeline gets there alone.
- Honest history of that number: the cached results said 8/8; the first fresh run in CI (`gate-eval`, 2026-10-08) said **7/8 with 1 false block**; after the B8 change below, fresh runs give 8/8 in every variant. See `fp-ci-pr2-b8-test-severity`.
- Latest CI run ([gate-eval](https://github.com/carlossas/student-progress/actions/runs/37729439791), 2026-10-08, `develop` at `f05964d`, 4096 output cap): the tables above, 12/12 AI tests, no review truncated. Gemini was slow that night: the AI tests took 7 min, and 19 min in the run before (I cancelled that one by mistake, thinking it was stuck). Usually it's under 3. Nothing failed, but a slow Gemini means a slow gate (DECISIONS.md backlog #4).
- 8 PRs is small: recall 17/18 has a 95% interval of about 0.74-0.99.

## Stability across prompt variants

The fixed seed makes two identical prompts give the same answer. It says nothing about a prompt that changes in irrelevant ways, which happens every time the scripts' findings change. `python -m gate eval --ai --variants 3` re-runs the AI with the scripts' findings and signals shuffled and reports which merge verdicts flip.

Same harness, fresh Gemini, before and after the B8 severity criterion:

| B8 prompt | Run 0 (original order) | Run 1 | Run 2 | PRs whose verdict flips |
|---|---|---|---|---|
| Before ("missing edge cases" listed as High) | 7/8 (false block on `score-validation`) | 8/8 | 8/8 | **1/8** |
| After (High only when tests cannot fail) | 8/8 | 8/8 | 8/8 | **0/8** |

The "before" row reproduces the CI result exactly: the verdict of `score-validation` depended on the order of an unrelated list in the prompt. The criterion removed the ambiguity the model was resolving at random.

Latest run (after):

<!-- eval:stability:start -->
3 prompt variants (run 0 = original order; runs 1+ shuffle the order of the scripts' findings and signals with a fixed seed).

| PR | Truth | Run 0 | Run 1 | Run 2 | Stable |
|---|---|---|---|---|---|
| `feature/lessons-pagination` | sound | pass | pass | pass | yes |
| `feature/score-validation` | comment | pass | pass | pass | yes |
| `fix/mobile-sync-visibility` | block | block | block | block | yes |
| `feature/support-context` | block | block | block | block | yes |
| `feature/email-reminders` | block | block | block | block | yes |
| `feature/streaks` | block | block | block | block | yes |
| `feature/analytics-archive` | block | block | block | block | yes |
| `fix/progress-percentage` | block | block | block | block | yes |

Verdict flips: **0/8 PRs**. Right merge call per run: 8/8, 8/8, 8/8.
<!-- eval:stability:end -->

## Failure analysis

<!-- eval:failures:start -->
| Id | Kind | PR | Rule | Severity | Source | Location | Finding / expected |
|---|---|---|---|---|---|---|---|
| `fn-pr7-minors-to-analytics` | FN | `feature/analytics-archive` | AGENTS#2 | critical | - | `app/archive.py:1` | minors' records, flagged with is_minor, handed to analytics without minimization or legal basis |
<!-- eval:failures:end -->

### fp-ci-pr2-b8-test-severity (fixed)
**Why:** In the first fresh CI eval, Gemini added High `AGENTS#6` on `score-validation` (`tests/test_score_validation.py:18`): "doesn't assert the 200, no non-numeric case". The critique is fair, but those tests do fail when the validation breaks: it is Medium. The cached run never showed it because the prompt had changed (the scripts' findings it receives are different now), so the cache missed and a new sample came out. The seed makes identical prompts repeatable; it does not make the verdict robust to a different prompt. Precision stayed 1.00 because `AGENTS#6` is *acceptable* on this PR; only the merge-verdict metric caught it.
**Change:** B8 now has an explicit criterion: **High only if the tests cannot fail** (trivial asserts, mocking the function under test, locking in a wrong behavior, no effective test); **"could be stronger" is Medium** (`gate/ai/prompts/r06_test_quality.md`, severity policy in `system.md`). Pinned by `tests/gate/ai/test_r06_test_severity_ai.py` (a score-validation-like fixture must not get a High; `streaks`-like tests that cannot fail must). The eval now measures prompt-variant stability: 1/8 flipping before, 0/8 after.

### fn-pr5-minors-to-sendgrid (fixed)
**Why:** It's scaffolding: nothing calls SendGrid yet, so the outbound script had nothing to match. The AI judged the code that exists, not what the module is for.
**Change:** A script, not a prompt (`gate/deterministic/vendor_channel.py`, A18). A changed module that names a known vendor and has a function handling a personal field gets High #2, unless the PR says `Legal basis: ...`. It stays quiet when the module already calls the vendor (pii_flow follows that data) or only handles `student_id`. Recall 0.88 → 0.94, still 0 FP and 8/8 verdicts. I picked a script because it's free, can't drift with the model, and doesn't need another prompt change measured across variants.

### fn-pr7-minors-to-analytics
**Why:** The PR is already blocked for retention and minimization, and the AI's fix covers this too. The model folds "data goes to analytics" into "too many fields".
**Change:** Not done yet. Next is a fixture where minimization is fine but the data goes to a third party, so #2 has to show up on its own (DECISIONS.md backlog #9).

### ci-r02-output-truncated (fixed)
**Why:** After the B8 change, `gate-eval` on PR #26 failed: the R02 AI test (several minors' data leaks in one fixture) hit the 2048-token output cap, which is a gate error and blocks. #26 was merged anyway, because `eval` isn't a required check. In production the same thing would block any PR with many real problems.
**Change:** The cap went from 2048 to 4096 (it only bills what the model writes, so normal PRs don't pay more), and a truncated review is retried with the cap doubled, up to 16384. The truncated try is billed in the run's cost. It only fails if it still truncates at the ceiling (`test_truncated_review_is_retried_with_a_bigger_cap`). Next: make `gate-eval` required for PRs that touch `gate/ai/`.

### fp-live-pr12-docs-rule (fixed)
**Why:** On GitHub, [PR #12](https://github.com/carlossas/student-progress/pull/12) (pagination, the clean PR) was blocked by "docs not updated" (High). The eval showed "pass" because process rules were out of scope. I made a rule that isn't in TEAM-STANDARDS blocking, and built an eval that couldn't see it.
**Change:** Process rules are Medium now. The merge verdict counts every finding (test: `test_r12_verdicts_count_unscored_rules`). That metric went from 6/8 to 8/8.

### fp-pr2-preexisting-severity (fixed)
**Why:** The 500 is real, but the line was already on `main`. A diff shows a moved line as new, so High blocked a PR that only improves things.
**Change:** `gate/report/baseline.py` turns High on moved lines into Medium, for rules #5, #7 and #9 only. Privacy, secrets and tests are never demoted.

## Trust policy

| Severity | Policy | Why |
|---|---|---|
| Critical (scripts or AI) | Block, logged override | Precision 1.00. A miss = a child's data leaked |
| High | Block (request changes) | Precision 1.00 |
| High on a moved line (#5/#7/#9) | Comment | Otherwise fixing old code gets punished |
| Medium / Low, process rules | Comment | Docs rule blocked the only clean PR |

Tripwires once it runs on real PRs:
- Overrides above ~5% → AI Critical drops to request-changes.
- Every override becomes a fixture.
- Gemini down = blocks everything, so a degraded mode is needed before this covers more repos.

Prompt injection: the script check (A17) has unit tests, and `tests/gate/ai/test_injection_resistance_ai.py` passes in CI. It checks that the model still reports a minor's email in a log when the PR tells it not to. Not tested: PRs from forks.


Golden PRs are pinned to a commit (`head:` in the YAML). `support-context` had `develop` merged into it through "Update branch" on PR #10. Its diff turned into the whole gate, and the eval quietly lost a true positive until I pinned it.
