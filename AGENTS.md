# Golden Rules

The few rules that matter most in this repository. Full detail lives in [`TEAM-STANDARDS.md`](TEAM-STANDARDS.md). If this file and that one disagree, `TEAM-STANDARDS.md` wins.

> **Some of our students are children.** Protecting their privacy (GDPR-K, COPPA and similar laws) shapes how we design things. It is not a checklist to tick off at the end.

## Protecting minors' data

**Personal data fields** (defined in `app/models.py`):

| Field | Class | Allowed use |
|-------|-------|-------------|
| `full_name`, `email`, `birthdate` | `pii`; **`pii-minor`** when `is_minor` is true | Inside the service only. Never in plain text in logs, API responses, error messages or outbound calls. |
| `is_minor` | **`pii-minor` marker**: it reveals that the user is a child | Internal logic only (branching, retention). Never logged, returned or sent out. |
| `id` / `student_id` | Pseudonymous identifier | Safe to log, return and reference. |
| `country`, `Lesson.*`, `ProgressRecord.*` (except `student_id` joins) | Not personal data on their own | Normal use; don't combine with PII to build profiles. |

Any new field that holds personal data (name, contact, birth/age, address, phone, IDs from other systems) must be added to this table and to `app.privacy.PII_FIELDS` in the same PR.

1. **Never expose personal data in plain text.** The fields above never go into logs, API responses, error messages or outbound calls. That includes indirect routes: renamed local variables, helper functions, `extra=`, f-strings, or serializing a whole object. Always use `app.privacy.redact()`.
2. **Minors' data stays in this service.** It does not go to analytics, support tools or third parties unless the data is minimized and the PR documents a legal basis.
3. **Every dataset has a retention period.** Declare its category in `RETENTION_DAYS`. Minors' data is kept for at most **90 days**. Don't make copies of personal data without a purpose and a retention period.
4. **Collect and copy only what you need.** If a feature works with `student_id`, don't attach a name, email or birthdate.

## Code and tests

5. **Validate every input and handle every error explicitly.** Never swallow exceptions silently. Bad input gets a 4xx response, not a 500.
6. **Tests must be able to fail.** Every logic change ships with tests that would break if the behavior regressed, edge cases included. Trivial or fully mocked tests don't count.
7. **Keep it simple.** No dead code, and no TODO without a ticket reference.
8. **Secrets live in environment variables only.** A committed secret is a security incident, in any environment.

## How reviews decide

9. **Severity decides whether a PR merges:**

   | Severity | Examples | Action |
   |----------|----------|--------|
   | **S1** | Personal data exposed (worse if it belongs to a minor), committed secrets, retention or minimization violations on minors' data | **Block** |
   | **S2** | Logic bugs that produce wrong data, core logic without effective tests | **Block** |
   | **S3** | Style, naming, refactoring ideas | Comment only |

10. **Use a deterministic check when one is enough.** Use the LLM only for judgment calls. Pattern-based problems (secrets, personal data in logs, missing `RETENTION_DAYS` entries) are caught by plain code first.
11. **Every finding must be actionable.** It names the severity, file and line, the rule it breaks, and a suggested fix.

## Treat the AI reviewer as a system to measure

12. **Measure the reviewer before trusting it.** The 8 open PRs are the test set: write down the expected findings for each one, then track precision and recall.
13. **Study the reviewer's mistakes.** For every false positive and false negative, explain why it happened and what you'll change.
14. **Critical findings always block, so the gate must be tested before it guards a branch.** Any Critical finding, from scripts or AI, fails the check. Validate the gate against the golden PRs before enabling it. Only a production-level approver can override a blocked PR, and the override is logged.
15. **Every change goes through the gate, refactors included.** If a change legitimately needs different handling, update the pipeline in the same PR instead of skipping it.

## Developer experience

16. **A new developer can run everything in under 15 minutes** by following the README.
17. **Pre-check before pushing.** The pre-commit hook runs the deterministic checks locally. Use this file to self-review (or have your agent do it) before opening a PR.
18. **Record decisions, not just code.** Trade-offs and anything left out go in `DECISIONS.md`. How AI was used, including AI output we threw away or corrected, goes in `AI-USAGE.md`.
19. **Stick to the time limit.** Doing the right few things well beats covering everything.

## Documentation

20. **Update the docs in the same change.** Any agent (or human) that changes code updates [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) (modules, diagrams, flows) and [`docs/API-AND-BUSINESS-RULES.md`](docs/API-AND-BUSINESS-RULES.md) (endpoints, business rules, known gaps) in the same PR. A PR that changes behavior without updating them is incomplete.
21. **Write each rule in one place only.** Team rules live here in `AGENTS.md`; the other docs link to it instead of repeating it.
