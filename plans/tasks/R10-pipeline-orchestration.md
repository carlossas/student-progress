# R10 — Deterministic first, findings feed the AI

**Rule:** AGENTS#10 · **Pipeline:** gate infrastructure · **Depends on:** R09-A, R11-A, R11-B

## Scope
- `.github/workflows/quality-gate.yml`:
  - the `deterministic` job uploads `findings.json` and `signals.json` as artifacts;
  - the `ai` job has `needs: deterministic` and `if: always()`, so it runs fully even when A fails (plan section 1);
  - a final `report` job merges both outputs through R09-A.
- `gate/ai/prompt_builder.py`: puts the A findings and the P4/A5 signals into the prompt, telling the model "already reported, do not repeat; use signals as hints".
- `gate/report/merge.py`: de-duplicates findings that share the same `rule`, `file` and `line`. The deterministic finding wins.

## Test
`tests/gate/deterministic/test_r10_orchestration.py::test_r10_orchestration`
- **Violation input:** an A finding (`AGENTS#1`, `app/main.py:58`), a P4 signal, and a mocked B finding at the same location.
- **Compliant input:** the parsed workflow YAML.
- **Expect:**
  - the built prompt contains the A finding and the signal;
  - the merged output has a single finding at that location, with `source: deterministic:*`;
  - the `ai` job declares `needs: deterministic` and `if: always()`.
