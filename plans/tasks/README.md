# Quality gate — tasks

Breakdown of [../quality-gate-classification.md](../quality-gate-classification.md) into one task per rule and pipeline. Rule numbers refer to [AGENTS.md](../../AGENTS.md).

**Status: all tasks implemented.** Tool substitutions (AST checks instead of semgrep/gitleaks/diff-cover, two statuses, `_ai` test suffix) are listed in section 8 of the plan.

## Conventions

- **Naming:** `R<rule>-<pipeline>`. `A` = deterministic (scripts, linters, gate code), `B` = AI (Gemini). Gate infrastructure tasks that belong to neither have no suffix. A rule enforced by both pipelines has two tasks.
- **One test per task.** Each task defines exactly one test function that proves its policy (exception: R14-C has one offline test per cost control):
  - It runs the check on a **violation fixture** and asserts the expected findings (`rule`, `severity`, `file`, and `line` when available).
  - It runs the same check on a **compliant fixture** and asserts **no** finding for that rule, to guard against false positives.
- **Test locations:**
  - Deterministic: `tests/gate/deterministic/test_rXX_*.py`. Offline; run on every PR and on pre-push.
  - AI: `tests/gate/ai/test_rXX_*_ai.py`. Marked `@pytest.mark.ai`, call Gemini with `GEMINI_API_KEY`, excluded by default (`addopts = -m "not ai"`). They run in the eval workflow and on any PR that changes `gate/ai/**`. They assert on `rule`, `severity` and `file`, never on message wording.
  - Fixtures: `tests/gate/fixtures/rXX/{violation,compliant}/`. Secrets in fixtures are obviously fake, and each fixture file is allowlisted individually in `gate/config/secret-allowlist.txt`.
- **Code layout:** `gate/deterministic/`, `gate/ai/` (client + `prompts/`), `gate/report/` (schema, actions, override), `gate/eval/`, `gate/hooks/`, `gate/config/`, `.github/workflows/quality-gate.yml`.
- **Done means:** the test passes, docs are updated (AGENTS#20), and findings follow the R11 schema.

## Order

| Phase | Tasks |
|-------|-------|
| 1. Foundation | [R01-P](R01-P-is-minor-in-pii-fields.md), [R11-A](R11-A-finding-schema.md), [R11-B](R11-B-ai-output-validation.md), [R09-A](R09-A-severity-actions.md) |
| 2. Deterministic checks | [R08-A](R08-A-secrets.md), [R01-A](R01-A-pii-exposure.md), [R02-A](R02-A-outbound-minors-data.md), [R03-A](R03-A-retention.md), [R05-A](R05-A-input-validation-errors.md), [R06-A](R06-A-tests-coverage.md), [R07-A](R07-A-simplicity.md), [R20-A](R20-A-docs-updated.md), [R16-A](R16-A-readme-smoke.md), [R18-A](R18-A-decision-records.md) |
| 3. AI checks | [R14-B](R14-B-ai-determinism.md), [R14-C](R14-C-ai-cost-controls.md), [R01-B](R01-B-pii-exposure.md), [R02-B](R02-B-minors-data-leaving.md), [R03-B](R03-B-secondary-copies.md), [R04-B](R04-B-data-minimization.md), [R05-B](R05-B-business-validation.md), [R06-B](R06-B-test-quality.md), [R09-B](R09-B-logic-bugs-style.md), [R20-B](R20-B-docs-accuracy.md), [R21-B](R21-B-single-source-rules.md) |
| 4. Orchestration | [R10](R10-pipeline-orchestration.md), [R17](R17-local-hooks.md), [R17-B](R17-B-check-all.md) |
| 5. Evaluation | [R12](R12-eval-metrics.md), [R13](R13-failure-analysis.md) |
| 6. Enforcement | [R14-A](R14-A-critical-block-override.md), [R15](R15-triggers-required-checks.md) |

Enforcement comes last: the checks stay in shadow mode until the eval matches the ground truth (AGENTS#14).

## Added after the live review (PR #22)

No task file: each has its own offline test.

| Feature | Code | Test |
|---|---|---|
| A17 prompt-injection check (AGENTS#15) | `gate/deterministic/prompt_injection.py` | `tests/gate/deterministic/test_prompt_injection.py`, `tests/gate/ai/test_injection_resistance_ai.py` |
| Findings on moved lines demoted (pre-existing debt) | `gate/report/baseline.py` | `tests/gate/deterministic/test_pre_existing_debt.py` |
| Secrets masked before any Gemini request | `gate/deterministic/secrets_scan.py` (`mask_secrets`), `gate/ai/prompt_builder.py` | `tests/gate/deterministic/test_secret_masking.py` |
| Severity refinements (copies of personal data Critical, A9 absorbs A10) | `gate/deterministic/pii_flow.py`, `gate/report/merge.py` | `tests/gate/deterministic/test_severity_refinements.py` |
| Per-base status checks | `gate/config.py` (`status_contexts`) | R09-A, R14-A tests |
| B8 severity: High only if tests cannot fail; "could be stronger" is Medium | `gate/ai/prompts/r06_test_quality.md` | `tests/gate/ai/test_r06_test_severity_ai.py` |
| Verdict stability across prompt variants | `gate/eval/run_eval.py` (`--variants`) | `test_r12_stability_across_prompt_variants` |

## Rules without a task

- **AGENTS#19 (timebox):** process only; tracked in `DECISIONS.md`.
