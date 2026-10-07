# R01-P — Add `is_minor` to `PII_FIELDS` (prerequisite)

**Rule:** AGENTS#1 · **Pipeline:** app code · **Depends on:** none · **Blocks:** R01-A, R01-B

## Scope
`is_minor` is a `pii-minor` marker (see the field table in AGENTS.md), but `redact()` does not mask it today. The gate reads its field list from `app.privacy.PII_FIELDS`, so that list must be complete first.

## Steps
- [ ] Add `is_minor` to `PII_FIELDS` in `app/privacy.py`.
- [ ] Update `docs/ARCHITECTURE.md` and `docs/API-AND-BUSINESS-RULES.md` (BR-6).

## Test
`tests/test_privacy.py::test_redact_masks_every_personal_field`
- **Input:** `{"student_id": "s-001", "full_name": "x", "email": "x", "birthdate": "x", "is_minor": True}`
- **Expect:** all four personal fields become `"[REDACTED]"`; `student_id` is unchanged.
