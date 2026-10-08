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

I changed the truth twice after seeing results. Every change is in the YAML with the reason. Two of them lowered my own numbers (the two #2 minors cases).

## Results

<!-- eval:results:start -->
| Pipeline | Merge verdict correct | False blocks | Missed blocks | Precision | Recall | TP | FP | FN | Severity agreement |
|---|---|---|---|---|---|---|---|---|---|
| deterministic | 6/8 | 0 | 2 | 1.00 | 0.53 | 10 | 0 | 8 | 0.90 |
| ai | 7/8 | 0 | 1 | 1.00 | 0.41 | 7 | 0 | 10 | 1.00 |
| combined | 8/8 | 0 | 0 | 1.00 | 0.88 | 16 | 0 | 2 | 0.94 |

Per severity (combined):

| Severity | Findings | Precision | Expected | Recall |
|---|---|---|---|---|
| critical | 7 | 1.00 | 8 | 0.88 |
| high | 7 | 1.00 | 7 | 0.86 |
| medium | 2 | 1.00 | 2 | 1.00 |
| low | 0 | — | 0 | — |

Per PR (combined):

| PR | Verdict (truth) | Gate result | TP | FP | FN |
|---|---|---|---|---|---|
| `feature/lessons-pagination` | sound | pass | 0 | 0 | 0 |
| `feature/score-validation` | comment | pass | 1 | 0 | 0 |
| `fix/mobile-sync-visibility` | block | block | 1 | 0 | 0 |
| `feature/support-context` | block | block | 3 | 0 | 0 |
| `feature/email-reminders` | block | block | 4 | 0 | 1 |
| `feature/streaks` | block | block | 2 | 0 | 0 |
| `feature/analytics-archive` | block | block | 4 | 0 | 1 |
| `fix/progress-percentage` | block | block | 1 | 0 | 0 |
<!-- eval:results:end -->

- Right merge call on 8/8, now measured with **fresh** Gemini calls (no cache) in 3 prompt variants (next section). Neither pipeline gets there alone.
- Honest history of that number: the cached results said 8/8; the first fresh run in CI (`gate-eval`, 2026-10-08) said **7/8 with 1 false block**; after the B8 change below, fresh runs give 8/8 in every variant. See `fp-ci-pr2-b8-test-severity`.
- 8 PRs is small: recall 16/18 has a 95% interval of about 0.67-0.97.

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
| `fn-pr5-minors-to-sendgrid` | FN | `feature/email-reminders` | AGENTS#2 | high | - | `app/notifications.py:1` | reminder emails to students go to SendGrid; minors' addresses would leave the service with no minimization or legal basis |
| `fn-pr7-minors-to-analytics` | FN | `feature/analytics-archive` | AGENTS#2 | critical | - | `app/archive.py:1` | minors' records, flagged with is_minor, handed to analytics without minimization or legal basis |
<!-- eval:failures:end -->

### fp-ci-pr2-b8-test-severity (fixed)
**Why:** In the first fresh CI eval, Gemini added High `AGENTS#6` on `score-validation` (`tests/test_score_validation.py:18`): "doesn't assert the 200, no non-numeric case". The critique is fair, but those tests do fail when the validation breaks: it is Medium. The cached run never showed it because the prompt had changed (the scripts' findings it receives are different now), so the cache missed and a new sample came out. The seed makes identical prompts repeatable; it does not make the verdict robust to a different prompt. Precision stayed 1.00 because `AGENTS#6` is *acceptable* on this PR; only the merge-verdict metric caught it.
**Change:** B8 now has an explicit criterion: **High only if the tests cannot fail** (trivial asserts, mocking the function under test, locking in a wrong behavior, no effective test); **"could be stronger" is Medium** (`gate/ai/prompts/r06_test_quality.md`, severity policy in `system.md`). Pinned by `tests/gate/ai/test_r06_test_severity_ai.py` (a score-validation-like fixture must not get a High; `streaks`-like tests that cannot fail must). The eval now measures prompt-variant stability: 1/8 flipping before, 0/8 after.

### fn-pr5-minors-to-sendgrid
**Why:** It's scaffolding: nothing calls SendGrid yet, so the outbound script has nothing to match. The AI judged the code that exists, not what the module is for.
**Change:** Add a script signal for vendor credentials (`SENDGRID_*`, `SEGMENT_*`...) next to a personal field. Then tell B2 to judge the module's purpose. Not done yet because I can't re-run the AI eval right now, and I won't ship a prompt change I haven't measured.

### fn-pr7-minors-to-analytics
**Why:** The PR is already blocked for retention and minimization, and the AI's fix covers this too. The model folds "data goes to analytics" into "too many fields".
**Change:** Add a fixture where minimization is fine but the destination is a third party, so #2 has to show up on its own.

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

Prompt injection: the script check (A17) has unit tests, and `tests/gate/ai/test_injection_resistance_ai.py` checks that the model still reports a minor's email in a log when the PR tells it not to. That AI test hasn't run here yet (no key). Not tested: PRs from forks.

Golden PRs are pinned to a commit (`head:` in the YAML). `support-context` had `develop` merged into it through "Update branch" on PR #10. Its diff turned into the whole gate, and the eval quietly lost a true positive until I pinned it.
