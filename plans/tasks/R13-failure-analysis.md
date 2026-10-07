# R13 — Failure analysis of every FP and FN

**Rule:** AGENTS#13 · **Pipeline:** gate infrastructure · **Depends on:** R12

## Scope
- `run_eval.py` lists every false positive and false negative with:
  - PR;
  - rule;
  - severity;
  - source pipeline;
  - file and line;
  - the finding or expected-finding text.
- `EVAL.md` gets a "Failure analysis" section with one entry per FP/FN. The harness fills in the facts. A person (or agent) writes **why it happened** and **what we change** (prompt, semgrep rule, threshold).
- The harness fails if any FP/FN entry is missing its analysis, so the eval can't be marked done with unexplained errors.

## Test
`tests/gate/deterministic/test_r13_failure_analysis.py::test_r13_failure_analysis`
- **Violation input:** the synthetic eval from R12 (1 FP and 1 FN), with an `EVAL.md` whose analysis is missing for the FN.
- **Compliant input:** the same eval with both analyses filled in.
- **Expect:**
  - the generated list contains exactly the FP and the FN, with correct fields;
  - violation: the completeness check fails and names the FN;
  - compliant: the check passes.
