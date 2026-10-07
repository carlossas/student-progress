# R02-B — Minors' data stays in the service (AI)

**Rule:** AGENTS#2 · **Pipeline:** B · **Check:** B4 · **Severity:** Critical · **Depends on:** R02-A, R11-B, R14-B

## Scope
Prompt section `gate/ai/prompts/r02_outbound.md`. For each A5 signal, the model decides:
- whether minors' data leaves the service;
- whether that data is minimized;
- whether the **PR description** documents a legal basis.

## Test
`tests/gate/ai/test_r02_minors_data_leaving.py::test_r02_minors_data_leaving_ai` (`@pytest.mark.ai`)
- **Violation fixture:** a diff that sends per-student progress with `country` and `birthdate` to a support tool. PR description: "Support needs context".
- **Compliant fixture:** a diff that sends only aggregated counts keyed by `student_id`. The PR description documents the purpose and legal basis.
- **Expect:**
  - violation: a Critical `AGENTS#2` finding in the file with the outbound call;
  - compliant: no `AGENTS#2` finding.
