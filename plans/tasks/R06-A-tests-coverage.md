# R06-A — Tests exist, pass and cover changed lines (deterministic)

**Rule:** AGENTS#6 · **Pipeline:** A · **Checks:** A8, A9, A10 · **Severity:** High · **Depends on:** R11-A

## Scope
- **A8** `pytest`: a failing test produces a finding with the test name.
- **A9** `gate/deterministic/tests_touched.py`: `app/` changed but `tests/` not changed. This applies to refactors too.
- **A10** `pytest-cov` + `diff-cover`: changed lines must reach **≥ 85%** coverage. Each uncovered line is reported.

## Test
`tests/gate/deterministic/test_r06_tests_coverage.py::test_r06_tests_coverage`
The test builds two throwaway git repos in `tmp_path`, each with a `main` commit and a feature commit.
- **Violation repo:** the feature adds an untested branch in `app/` (coverage of changed lines below 85%), changes no file under `tests/`, and contains one failing test.
- **Compliant repo:** the feature adds the logic together with tests covering 100% of the changed lines, and all tests pass.
- **Expect:**
  - violation: three High `AGENTS#6` findings, one each from A8, A9 and A10;
  - compliant: zero `AGENTS#6` findings.
