# Decisions

Rules: [AGENTS.md](AGENTS.md). Full design: [plans/quality-gate-classification.md](plans/quality-gate-classification.md).

## ADR-1 · Scripts first, LLM only for judgment

Patterns go to scripts: secrets, PII reaching logs/responses/outbound calls, retention, TODOs, coverage. They're plain Python over `ast`, so they're free, exact and fast enough for pre-commit. The LLM only gets what a script can't decide: renamed data, minimization, weak tests, logic vs business rules.
I dropped semgrep/gitleaks/diff-cover: no native Windows support, an extra binary, and semgrep's taint mode doesn't follow helper calls (which is how `support-context` leaks).
Trade-off: we maintain our own patterns.

## ADR-2 · The gate runs from the base branch; the AI job never runs PR code

Prompts, config and rules come from the base branch, so a PR can't loosen its own review. Only the AI job has the API key, and it only reads files.
- **Secrets are masked** before anything goes to Gemini (`mask_secrets`). The model doesn't need the value, and Gemini is a third party.
- **Prompt injection** gets two layers. The system prompt treats PR text as data, and a script (A17) flags text aimed at the reviewer (telling it to drop its rules or return an empty review) as High. The script doesn't depend on the model it protects.
Compatibility: the workflow comes from the PR but the gate code from the base, so new inputs go in env vars and never as new CLI flags. PR #21's new flag crashed `develop`'s older gate.
Gap: on `pull_request` a PR can edit the workflow file. Today `workflow_policy` flags that edit; the real fix is CODEOWNERS (backlog).

**Current base, not the event's.** The gate is checked out from the base branch's current tip (`github.base_ref`) and diffs against the first parent of the PR's merge commit. `github.event.pull_request.base.sha` is stale on reopened and older PRs: a reopen on PR #12 ran a gate from before #19–#22, with old check names and severities.

## ADR-3 · What blocks

| Finding | Effect |
|---|---|
| Critical (scripts or AI) | Fails the check, merge blocked |
| High | Request changes, merge blocked |
| High on a moved line (#5/#7/#9) | Demoted to Medium |
| Medium / Low, process rules (#16/#18/#20) | Comment only |
| Gate crash / Gemini error | Blocks, never a silent pass |

The checks are named per base branch (`quality-gate/<base>/critical`, `.../high`). A status belongs to a commit, so one branch with PRs into `develop` and `main` used to overwrite its own checks.

Critical/High = S1/S2 from TEAM-STANDARDS, nothing invented. Two calls came from measuring:
- **Docs rule doesn't block.** It blocked the only clean PR, and it isn't a team standard.
- **Moved lines don't block on code quality.** Otherwise fixing old code gets punished. Privacy, secrets and tests are never demoted.

`/gate-override <reason>` (admin/maintain) flips the statuses for that commit and is logged on the PR. Rollout: `shadow` until the eval passes, `enforce` after.

## ADR-4 · One Gemini call per PR, stable and cheap

One structured call with temperature 0 and a fixed seed: temperature alone still flipped a High between runs. The seed only makes *identical* prompts repeat: a prompt that differed in an irrelevant way (the order of the scripts' findings) flipped `score-validation` in CI. The fix was a sharper criterion, not more randomness control: ambiguous severity rules get resolved at random. The eval now measures stability across prompt variants (`--variants`). LOW thinking and a JSON schema. Findings with an unknown rule or a line outside the diff are dropped, never posted.
Cost is ~$0.003 per review: cache by request hash, output capped at 2k tokens, large PRs split into ≤30k-token batches.

## ADR-5 · The eval's headline is the merge verdict

My first eval scored only AGENTS#1-9. It said 1.00/1.00 while the live gate was blocking the clean PR through a rule it didn't score. So now the verdict per PR comes first and counts every finding. I only change the ground truth with an argument about the code, and log each change.

## ADR-6 · Scaling past one repo

Not built, but this is the order I'd do it in:
1. **Reusable workflow + package**, versioned. Each repo only configures its PII fields and retention.
2. **Bedrock instead of Gemini.** Code stays in our AWS account, access goes through IAM, no extra DPA. The client is already one interface; I'd re-run the eval before switching.
3. **SLO + degraded mode.** Today a Gemini outage blocks every merge.
4. **Cost at scale is CI, not the LLM.** 100 devs is ~900 reviews/day: ~$4/day of AI vs ~$22/day of runner minutes.
5. **Measure in production.** Override rate, false blocks, time-to-merge. Every override becomes a fixture.
6. **The gate is one layer.** In production: CloudWatch log data protection, Macie, PII tagged in the models.

## Left out (priority order)

1. CODEOWNERS on `.github/` and `gate/`.
2. Fork PRs (no secrets → the AI job fails closed).
3. Auto-open an incident + rotation runbook on a committed secret.
4. Make the `eval` check required for PRs that touch `gate/ai/` (#26 merged with it red).
