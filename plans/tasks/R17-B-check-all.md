# R17-B — One command to check everything locally

**Rule:** AGENTS#17 (pre-check before pushing) · **Pipeline:** local (A + B) · **Depends on:** R17, R14-C

## Scope
- `python -m gate all` (`gate/local.py`), wrappers `scripts/check-all.sh` and `scripts/check-all.ps1`.
- Context: `DiffContext.from_worktree` = commits not on the base + staged + unstaged + untracked files; base defaults to `origin/develop`, `origin/main`, `main`.
- Steps: pre-commit checks (staged) → lint (`python -m gate lint [--fix]`: repo `ruff check` + gate format policy on changed files) → full tests + changed-line coverage → deterministic pipeline → AI pipeline.
- AI step runs only when `GEMINI_API_KEY` is set and `gate.ai.client.probe()` (model metadata request, no tokens) succeeds; otherwise **skipped** with the reason, never failed.
- One summary table and a final verdict: READY (exit 0) or BLOCKED (exit 1).
- Guide for developers: `PIPELINE_README.md`.

## Test
`tests/gate/deterministic/test_check_all.py::test_check_all` (offline, throwaway git repo)
- **Violation:** an untracked file logging `student.email`, no API key → exit 1, `AGENTS#1` reported, AI step "GEMINI_API_KEY is not set (deterministic checks only)".
- **Compliant:** logic + tests + both docs updated, invalid key (probe mocked) → exit 0, AI step skipped with the probe's reason, "RESULT: READY (AI skipped)".
