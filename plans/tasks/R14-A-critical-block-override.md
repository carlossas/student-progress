# R14-A — Critical always blocks; logged production override (deterministic)

**Rule:** AGENTS#14 · **Pipeline:** A (gate code, applies to findings from both pipelines) · **Depends on:** R09-A, R12, R13

## Scope
- `GATE_MODE=shadow|enforce` (repo variable):
  - in `shadow`, Criticals are posted but the job exits 0;
  - switch to `enforce` once `EVAL.md` matches the ground truth.
- `gate/report/override.py` handles a `/gate-override <reason>` PR comment (`issue_comment` workflow):
  - checks through the GitHub API that the commenter belongs to `@org/production-approvers` (token secret with `read:org`);
  - requires a non-empty reason;
  - re-runs the report with the blocking checks marked as overridden;
  - records who, when, why and which findings in the run summary and as a PR comment.
- Any other user, or an override without a reason, is rejected with a reply comment.

## Test
`tests/gate/deterministic/test_r14_critical_block_override.py::test_r14_critical_block_override`
This test mocks the GitHub API.
- **Violation input:** one Critical finding in `enforce` mode, then three override attempts:
  - a non-member comments `/gate-override hotfix`;
  - a member comments `/gate-override` with no reason;
  - a member comments `/gate-override incident INC-42`.
- **Compliant input:** the same Critical finding in `shadow` mode.
- **Expect:**
  - violation, before any override: exit 1;
  - the first two override attempts are rejected, and the job still exits 1;
  - the third attempt succeeds: exit 0, with a record containing user, timestamp, reason and finding IDs;
  - compliant: exit 0 with the finding posted.
