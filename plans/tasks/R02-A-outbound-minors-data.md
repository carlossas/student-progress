# R02-A — Minors' data stays in the service (deterministic)

**Rule:** AGENTS#2 · **Pipeline:** A · **Checks:** P2 (outbound sinks), A5 · **Severity:** Critical / signal · **Depends on:** R01-A

## Scope
- **P2 outbound sinks** in `gate/deterministic/pii_flow.py` (AST taint tracking): personal fields reaching `httpx`, `requests`, `smtplib`, analytics or support SDKs, queues or file exports are Critical.
- **A5** `pii_flow.outbound_signals()`: any new outbound channel (import, client, logging handler, file export) is written to `signals.json` for R02-B. It is not posted.

## Test
`tests/gate/deterministic/test_r02_outbound.py::test_r02_outbound_minors_data`
- **Violation fixture:** `httpx.post(ANALYTICS_URL, json={"birthdate": s.birthdate, "is_minor": s.is_minor})`.
- **Compliant fixture:** `httpx.post(ANALYTICS_URL, json={"student_id": s.id, "lesson_id": l})`.
- **Expect:**
  - violation: one Critical `AGENTS#2` finding on the `httpx.post` line;
  - compliant: no posted finding, but one A5 entry in `signals.json`.
