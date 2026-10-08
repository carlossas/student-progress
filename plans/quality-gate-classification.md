# Plan — Quality gate: rule classification

**Status:** implemented (see section 8 for what changed while building) · **Source of rules:** [AGENTS.md](../AGENTS.md) (rule numbers below refer to it)

Splits every golden rule into two GitHub Actions pipelines plus a local hook:

- **Pipeline A — Deterministic** (scripts, linters, policies): fast, free, reproducible.
- **Pipeline B — AI review** (Gemini): judgment calls a script can't make. Receives the PR diff, `AGENTS.md`, and Pipeline A's findings.
- **Local pre-commit (husky)**: the fast subset of Pipeline A, so developers fix issues before spending CI time or Gemini credits.

Some rules run in both pipelines: the script catches exact patterns, the LLM catches renamed or indirect variants.

## 1. When each pipeline runs

| Trigger | Deterministic (A) | AI (B) |
|---------|:-:|:-:|
| `git commit` (husky pre-commit, staged files) | Fast subset (section 6) | — |
| `git push` (husky pre-push) | Tests + coverage | — |
| PR to any branch | ✅ | — |
| PR to `develop` or `main` | ✅ | ✅ always runs fully, even if A already failed |

Both `develop` and `main` are protected: the gate's checks are required to merge. Everything goes through it, refactors included (rule 15); if a change needs different handling, the pipeline is updated in the same PR.

## 2. Severity → pipeline action

| Severity | Maps to | Result | Log | PR comment | Merge |
|----------|---------|--------|-----|------------|-------|
| **Critical** | S1 | ❌ Job fails with error | Job log + run summary | Inline on file/line with remediation and suggested code (when the tool can provide it) | **Blocked** |
| **High** | S2 | Job succeeds, sets required status `quality-gate/<base>/high` to failure | Run summary | **Request changes** review + inline comments | **Blocked** |
| **Medium** | S3 | ✅ | Run summary | Inline comment | Allowed |
| **Low** | S3 | ✅ | Run summary | One grouped summary comment | Allowed |

Critical findings block **from both pipelines** (rule 14). To make that safe:

- **Validate before enforcing.** Run the gate in shadow mode (comments only) over the 8 golden PRs until results match the ground truth in `EVAL.md`, then make the checks required on `develop`/`main`.
- **Keep the AI deterministic.** Gemini runs with temperature 0, a **low thinking level**, and a strict JSON response schema. Findings that fail schema validation are dropped and logged, never posted.
- **Override.** A member of the production approvers team (e.g. `@org/production-approvers`) comments `/gate-override <reason>`. The workflow verifies team membership through the GitHub API, marks the blocking checks as overridden, and records who, when and why in the run summary and as a PR comment. Nobody else can bypass.

Every finding uses the same shape (rule 11):

```json
{
  "rule": "AGENTS#1",
  "severity": "critical|high|medium|low",
  "source": "deterministic:<tool>|ai:gemini",
  "file": "app/main.py",
  "line": 58,
  "message": "Student email passed to logger.info without redact()",
  "suggestion": "logger.info(\"...\", redact({...}))"
}
```

Scripts that only know the file (e.g. "docs not updated") leave `line` empty and post a file-level comment.

## 3. Personal data policy checks (rules 1–4)

Field classification is defined in the **Personal data fields** table in [AGENTS.md](../AGENTS.md). The gate reads the field list from code (`app.privacy.PII_FIELDS` + `is_minor`) so there is one source of truth.

> **Prerequisite (separate PR):** add `is_minor` to `app.privacy.PII_FIELDS` so `redact()` masks it too.

### 3.1 Deterministic (Pipeline A)

| ID | Check | Tool | Severity |
|----|-------|------|----------|
| P1 | **Registry sync.** Every dataclass field in `app/models.py` whose name looks personal (`name`, `mail`, `birth`, `dob`, `age`, `phone`, `address`, `minor`, `document`) must be in `PII_FIELDS`. | Python script | Critical |
| P2 | **Global usage search on changed lines.** Find every use of `full_name`, `email`, `birthdate`, `is_minor` (attribute, dict key, kwarg) and classify it by where the value ends up (the sink). Values passed through `redact()` are considered safe. | `semgrep` taint rules | by sink ↓ |
| | → logging, `print`, exception/`HTTPException` messages | | Critical |
| | → returned from a route handler or response model in plain text | | Critical |
| | → outbound: HTTP clients, SMTP, analytics/support SDKs, queues, file export | | Critical |
| | → persisted or copied (new collection, file, cache) | | Critical (raised from High on 2026-10-07; see section 8) |
| | → internal logic only | | not posted; forwarded to B |
| P3 | **Whole-object exposure.** `Student` objects reaching any sink above through `__dict__`, `asdict()`, `vars()`, `str()`, `repr()` or f-strings. Dataclass `repr` prints every field. | `semgrep` | Critical |
| P4 | **Alias signal.** New identifiers resembling PII (`name`, `mail`, `dob`, `age`, `minor`, `kid`, `child`, `junior`) on changed lines. Not posted; sent to B as hints. | regex script | signal only |

