# R09-B — S2 logic bugs and S3 style (AI)

**Rule:** AGENTS#9 · **Pipeline:** B · **Checks:** B11, B12 · **Severity:** High (logic) / Low (style) · **Depends on:** R11-B, R14-B

## Scope
Prompt section `gate/ai/prompts/r09_logic_style.md`:
- **B11** Logic bugs that produce incorrect data (S2): wrong formulas, double counting, off-by-one, broken edge cases. The prompt uses the business rules in `docs/API-AND-BUSINESS-RULES.md` as the expected behavior.
- **B12** Style, naming and refactoring ideas (S3). These are always Low and never block.

## Test
`tests/gate/ai/test_r09_logic_bugs_style.py::test_r09_logic_bugs_style_ai` (`@pytest.mark.ai`)
- **Violation fixture:**
  - the progress percentage counts duplicate completions, so it can exceed 100;
  - a variable is named `x2`.
- **Compliant fixture:** completions are de-duplicated by `lesson_id`, with clear names.
- **Expect:**
  - violation: a High `AGENTS#9` finding on the percentage logic, and a Low finding on the naming;
  - compliant: no High `AGENTS#9` finding. Low style findings are allowed but not required.
