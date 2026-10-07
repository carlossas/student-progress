# R12 — Eval harness: ground truth, precision and recall

**Rule:** AGENTS#12 · **Pipeline:** gate infrastructure · **Depends on:** R10

## Scope
- `eval/ground_truth.yaml`: the expected findings for each of the 8 golden PRs (`pr`, `rule`, `severity`, `file`, `line`), plus PRs that are expected to be clean.
- `gate/eval/run_eval.py`:
  1. checks out each PR branch and runs the full gate in shadow mode;
  2. matches findings to the ground truth by `pr` + `rule` + `file` + `line ± 3`;
  3. computes precision and recall per pipeline (A, B, A+B) and per severity;
  4. writes the tables into `EVAL.md`.
- `.github/workflows/eval.yml`: runs manually and on any PR that changes `gate/**`.

## Test
`tests/gate/deterministic/test_r12_eval_metrics.py::test_r12_eval_metrics`
- **Violation input:** a synthetic ground truth with 4 expected findings, and gate output with 3 true positives, 1 false positive (a wrong line beyond ±3) and 1 miss.
- **Compliant input:** gate output identical to the ground truth.
- **Expect:**
  - violation: precision = 0.75 and recall = 0.75, broken down correctly per severity;
  - compliant: precision = recall = 1.0.
