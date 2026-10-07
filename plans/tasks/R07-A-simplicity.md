# R07-A — No dead code, TODO with ticket, lint (deterministic)

**Rule:** AGENTS#7 · **Pipeline:** A · **Checks:** A11, A12, A13 · **Severity:** Medium (A11, A12) / Low (A13) · **Depends on:** R11-A

## Scope
- **A11** `ruff` (`F401`, `F841`) + `vulture --min-confidence 80`: unused imports and variables, unreachable code.
- **A12** `gate/deterministic/todo_ticket.py`: `TODO`/`FIXME` without a ticket reference (`[A-Z]+-\d+`).
- **A13** `ruff check` + `ruff format --check`. Findings include ruff's autofix suggestion.

## Test
`tests/gate/deterministic/test_r07_simplicity.py::test_r07_simplicity`
- **Violation fixture:** an unused `import os`, an unused local variable, `# TODO: fix later`, and a mis-formatted line.
- **Compliant fixture:** a clean, formatted file containing `# TODO(OE-123): paginate`.
- **Expect:**
  - Medium `AGENTS#7` findings for the import, the variable and the TODO;
  - a Low `AGENTS#7` finding for the formatting;
  - zero `AGENTS#7` findings on the compliant fixture.
