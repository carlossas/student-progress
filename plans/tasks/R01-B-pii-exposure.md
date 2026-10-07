# R01-B — No personal data in plain text (AI)

**Rule:** AGENTS#1 · **Pipeline:** B · **Checks:** B1, B2, B3 · **Severity:** Critical · **Depends on:** R01-A, R11-B, R14-B

## Scope
Prompt section `gate/ai/prompts/r01_pii.md`, covering what semgrep cannot follow:
- **B1** Fields copied into renamed locals, passed across helpers, or unpacked from dicts or comprehensions, then reaching a log, response, error or outbound call.
- **B2** Derived personal data: age computed from `birthdate`, email domain, initials, unsalted hashes.
- **B3** Minor status revealed indirectly: `junior` flags, minors-only endpoints or lists.

The prompt includes the P4 alias signals and the R01-A findings, and tells the model not to repeat them.

## Test
`tests/gate/ai/test_r01_pii_exposure.py::test_r01_pii_exposure_ai` (`@pytest.mark.ai`)
- **Violation fixture** `fixtures/r01-ai/violation.diff`:
  - `contact = s.email` → `_describe(contact)` → `logger.info(...)`;
  - an endpoint returning `age` computed from `birthdate`;
  - `GET /students/juniors`.
- **Compliant fixture** `fixtures/r01-ai/compliant.diff`: the same features using `student_id` and `redact()`.
- **Expect:**
  - at least 3 Critical `AGENTS#1` findings in the violating file, one per case;
  - zero `AGENTS#1` findings on the compliant diff.
