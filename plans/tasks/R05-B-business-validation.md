# R05-B — Business-level input validation (AI)

**Rule:** AGENTS#5 · **Pipeline:** B · **Check:** B7 · **Severity:** High · **Depends on:** R05-A, R11-B, R14-B

## Scope
Prompt section `gate/ai/prompts/r05_validation.md`. It covers validation that a type check can't express:
- IDs that must exist (for example, `lesson_id` in the catalog);
- value ranges (for example, `score` must be 0–100);
- inputs that still lead to a 500 instead of a 4xx.

The prompt includes `docs/API-AND-BUSINESS-RULES.md` as domain context.

## Test
`tests/gate/ai/test_r05_business_validation.py::test_r05_business_validation_ai` (`@pytest.mark.ai`)
- **Violation fixture:** a Pydantic model with `score: int` (no bounds), and a handler that stores any `lesson_id` without checking `store.LESSONS`.
- **Compliant fixture:** `score: int = Field(ge=0, le=100)`, and a handler that returns 404 for an unknown `lesson_id`.
- **Expect:**
  - violation: High `AGENTS#5` findings for both the missing score range and the missing lesson check;
  - compliant: no `AGENTS#5` finding.
