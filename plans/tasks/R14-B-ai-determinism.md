# R14-B — Stable AI output so Criticals can block (AI)

**Rule:** AGENTS#14 · **Pipeline:** B · **Depends on:** R11-B

## Scope
- `gate/ai/config.py` sets:
  - `temperature=0`;
  - **low thinking level**;
  - the JSON `response_schema`;
  - the model from the `GEMINI_MODEL` repo variable;
  - the key from the `GEMINI_API_KEY` secret.
- The prompt asks for findings in a fixed order (by rule, then file, then line) to reduce variation.
- A fixed sampling `seed` (`gate/ai/config.py`): measured on 2026-10-07, temperature 0 alone let a High finding come and go between identical runs; with the seed, 3 runs are identical.
- On an API error or timeout, the `ai` job fails with an error. It never passes silently (AGENTS#5).

## Test
`tests/gate/ai/test_r14_ai_determinism_ai.py::test_r14_ai_determinism` (`@pytest.mark.ai`)
- **Violation input:** the R01-B violation diff, reviewed 3 times.
- **Compliant input:** the R01-B compliant diff, reviewed 3 times.
- **Expect:**
  - violation: the set of `(rule, severity, file)` is identical across all 3 runs, and each run includes Critical `AGENTS#1`;
  - compliant: all 3 runs return no Critical finding.
