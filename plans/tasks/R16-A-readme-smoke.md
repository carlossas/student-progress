# R16-A — README runnable in under 15 minutes (deterministic)

**Rule:** AGENTS#16 · **Pipeline:** A · **Check:** A15 · **Severity:** Medium · **Depends on:** R11-A

## Scope
- `gate/deterministic/readme_smoke.py`:
  1. extracts the `bash` code blocks under "Running locally" in `README.md`;
  2. runs them in order on a fresh runner, starting `uvicorn` in the background and checking `GET /health`;
  3. stops with a total timeout of 15 minutes.
- A failure produces a Medium finding on `README.md` that names the failing command.
- `readme-smoke` job in `quality-gate.yml`; it runs on every PR.

## Test
`tests/gate/deterministic/test_r16_readme_smoke.py::test_r16_readme_smoke`
- **Violation fixture:** a README whose second `bash` block runs a command that exits 1 (for example, `pip install -r requirement.txt` with a typo, stubbed).
- **Compliant fixture:** a README whose blocks all succeed (stubbed commands, health check mocked).
- **Expect:**
  - violation: one Medium `AGENTS#16` finding on `README.md` that quotes the failing command;
  - compliant: zero findings;
  - when the timeout is exceeded (simulated with a 1-second limit), the result is a Medium finding.