Semgrep taint tracking only follows data inside one function, which is why Pipeline B repeats this check with more flexibility.

### 3.2 AI (Pipeline B)

| ID | What the LLM judges | Severity |
|----|---------------------|----------|
| B1 | **Flexible PII tracking.** Fields copied into renamed locals (`n = s.full_name`, `contact`, `mail_addr`), passed across helpers, unpacked from dicts or built in comprehensions, then reaching a log, response, error or outbound call. | Critical |
| B2 | **Derived personal data.** Age computed from `birthdate`, email domain, initials, unsalted hashes of email: still personal data. | Critical (minors) / High |
| B3 | **Leaking minor status.** `is_minor` exposed indirectly: `junior` flags, separate endpoints or lists that reveal who is a child, filtering visible from outside. | Critical |
| B4 | **Minors' data leaving the service** (analytics, support tools, third parties, email). Is minimization applied and a legal basis documented in the PR description? | Critical |
| B5 | **Secondary copies** of personal data without purpose or retention category. | Critical (minors) / High |
| B6 | **Data minimization.** A feature attaches name/email/birthdate when `student_id` would do. | Critical (minors) / High |

## 4. Classification matrix

| # | Rule | A · Deterministic | B · AI | Severity |
|---|------|:-:|:-:|----------|
| 1 | No personal data in plain text | ✅ P1–P3 | ✅ B1–B3 | Critical |
| 2 | Minors' data stays in the service | ✅ P2 outbound, A5 | ✅ B4 | Critical |
| 3 | Retention declared, minors ≤ 90 days | ✅ A3, A4 | ✅ B5 | Critical |
| 4 | Data minimization | — | ✅ B6 | Critical (minors) / High |
| 5 | Validate input, explicit error handling | ✅ A6, A7 | ✅ B7 | High |
| 6 | Tests that can fail | ✅ A8–A10 | ✅ B8 | High |
| 7 | No dead code / TODO with ticket | ✅ A11–A13 | — | Medium / Low |
| 8 | Secrets only in env vars | ✅ A1 | — | Critical |
| 9, 11 | Severity decides merge / actionable findings | — | — | Gate config (section 2) |
| 10 | Deterministic first | — | — | A also runs locally and its findings feed B |
| 12, 13 | Measure the reviewer, study its mistakes | — | — | Eval harness → `EVAL.md` |
| 14 | Critical always blocks, tested gate, logged override | — | — | Section 2 |
| 15 | Everything through the gate | — | — | No skip labels; required checks |
| 16 | README runnable in < 15 min | ✅ A15 | — | Medium |
| 17 | Pre-check before pushing | — | — | Husky hooks (section 6) |
| 18 | Record decisions & AI usage | ✅ A16 | — | Low |
| 19 | Respect the timebox | — | — | Process, not checkable |
| 20 | Docs updated in same change | ✅ A14 | ✅ B9 | Medium (missing or inaccurate; process rule, never blocks: DECISIONS ADR-3) |
| 21 | Each rule in one place | — | ✅ B10 | Low |

## 5. Remaining checks

### 5.1 Pipeline A — Deterministic

| ID | Rule | Check | Tool | Severity |
|----|------|-------|------|----------|
| A1 | 8 | Secrets in diff and history (API keys, tokens, `.env` files) | `gitleaks` | Critical |
| A3 | 3 | Every `RETENTION_DAYS` key containing `minor` is ≤ 90 | Python script | Critical |
| A4 | 3 | New collection, file or DB write in `app/` without a `RETENTION_DAYS` change in the PR | Python script on diff | High |
| A5 | 2 | New outbound channels (`httpx`, `requests`, `smtplib`, SDK imports, logging handlers, file exports) | `semgrep` | Signal → B |
| A6 | 5 | Bare/broad `except`, `except: pass` | `ruff` (`E722`, `BLE001`, `S110`) | High |
| A7 | 5 | Route handler taking a raw `dict` instead of a Pydantic model | `semgrep` | High |
| A8 | 6 | Test suite passes | `pytest` | High |
| A9 | 6 | `app/` changed but `tests/` not changed (refactors included) | Python script on diff | High |
| A10 | 6 | **≥ 85% coverage of changed lines** | `pytest-cov` + `diff-cover` | High |
| A11 | 7 | Unused imports/variables, unreachable code | `ruff` (`F401`, `F841`), `vulture` | Medium |
| A12 | 7 | `TODO`/`FIXME` without ticket ref | regex script | Medium |
| A13 | 7 | Lint / format | `ruff check`, `ruff format --check` | Low |
| A14 | 20 | `app/` changed but `docs/ARCHITECTURE.md` and `docs/API-AND-BUSINESS-RULES.md` not changed (refactors included) | Python script on diff | Medium |
| A15 | 16 | Fresh-runner smoke test following the README (`pip install`, `pytest`, `uvicorn`, `GET /health`) | Actions job | Medium |
| A16 | 18 | `DECISIONS.md` and `AI-USAGE.md` exist | script | Low |

