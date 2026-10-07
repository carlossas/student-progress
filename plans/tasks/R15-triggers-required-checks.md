# R15 — Every change goes through the gate

**Rule:** AGENTS#15 · **Pipeline:** gate infrastructure · **Depends on:** R10, R14-A

## Scope
- `quality-gate.yml` triggers:
  - `pull_request` on **all** branches;
  - no `paths-ignore`, and no label- or title-based skip conditions;
  - the `ai` job runs only when `github.base_ref` is `develop` or `main` (plan section 1).
- `gate/setup/branch_protection.sh` (`gh api`) protects `develop` and `main`, requiring the checks `quality-gate/deterministic`, `quality-gate/ai` and `quality-gate/high`, and dismissing stale reviews. It is documented in the README.

## Test
`tests/gate/deterministic/test_r15_triggers.py::test_r15_triggers`
This test parses the workflow YAML.
- **Violation input:** a fixture workflow with:
  - `paths-ignore: ["docs/**"]`;
  - `if: !contains(github.event.pull_request.labels.*.name, 'skip-gate')`;
  - an `ai` job without a branch condition.
- **Compliant input:** the real `.github/workflows/quality-gate.yml`.
- **Expect:**
  - violation: the policy checker reports all three problems;
  - compliant: the checker passes, `deterministic` runs on every PR, and `ai` runs only for base `develop` or `main`.
