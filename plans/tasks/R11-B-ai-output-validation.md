# R11-B — Gemini returns only valid, actionable findings (AI)

**Rule:** AGENTS#11 · **Pipeline:** B · **Depends on:** R11-A

## Scope
- `gate/ai/client.py`: calls Gemini with `response_schema` set to the R11 finding schema (array of findings).
- `gate/ai/validate.py`: drops and logs items that are invalid, meaning any of:
  - missing fields;
  - unknown severity;
  - an `AGENTS#n` rule that doesn't exist;
  - a `file` that isn't in the diff;
  - a `line` outside the changed hunk ±3.

  Dropped items are never posted. The run summary shows how many were dropped.

## Test
`tests/gate/deterministic/test_r11_ai_output_validation.py::test_r11_ai_output_validation`
This test runs offline: it uses a mocked Gemini response, because it tests the validation policy rather than the model.
- **Violation input:** a mocked response with 4 items:
  - one valid;
  - one with no `file`;
  - one with severity `"urgent"`;
  - one pointing at a file outside the diff.
- **Compliant input:** a mocked response with 2 valid items.
- **Expect:**
  - violation: exactly 1 finding survives, and the log and summary report 3 drops with their reasons;
  - compliant: both items survive and no drops are logged.
