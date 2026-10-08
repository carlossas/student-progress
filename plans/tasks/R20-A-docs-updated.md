# R20-A — Docs updated in the same change (deterministic)

**Rule:** AGENTS#20 · **Pipeline:** A · **Check:** A14 · **Severity:** High · **Depends on:** R11-A

## Scope
`gate/deterministic/change_policy.py` (`docs_touched`), diff mode: if any file under `app/` changed, both `docs/ARCHITECTURE.md` and `docs/API-AND-BUSINESS-RULES.md` must appear in the diff.
- Refactors are included, with no skip label.
- The finding is file-level and names the missing doc or docs.

## Test
`tests/gate/deterministic/test_r20_docs_updated.py::test_r20_docs_updated`
- **Violation input:** a changed-file list of `app/main.py` and `tests/test_progress.py`.
- **Compliant input:** a changed-file list of `app/main.py`, `tests/test_progress.py`, `docs/ARCHITECTURE.md` and `docs/API-AND-BUSINESS-RULES.md`.
- **Expect:**
  - violation: one High `AGENTS#20` finding that names both docs;
  - compliant: zero findings;
  - a docs-only change (no `app/` files) also produces zero findings.
