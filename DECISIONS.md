# Decisions

Mini-ADRs for the quality gate. Context and rule numbers: [AGENTS.md](AGENTS.md), [plans/quality-gate-classification.md](plans/quality-gate-classification.md).

## ADR-1 · Deterministic checks in Python AST, not semgrep/gitleaks/diff-cover

**Decision.** The PII flow (P1–P3), outbound signals (A5), retention (A3/A4), input validation (A7) and secret scanning (A1) are small Python modules over `ast` and regexes. Changed-line coverage (A10) is computed from coverage.py's XML instead of diff-cover. ruff and vulture stay as external linters.

**Why.** One code path for CI and the husky hooks on Linux and Windows (semgrep has no native Windows support, gitleaks is an extra binary). Semgrep OSS taint mode is intra-procedural anyway; the AST version adds one level of cross-function summaries ("this helper returns personal data"), which is what catches `feature/support-context`. Every check is unit-tested with a violation and a compliant fixture.

**Trade-off.** We maintain the secret patterns and the sink lists ourselves. Deeper data flow (renamed fields across files, derived values) is deliberately left to the AI pipeline.

## ADR-2 · The gate runs from the base branch; the AI job never executes PR code

**Decision.** Each job checks out the PR merge result as data and the base branch as the gate (`GATE_HOME`). Prompts, rule map, lint config and allowlists come from the base. The deterministic job runs the PR's tests but has no secrets; the AI job holds `GEMINI_API_KEY` but only reads files.

**Why.** A PR must not be able to relax the rules it is judged by, and untrusted code must not run next to the API key. PR text is passed to Gemini as untrusted data and the system prompt forbids following instructions in it.

**Limits.** On `pull_request` events GitHub runs the workflow file from the PR itself, so a PR could edit `quality-gate.yml`. Mitigations: the required checks are commit statuses that only the real gate posts, `workflow_policy` (R15) flags changes to the gate workflow, and the next step is a CODEOWNERS rule on `.github/` and `gate/`. The PR that introduces the gate necessarily runs its own copy (bootstrap, logged as a warning).

## ADR-3 · Blocking through two commit statuses, with a logged production override

**Decision.** The `report` job is the single policy point (`gate/report/actions.py`). It sets `quality-gate/critical` and `quality-gate/high`; branch protection on `develop` and `main` requires both. Critical also fails the job with annotations; High posts a request-changes review. `/gate-override <reason>` by a repo `admin`/`maintain` (or a member of `GATE_OVERRIDE_TEAM`) flips both statuses for that commit and records who, when, why and which findings.

**Why.** Statuses can be overridden without re-running jobs and without admin bypass of branch protection, and the override is visible on the PR. A crashed check or a failed Gemini call is a blocking *gate error*, never a silent pass.

**Rollout.** `GATE_MODE=shadow` (comment only) is the default until the golden-set evaluation validates the gate (AGENTS#14); then the repo variable is switched to `enforce`. **Severity refinements** after reviewing the live PRs (approved 2026-10-07): copies of personal data into stored collections are Critical; "no tests touched" absorbs the changed-line coverage finding; script and AI findings on neighbouring lines of one statement are merged. The docs rule (AGENTS#20) stays High although it fires on most PRs: undocumented behavior changes are what it exists to stop.

Branch protection on `develop` and `main` (applied 2026-10-07, after making the repo public: GitHub's free plan has no protection for private repos) also requires 1 approving review; admins can bypass, which GitHub records.

## ADR-4 · One Gemini call per PR, stable settings, strict output

**Decision.** A single structured-output call covers all AI checks (B1–B12), with temperature 0, `GEMINI_THINKING_LEVEL=LOW`, a JSON response schema and the model fallback chain from the reporting spike (503 → retry same model, 429 → next model, billing-aware error messages). Findings that fail validation (unknown rule or severity, file not in the diff, line outside the changed hunk ±3) are dropped and counted, never posted. Deterministic findings and signals go into the prompt so the model does not repeat them.

**Why.** Cost and latency scale with calls; one call with the whole diff gives the model cross-file context. LOW thinking matched higher levels on mapping tasks in the spike at a fraction of the cost. Validation keeps hallucinated locations out of PR comments.

**Stability:** temperature 0 alone was not enough on 3.8 Flash (a High finding came and went between identical runs); a fixed sampling `seed` makes reviews repeatable (R14-B).

**Cost controls** (plan section 9, summary for leadership in [docs/PIPELINES.md](docs/PIPELINES.md#cost-optimization)): results cached by a hash of the full request (unchanged re-runs cost $0); output capped at 2048 tokens (configurable, truncation fails loudly); system prompt byte-identical and placed first so Gemini's prompt cache bills it at 10%; system prompt limited to the rules the AI judges (−21%).

**Large PRs:** big files go as changed hunks, generated files are never sent, and files are packed into requests of ≤ 30k input tokens (one output cap each). Cross-file context between batches is lost, which is acceptable because files stay in path order (a module and its tests usually share a request) and the deterministic summaries already follow helpers across files.

**Trade-off.** The fallback chain can serve a different model than configured; the run summary names the model that answered. The output cap is a guess until real reviews are measured: too low fails reviews (loudly), too high only costs money.

## ADR-5 · Evaluation scope and matching

**Decision.** The eval scores AGENTS#1–9 only. Process rules (#16 README, #18 records, #20 docs) fire on every pre-gate branch by construction and would inflate precision. A finding matches a ground-truth item by rule, file and line ±3; debatable findings are listed as `acceptable` (neither rewarded nor penalized); severity is reported separately as *severity agreement*.

**Why.** Precision/recall should measure judgment on the team standards, not bookkeeping. Separating severity from matching shows when the gate found the right problem but under- or over-rated it (e.g. `feature/analytics-archive`, see EVAL.md).

## ADR-6 · Left out, in priority order

1. **CODEOWNERS for `.github/` and `gate/`**: closes the workflow-edit gap in ADR-2. Five minutes, needs the team's GitHub handles.
2. **Fork PRs** (now relevant: the repo is public since 2026-10-07): fork PRs get no secrets and a read-only `GITHUB_TOKEN`, so the AI job fails closed (gate error) and the report can't comment. Needs a `pull_request_target` reporter that never checks out PR code, and a decision on whether fork PRs get the AI review.
3. **Prompt-injection tests** in the golden set (PR text that tries to suppress findings).
4. **SARIF upload** so findings also appear in GitHub code scanning.
5. **A larger golden set**: 8 PRs give wide confidence intervals; every real FP/FN from production should become a fixture.
