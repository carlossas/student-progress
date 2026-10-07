# R14-C — AI cost controls

**Rule:** AGENTS#14 (a stable, measured gate) · **Pipeline:** B · **Controls:** C1–C4 (plan section 9) · **Depends on:** R11-B, R14-B

## Scope
- **C1 Result cache:** `review()` keys each review by a SHA-256 of the full request and model settings; `python -m gate ai --key-only` prints the key without an API key; the `ai` job restores/saves `gate-cache/` with `actions/cache`. Only well-formed answers are cached.
- **C2 Output cap:** `GEMINI_MAX_OUTPUT_TOKENS` (default 2048); `MAX_TOKENS` finish reason raises `OutputTruncated` (blocking gate error with a hint to raise the cap). Terse-format instructions in `prompts/system.md`.
- **C3 Prompt caching:** byte-identical system prompt; repository context before PR content; cached tokens priced at 10% of input; the run summary shows cached tokens.
- **C4 Smaller system prompt:** `agents_excerpt()` sends only rules 1–6, 20, 21 and the personal-data field table.

- **C5 Large PRs:** big files as changed hunks, generated files excluded, files batched under `GEMINI_MAX_INPUT_TOKENS` (default 30k); one call per batch, results merged; each batch cached.

- **C6 Per-run cost:** `gate/report/cost.py` computes AI + CI cost of each run (job durations from the GitHub API, rounded up per job); logged by the `report` job and by `check-all`.

## Test
`tests/gate/deterministic/test_ai_cost_controls.py` (offline: fake client, no Gemini calls). Four test functions, one per control:
- **C1** same request twice → 1 API call, second served from cache at $0; a different diff, thinking level or PR description → new call; malformed answer → error and nothing cached.
- **C2** cap defaults to 2048 and follows `GEMINI_MAX_OUTPUT_TOKENS`; a `MAX_TOKENS` response raises `OutputTruncated` naming the variable.
- **C3/C4** excerpt contains exactly rules {1–6, 20, 21} and the field table, is < 75% of AGENTS.md; system prompt identical across PRs; `<repository_context>` precedes `<pull_request>`.
- **Pricing** cached input billed at 10%; savings reported.
- **C5** a 1,000-line file is sent as its changed hunk with gaps marked; `eval/results/` and `package-lock.json` are not sent; 8 files under a 9k budget become several requests, each under budget; one API call per request, duplicate findings merged, a second run fully cached; a small PR stays a single request.

- **C6** `tests/gate/deterministic/test_pipeline_cost.py`: 4 jobs of 95/140/30/12 s bill 7 minutes ($0.042 at $0.006); AI + CI total and rendered line; cached AI = $0; no AI job = AI $0.

Measured (2026-10-07): this repo's 167-file branch → 5 requests, 164.8k input tokens, $0.13, 28 s.

## Follow-up after the first real runs
Read `cost.cached_tokens` and output tokens in the run summaries; lower or raise `GEMINI_MAX_OUTPUT_TOKENS` accordingly (no code change).
