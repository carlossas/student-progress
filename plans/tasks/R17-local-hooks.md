# R17 — Pre-check before pushing (husky hooks)

**Rule:** AGENTS#17 · **Pipeline:** local (subset of A) · **Depends on:** R01-A, R03-A, R05-A, R07-A, R08-A, R06-A

## Scope
- A minimal `package.json` with `husky` as a dev dependency, and a `prepare` script. The README adds `npm install` to the setup steps.
- `.husky/pre-commit` calls `gate/hooks/pre_commit.sh` on staged files:
  - `gitleaks protect --staged`;
  - `ruff check` and `ruff format --check`;
  - semgrep rules P2, P3, A6, A7;
  - P1 registry sync;
  - A3 retention;
  - A12 TODO check.

  Target runtime: under 10 seconds.
- `.husky/pre-push` calls `gate/hooks/pre_push.sh`: `pytest` + `diff-cover --fail-under 85` against `origin/develop`.
- Both hooks print findings in the same format as CI, and exit non-zero on Critical or High findings.

## Test
`tests/gate/deterministic/test_r17_local_hooks.py::test_r17_local_hooks`
The test calls `gate/hooks/pre_commit.sh` directly in a throwaway git repo, so Node isn't needed.
- **Violation input:** stage a file with a fake API key and `logger.info(student.email)`.
- **Compliant input:** stage a clean file.
- **Expect:**
  - violation: exit code ≠ 0, with output listing the `AGENTS#8` and `AGENTS#1` findings;
  - compliant: exit 0 in under 10 seconds.