### 5.2 Pipeline B — AI (Gemini)

| ID | Rule | What the LLM judges | Severity |
|----|------|---------------------|----------|
| B7 | 5 | Validation that matters for the business: unknown `lesson_id`, score out of range, inputs that cause 500s | High |
| B8 | 6 | **Do the tests make sense?** Trivial asserts, fully mocked logic, asserting on the implementation instead of the behavior, missing edge cases, tests written only to hit 85%. Coverage without meaningful asserts is reported. | High |
| B11 | — | Logic bugs that produce incorrect data (wrong percentage, double counting) | High |
| B9 | 20 | Docs changed but don't reflect the diff (new endpoint/rule missing) | Medium |
| B10 | 21 | Rules from `AGENTS.md` duplicated into other files | Low |
| B12 | — | Style, naming, refactoring ideas | Low |

**Prompt inputs:** PR title + description, unified diff, full content of changed files, `AGENTS.md`, `app/models.py`, Pipeline A findings + P4/A5 signals.
**Config:** `GEMINI_API_KEY` as a GitHub secret (rule 8); `GEMINI_MODEL`, `GEMINI_THINKING_LEVEL`, `GEMINI_MAX_OUTPUT_TOKENS` as repo variables; temperature 0; low thinking level; JSON response schema. Cost controls: section 9.

## 6. Local hooks (husky)

| Hook | Runs | Target |
|------|------|--------|
| `pre-commit` | secret scan, `ruff check`, `ruff format --check`, PII flow + validation checks (P1–P3, A6, A7), A3/A4 retention, A12 TODO | Staged files, < 10 s |
| `pre-push` | `pytest` + changed-line coverage (85%) against `origin/develop` | Whole repo |

Husky needs Node: the repo gets a minimal `package.json` (dev dependency only) and the README documents `npm install` once after cloning.

## 7. Resolved questions

1. **Husky** kept, as requested (`package.json`, `.husky/`, `gate/hooks/run.sh`).
2. **Override authorization**: repo `admin`/`maintain` permission by default; set `GATE_OVERRIDE_TEAM=org/team` (+ `GATE_ORG_TOKEN`) to require a team instead.
3. **`is_minor` in `PII_FIELDS`**: done (R01-P).

## 8. Implementation notes (as built)

Deviations from the sections above, with the reason in [DECISIONS.md](../DECISIONS.md):

