### AGENTS#1 — personal data in plain text (B1, B2, B3) · critical

Personal fields: `full_name`, `email`, `birthdate`, `is_minor` (see the field table in AGENTS.md), plus any field the diff adds that holds personal data. A "sink" is a log/print call, an API response, an exception/error message, or an outbound call.

- **B1 Indirect flow.** A personal field copied into a renamed variable (`contact = s.email`), passed through helpers (possibly in another file), unpacked from dicts, built in comprehensions or f-strings, then reaching a sink. Follow the value across functions and files in the diff. `redact()` makes a value safe.
- **B2 Derived personal data.** Age computed from `birthdate`, email domain or local part, initials, unsalted hashes of email: still personal data when it reaches a sink.
- **B3 Minor status revealed.** `is_minor` exposed indirectly: `junior`/`kid` flags, minors-only endpoints or lists, filters whose output tells an outsider who is a child.

The hints section may flag suspicious identifiers (P4); verify them, they can be false alarms.
