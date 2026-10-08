# R03-A — Retention declared, minors ≤ 90 days (deterministic)

**Rule:** AGENTS#3 · **Pipeline:** A · **Checks:** A3, A4 · **Severity:** Critical (A3) / High (A4) · **Depends on:** R11-A

## Scope
- **A3** `gate/deterministic/retention.py`: every `RETENTION_DAYS` key containing `minor` is ≤ 90.
- **A4** same script, diff mode: a new module-level collection, file write or DB write in `app/` requires a `RETENTION_DAYS` change in the same PR.

## Test
`tests/gate/deterministic/test_r03_retention.py::test_r03_retention`
- **Violation fixture:**
  - `RETENTION_DAYS = {"progress": 365, "progress_minor": 180}`;
  - a diff adding `ARCHIVE: list = []` to `app/store.py` without touching `RETENTION_DAYS`.
- **Compliant fixture:** `progress_minor: 90`, and a diff that adds `ARCHIVE` together with `"archive_minor": 90`.
- **Expect:**
  - a Critical `AGENTS#3` finding on the `progress_minor` line, suggesting a cap of 90;
  - a High `AGENTS#3` finding on the `ARCHIVE` line;
  - zero `AGENTS#3` findings on the compliant fixture.
