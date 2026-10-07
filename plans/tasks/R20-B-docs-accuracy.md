# R20-B — Docs reflect the change (AI)

**Rule:** AGENTS#20 · **Pipeline:** B · **Check:** B9 · **Severity:** Medium · **Depends on:** R20-A, R11-B, R14-B

## Scope
Prompt section `gate/ai/prompts/r20_docs.md`. It receives the code diff and the full updated docs, then checks whether any of the following are missing or wrong in the docs:
- new or changed endpoints;
- business rules;
- known gaps;
- modules.

## Test
`tests/gate/ai/test_r20_docs_accuracy.py::test_r20_docs_accuracy_ai` (`@pytest.mark.ai`)
- **Violation fixture:** a diff that adds `GET /students/{id}/streak`. The docs were touched (a typo fix only), but the endpoint and its streak rule are not documented.
- **Compliant fixture:** the same diff, with the endpoint added to the endpoints table and a new BR row.
- **Expect:**
  - violation: a Medium `AGENTS#20` finding on `docs/API-AND-BUSINESS-RULES.md` that mentions the missing endpoint;
  - compliant: no `AGENTS#20` finding.
