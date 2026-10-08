# R18-A — Decision and AI-usage records exist (deterministic)

**Rule:** AGENTS#18 · **Pipeline:** A · **Check:** A16 · **Severity:** Low · **Depends on:** R11-A

## Scope
`gate/deterministic/change_policy.py` (`records`):
- checks that `DECISIONS.md` and `AI-USAGE.md` exist at the repo root;
- checks that neither file is empty, meaning each has at least one heading beyond the title.

## Test
`tests/gate/deterministic/test_r18_decision_records.py::test_r18_decision_records`
- **Violation fixture:** a repo root with `DECISIONS.md` (containing only a title) and no `AI-USAGE.md`.
- **Compliant fixture:** both files present, each with content sections.
- **Expect:**
  - violation: two Low `AGENTS#18` findings, one for the empty `DECISIONS.md` and one for the missing `AI-USAGE.md`;
  - compliant: zero findings.
