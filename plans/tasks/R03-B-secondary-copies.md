# R03-B — No secondary copies without purpose and retention (AI)

**Rule:** AGENTS#3 · **Pipeline:** B · **Check:** B5 · **Severity:** Critical (minors) / High · **Depends on:** R03-A, R11-B, R14-B

## Scope
Prompt section `gate/ai/prompts/r03_copies.md`. It detects copies of personal data (archives, caches, denormalized events) that have no declared purpose or retention category. This includes copies built indirectly, such as an event enriched with student attributes.

## Test
`tests/gate/ai/test_r03_secondary_copies.py::test_r03_secondary_copies_ai` (`@pytest.mark.ai`)
- **Violation fixture:** a diff that archives each progress event enriched with `country`, `birthdate` and `is_minor` "for cohort analytics", with no retention entry.
- **Compliant fixture:** an archive holding only `student_id`, `lesson_id` and `score`, with `RETENTION_DAYS["archive"]` declared and the purpose stated in the docstring.
- **Expect:**
  - violation: a Critical `AGENTS#3` finding, because minors' data is involved;
  - compliant: no `AGENTS#3` finding.
