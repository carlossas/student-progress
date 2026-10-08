# AI usage

## Tools

| Tool | For |
|---|---|
| Claude Code (Opus 5.5) | Planning, gate code, tests, workflows, doc drafts. Also a second review of the repo against the challenge. |
| Gemini 3.8 Flash | The reviewer inside the gate |
| My earlier reporting spike | Base for the Gemini client (fallbacks, 429/503, pricing), ported from TS |

I wrote the rules, the ground truth and the severity calls. Agents wrote most of the code against one test per rule. I edited the docs from Claude drafts.

## Key prompts

1. "Document this repo's architecture and its real endpoints and business rules." → `docs/`
2. "With the challenge and TEAM-STANDARDS, write short golden rules for this repo." → `AGENTS.md`
3. "Split these rules into a script pipeline and a Gemini pipeline. Critical fails with path and code, High blocks, Medium/Low comment." → the classification plan
4. "One task per rule, one test per rule per pipeline." → `plans/tasks/`, `tests/gate/`
5. "Review the repo against the challenge, think business, not only tech." → found the false block and the gaps below

## What I corrected or threw away

- **PII was generic.** The first plan didn't classify `is_minor`. I made it use the real fields and treat `is_minor` as a minors' marker.
- **AI Criticals as non-blocking.** Claude proposed that. I rejected it: Criticals block from both pipelines, with a tested gate and a logged override.
- **Docs rule at High.** I first approved it. The live run showed it blocking the clean PR, so I moved it to Medium.
- **Ground truth too easy.** My first version parked the two "minors' data leaves the service" cases as acceptable. I made them expected; recall dropped from 1.00 to 0.88.
- **Bugs found only against the real APIs:** a key check closed its client before sending, temperature 0 wasn't deterministic (fixed with a seed), the token estimate was 17% low, one AI test was too strict.
- **I trusted a cached eval.** 8/8 came from cached AI results. The first fresh run in CI said 7/8: one false block, from a severity rule for tests the model was reading two ways. I fixed the rule, and the eval now runs fresh and checks that the verdict holds when the prompt changes.
- **The formatter rewrote a test fixture.** The tests caught it, and fixtures are now excluded from lint.
