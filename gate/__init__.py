"""AI quality gate: deterministic checks + Gemini review of pull requests against AGENTS.md.

Entry point: `python -m gate <command>` (see gate/__main__.py).
The gate always runs from the BASE branch checkout; the PR checkout is only data.
"""
