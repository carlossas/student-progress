# R06-B — Tests make sense (AI)

**Rule:** AGENTS#6 · **Pipeline:** B · **Check:** B8 · **Severity:** High · **Depends on:** R06-A, R11-B, R14-B

## Scope
Prompt section `gate/ai/prompts/r06_test_quality.md`. It judges whether tests can actually fail when behavior breaks. It flags:
- trivial asserts;
- fully mocked logic;
- asserts on the implementation instead of the behavior;
- missing edge cases;
- tests written only to reach the 85% coverage threshold.

The prompt receives the A10 coverage report so the model can spot high coverage with weak asserts.

## Test
`tests/gate/ai/test_r06_test_quality.py::test_r06_test_quality_ai` (`@pytest.mark.ai`)
- **Violation fixture:** a diff that adds percentage logic. Its tests:
  - `assert resp.status_code in (200, 404)`;
  - mock the function under test;
  - assert `True`;
  - never test zero lessons or duplicates.
- **Compliant fixture:** the same logic, with tests asserting exact values for normal, zero-lesson and duplicate-completion cases.
- **Expect:**
  - violation: at least one High `AGENTS#6` finding located in the test file;
  - compliant: no `AGENTS#6` finding.
