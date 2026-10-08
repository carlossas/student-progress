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
Cost is ~$0.004 per review: cache by request hash, output capped at 4k tokens (doubled up to 16k if a review needs it), large PRs split into ≤30k-token batches. The cap was 2k until a review with many real problems got cut off in CI.

## ADR-5 · The eval's headline is the merge verdict

My first eval scored only AGENTS#1-9. It said 1.00/1.00 while the live gate was blocking the clean PR through a rule it didn't score. So now the verdict per PR comes first and counts every finding. I only change the ground truth with an argument about the code, and log each change.

## ADR-6 · Scaling past one repo

Not built, but this is the order I'd do it in:
1. **One shared gate**, versioned (backlog #1). Each repo only configures its PII fields and retention.
2. **Bedrock instead of Gemini.** Code stays in our AWS account, access goes through IAM, no extra DPA. The client is already one interface; I'd re-run the eval before switching.
3. **SLO + degraded mode** (backlog #4).
4. **Cost at scale is CI, not the LLM.** 100 devs is ~900 runs/day: ~$4/day of AI vs ~$22/day of runner minutes, most of it per-job rounding. Fewer, merged jobs come first (backlog #10).
5. **Measure in production.** Override rate, false blocks, time-to-merge. Every override becomes a fixture.
6. **The gate is one layer.** In production: CloudWatch log data protection, Macie, PII tagged in the models.

## Backlog (priority order)

1. **One shared gate for every service.** Move the pipeline and its tests into their own repo or package, so a fix lands everywhere at once. Version the tests, prompts and LLM settings together, and let each service pin a version and upgrade when it's ready.
2. **Make `gate-eval` a required check** on PRs that touch `gate/ai/`. #26 merged with it red because nothing stopped it.
3. **CODEOWNERS** on `.github/` and `gate/`, so the gate can't be edited by the PR it reviews.
4. **Degraded mode.** Today a Gemini outage blocks every merge.
5. **Tickets for what gets left behind.** When a developer merges without fixing a Medium or Low comment, open a ticket for it automatically, linked to the PR and the line. Nothing gets lost, and the merge isn't blocked.
6. **A dashboard per developer.** Which mistakes show up most, how PRs are trending, code quality over time. The point is to know where to coach, not to rank people.
7. **Fork PRs.** They get no secrets, so the AI job fails closed and the report can't comment.
8. **Secret incident flow.** A committed secret should open an incident with the rotation steps, not just block.
9. **The last known miss** (`fn-pr7-minors-to-analytics` in EVAL.md): a fixture where minimization is fine but the data goes to a third party.
10. **Fewer CI jobs.** A gate run does about 1.5 minutes of real work but gets billed 4, because GitHub rounds every job up to a full minute and we have 4 of them. Putting the checks in one or two jobs should cut the CI bill roughly in half. It's free on this public repo, but on a private one CI is most of the bill, so I'd do this before switching to a cheaper model.
