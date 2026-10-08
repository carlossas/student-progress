# R11-A — Actionable finding schema for scripts (deterministic)

**Rule:** AGENTS#11 · **Pipeline:** A · **Depends on:** none · **Blocks:** every check task

## Scope
- `gate/report/schema.json`: JSON Schema for a finding (`rule`, `severity`, `source`, `file`, `line?`, `message`, `suggestion`), as defined in plan section 2.
- `gate/report/finding.py`: a `Finding` dataclass plus validation.
- `gate/report/adapters.py`: converters from `ruff`, `ruff format`, `vulture`, pytest JUnit and coverage.xml into `Finding` (the gate's own checks build findings directly). Each maps the tool's rule ID to an `AGENTS#n` rule and a severity, using one table in `gate/config/rule_map.yml`.

## Test
`tests/gate/deterministic/test_r11_finding_schema.py::test_r11_finding_schema`
- **Violation input:**
  - recorded raw outputs from each tool (`fixtures/r11/ruff.json`, `vulture.txt`, `junit.xml`, `coverage.xml`);
  - one tool rule ID that is not mapped in `rule_map.yml`.
- **Compliant input:** the same tool outputs, with every rule ID mapped.
- **Expect:**
  - every mapped item becomes a `Finding` that validates against the schema, with a non-empty `rule`, `severity`, `file` and `suggestion`;
  - the unmapped rule ID raises an explicit error. It is never dropped silently (AGENTS#5).
