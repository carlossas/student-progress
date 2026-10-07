# R09-A — Severity decides the merge action (deterministic)

**Rule:** AGENTS#9 · **Pipeline:** A (gate code, shared by both pipelines) · **Depends on:** R11-A

## Scope
`gate/report/actions.py` turns a list of findings into PR actions, following section 2 of the plan:

| Severity | Job | `quality-gate/<base>/high` status | Review | Comment |
|----------|-----|----------------------------|--------|---------|
| Critical | exit 1 + error log | — | Request changes | Inline, with suggestion |
| High | exit 0 | failure | Request changes | Inline |
| Medium | exit 0 | success | Comment | Inline |
| Low | exit 0 | success | Comment | Grouped in summary |

Findings without a `line` become file-level comments. It also writes the run summary (`$GITHUB_STEP_SUMMARY`).

## Test
`tests/gate/deterministic/test_r09_severity_actions.py::test_r09_severity_actions`
- **Violation input** (one finding per severity, parametrized): a Critical, a High, a Medium and a Low finding.
- **Compliant input:** an empty findings list.
- **Expect:**
  - exactly the exit code, status, review event and comment placement from the table for each severity;
  - for the empty list: exit 0, status success, no review posted.
