# R01-A — No personal data in plain text (deterministic)

**Rule:** AGENTS#1 · **Pipeline:** A · **Checks:** P1, P2, P3, P4 · **Severity:** Critical · **Depends on:** R01-P, R11-A

## Scope
- **P1** `gate/deterministic/pii_registry.py`: dataclass fields in `app/models.py` with personal-looking names (`name`, `mail`, `birth`, `dob`, `age`, `phone`, `address`, `minor`, `document`) must be in `PII_FIELDS`.
- **P2** `gate/deterministic/pii_flow.py`, AST taint tracking with one level of cross-function summaries:
  - sources: `full_name`, `email`, `birthdate`, `is_minor` (as attribute, dict key or kwarg);
  - sanitizer: `redact()`;
  - Critical sinks: logging, `print`, exception messages, route return values, outbound calls;
  - Critical sink: new persisted collections (raised from High on 2026-10-07, see `tests/gate/deterministic/test_severity_refinements.py`).
- **P3** same file: `Student` objects reaching a sink through `__dict__`, `asdict()`, `vars()`, `str()`, `repr()` or f-strings.
- **P4** `gate/deterministic/pii_alias.py`: PII-like identifiers on changed lines are written to `signals.json` (not posted).

## Test
`tests/gate/deterministic/test_r01_pii_exposure.py::test_r01_pii_exposure`
- **Violation fixture** `fixtures/r01/violation/`:
  - `logger.info(student.email)`;
  - a route returning `{"email": s.email}`;
  - `HTTPException(detail=f"{student}")`;
  - `logger.info(asdict(student))`;
  - a model with a `phone` field that is missing from `PII_FIELDS`.
- **Compliant fixture** `fixtures/r01/compliant/`: `logger.info(redact({...}))`, and a route returning `{"student_id": s.id}`.
- **Expect:**
  - 5 Critical `AGENTS#1` findings, one per violation line, with a `redact()` suggestion where applicable;
  - zero `AGENTS#1` findings on the compliant fixture.
