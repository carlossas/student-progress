# AI usage

> Draft written by Claude Code from the session that built the gate. Review and adjust it: this file is the author's account.

## Tools

| Tool | Used for |
|------|----------|
| **Claude Code** (Claude Opus 5.5, Claude desktop app) | Architecture/API docs, golden rules (AGENTS.md), rule classification plan, task breakdown, and the implementation of the gate, its tests, workflows and docs. |
| **Gemini** (`gemini-3.8-flash`, LOW thinking) | The AI reviewer inside the gate (Pipeline B). |
| **reporting-spike agent** (own earlier work) | Base for the Gemini client: model fallback chain, 429/503 handling, billing hints, token pricing. Ported from TypeScript to Python. |

## Most important prompts

1. *"Create a diagram with the architecture of this repository … with other document detailing the actual requests and business rules."* → `docs/ARCHITECTURE.md`, `docs/API-AND-BUSINESS-RULES.md`.
2. *"Together with [the challenge text] and TEAM-STANDARDS.md, create simple golden rules for this repository."* → later moved to `AGENTS.md` as the single source of rules, plus a rule to keep the two docs updated on every change.
3. *"Convert all these golden rules into 2 separate pipelines … scripts/linters … and an AI pipeline (Gemini) … classify which rules go where; critical returns an error and a comment with path and code, high blocks with a comment, medium/low comment and allow merge."* → `plans/quality-gate-classification.md`.
4. *"Create a tasks/ folder, one task per rule (two if both pipelines), one test per rule per pipeline."* → `plans/tasks/`.
5. *"Start with phase 1 and continue to finish all … use the reporting-spike agent config as a base … the pipeline should be able to run in GitHub."* → the gate itself.

## AI output corrected or discarded

- **Missing personal-data classification (corrected by me).** The first plan treated "PII" generically and did not classify `is_minor`. I asked for the real field names from the code, `is_minor` as a minors' marker, a global search of how new code uses them (logs, plain responses, outbound), and an AI pass for renamed variables. Result: the field table in AGENTS.md, checks P1–P4 and B1–B3, and `is_minor` added to `PII_FIELDS`.
- **AI Criticals as non-blocking (discarded).** The AI proposed that AI-only Critical findings start as non-blocking. I decided Criticals block from both pipelines, with a low thinking level, a tested gate and a production-level override instead.
- **semgrep/gitleaks/diff-cover replaced (AI's own correction).** The plan named semgrep, gitleaks and diff-cover. During implementation they were replaced by Python AST checks and coverage.xml parsing so the same code runs in CI and in the husky hooks on Windows (ADR-1 in DECISIONS.md).
- **Bugs found only by running against the real API.** The free key check closed its client before sending (a valid key looked unreachable); `temperature=0` alone didn't make reviews repeatable (fixed with a sampling seed); the local token estimate was 17% low (recalibrated); one AI test demanded an optional style note (relaxed). All found by testing the AI-written code against Gemini and GitHub, then fixed.
- **Formatter rewrote a test fixture (caught by the tests).** Running `ruff format` over `tests/` reformatted a fixture that must stay unformatted (it tests the formatting check). The R07 test failed, the fixture was restored, and fixtures are now excluded from repo-wide lint/format.
