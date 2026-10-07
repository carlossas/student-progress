# R05-A — Validate input, handle errors explicitly (deterministic)

**Rule:** AGENTS#5 · **Pipeline:** A · **Checks:** A6, A7 · **Severity:** High · **Depends on:** R11-A

## Scope
- **A6** `ruff` with rules `E722`, `BLE001`, `S110`: bare or broad `except`, and `except: pass`.
- **A7** `.semgrep/validation.yml`: route handlers that take a raw `dict` (or untyped body) instead of a Pydantic model.

Both checks convert their tool output to findings through R11-A.

## Test
`tests/gate/deterministic/test_r05_validation_errors.py::test_r05_validation_errors`
- **Violation fixture:**
  - `@app.post(...) def h(payload: dict)`;
  - `try: ... except Exception: pass`.
- **Compliant fixture:**
  - `def h(payload: ProgressIn)`, where `ProgressIn` is a Pydantic model;
  - `except KeyError as e: raise HTTPException(422, ...) from e`.
- **Expect:**
  - two High `AGENTS#5` findings on the handler line and the `except` line, the first suggesting a Pydantic model;
  - zero `AGENTS#5` findings on the compliant fixture.
