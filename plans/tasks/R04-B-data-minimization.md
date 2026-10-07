# R04-B — Collect and copy only what you need (AI)

**Rule:** AGENTS#4 · **Pipeline:** B · **Check:** B6 · **Severity:** Critical (minors) / High · **Depends on:** R11-B, R14-B

## Scope
Prompt section `gate/ai/prompts/r04_minimization.md`. It flags features that attach name, email, birthdate or `is_minor` when `student_id` would be enough for the stated purpose. The finding is Critical when the data can belong to minors.

## Test
`tests/gate/ai/test_r04_data_minimization.py::test_r04_data_minimization_ai` (`@pytest.mark.ai`)
- **Violation fixture:** a support helper that builds a lookup context with `full_name`, `email` and `birthdate` to "speed up tickets".
- **Compliant fixture:** the same helper returning only `student_id`, progress counts and the last lesson.
- **Expect:**
  - violation: a Critical `AGENTS#4` finding on the helper;
  - compliant: no `AGENTS#4` finding.