| Plan | As built | Why |
|------|----------|-----|
| semgrep taint rules (P2, P3, A5, A7) | `gate/deterministic/pii_flow.py`, `validation.py` (Python `ast`), with one level of cross-function summaries | Same code in CI and in the hooks on Windows; catches PII returned by helpers (ADR-1) |
| gitleaks (A1) | `gate/deterministic/secrets_scan.py` (patterns + `.env`/key files + every commit in the range) | No extra binary; same code in the pre-commit hook |
| diff-cover (A10) | coverage.py XML parsed in `gate/report/adapters.py` | One less dependency; exact changed lines from the gate's own diff |
| Status `quality-gate/high` only | Two required statuses per base branch: `quality-gate/<base>/critical` and `quality-gate/<base>/high` | The override lifts blocks without re-running jobs (ADR-3); per-base names because one commit can head PRs into several branches (live PRs #4/#10) |
| ruff `E501` as Low | Ignored in `gate/config/ruff.toml` | `ruff format` owns line length; long message strings can't be split |
| AI tests `tests/gate/ai/test_rXX_*.py` | `tests/gate/ai/test_rXX_*_ai.py` | Avoids module-name clashes with the deterministic tests |
| Logic bugs / style (B11, B12) | Reported under `AGENTS#9` (S2/S3 definitions) | They have no rule of their own |
| P2 copy of personal data: High | **Critical** | Reviewing live PR #17: a copy of minors' data without retention is S1 (approved 2026-10-07) |
| A9 and A10 both reported | A10 dropped when A9 fires | One root cause, one finding (live PR #15) |
| Merge on identical (rule, file, line) | AI finding within ±3 lines of a script finding with the same rule is merged | Live PR #14 got two comments for one log call (PR #19) |
| — | **Added after the live review (PR #22):** A17 prompt-injection check (`gate/deterministic/prompt_injection.py`, AGENTS#15); High code-quality findings (#5, #7, #9) on lines the PR only moved are demoted to Medium (`gate/report/baseline.py`; privacy, secrets and tests never are); secrets are masked in files and PR text before any request reaches Gemini (`secrets_scan.mask_secrets`) | Second layer against PR text steering the reviewer; don't make authors pay for debt they only moved; no secret ever leaves through the AI call |

## 9. AI cost controls

Output (and thinking) tokens cost 5× input, so the levers are: fewer calls, less output, cheaper input. Executive view and model outlook: [docs/PIPELINES.md](../docs/PIPELINES.md#cost-optimization).

| ID | Control | Implementation | Tested by |
|----|---------|----------------|-----------|
| C1 | **Result cache** keyed by SHA-256 of the full request (diff and changed files, PR title/description, deterministic findings, system prompt, model chain, thinking level, output cap). Hit → no API call, $0. Malformed answers are never cached. | `gate/ai/review.py`; CI restores/saves it with `actions/cache` (`ai --key-only` computes the key without the API key); local cache in `.gate-cache/ai` | [R14-C](tasks/R14-C-ai-cost-controls.md) |
| C2 | **Output cap and terse format**: `GEMINI_MAX_OUTPUT_TOKENS` (default 2048, was 8192); messages ≤ 2 sentences, snippets ≤ 6 lines. A capped (truncated) review is a blocking gate error, never a partial pass. Tune the cap after the first measured runs. | `gate/ai/config.py`, `client.py` (`OutputTruncated`), `prompts/system.md` | R14-C |
| C3 | **Prompt caching**: system prompt byte-identical for every PR; repository context placed before the PR content to extend the cacheable prefix. Cached tokens priced at 10% of input in the cost line. | `gate/ai/prompt_builder.py`, `pricing.py` (measured: 0 cached tokens; prompt likely under Google's implicit-cache minimum) | R14-C |
| C4 | **Smaller system prompt**: only the AGENTS.md rules the AI judges (1–6, 20, 21) plus the field table; script-only rules omitted. ≈ 3.1k → ≈ 2.4k tokens (−21%). | `prompt_builder.agents_excerpt` | R14-C |

| C5 | **Large PRs**: files > 300 lines sent as changed hunks ± 30 lines (± 5 when a single file exceeds the budget); generated files (`eval/results/`, lockfiles, coverage/junit XML) never sent; files packed in order into requests of ≤ `GEMINI_MAX_INPUT_TOKENS` (default 30k, estimated locally at 3.0 chars/token, calibrated on a real run); one call per request, findings merged and deduplicated, each request cached separately. A typical PR stays one byte-identical request. | `prompt_builder.plan_batches`, `numbered`, `reviewable_files`; `review.py` | R14-C |

| C6 | **Per-run cost logging**: the `report` job adds the AI spend (all requests, $0 when cached) to the CI runner minutes (each job rounded up × `GATE_ACTIONS_USD_PER_MINUTE`, default $0.006) and logs it as a notice, in the summary/PR comment and in `cost.json`. `check-all` prints the local AI spend. | `gate/report/cost.py`, `gate/__main__.py` (`report`), `gate/local.py` | `test_pipeline_cost.py` |

Not adopted (yet): Batch/Flex tiers (too slow for blocking reviews; fine for eval), model routing to Flash-Lite (needs the golden-set evaluation first).

## 10. Developer tooling (AGENTS#17)

One command runs everything a developer needs before opening a PR: `python -m gate all` (wrappers `scripts/check-all.sh`, `scripts/check-all.ps1`). Guide: [PIPELINE_README.md](../PIPELINE_README.md).

| Step | What | Blocks on |
|------|------|-----------|
| 1 | Pre-commit fast checks on staged files | Critical/High |
| 2 | Lint: repo-wide `ruff check` (same as CI) + gate format policy on changed files (`python -m gate lint [--fix]`) | Any lint error |
| 3 | Full test suite + 85% changed-line coverage | Failing test, coverage |
| 4 | Deterministic pipeline on commits + uncommitted + untracked changes vs the PR's base | Critical/High |
| 5 | AI pipeline, only if `GEMINI_API_KEY` is set and valid (checked with a free metadata request); otherwise skipped with the reason | Critical/High |

Exit code 0 = READY, 1 = BLOCKED. Task: [R17-B](tasks/R17-B-check-all.md).
