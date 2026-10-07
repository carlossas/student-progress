# R21-B — Each rule in one place only (AI)

**Rule:** AGENTS#21 · **Pipeline:** B · **Check:** B10 · **Severity:** Low · **Depends on:** R11-B, R14-B

## Scope
Prompt section `gate/ai/prompts/r21_single_source.md`. It checks whether a PR copies or rephrases rules from `AGENTS.md` into other files (docs, READMEs, code comments) instead of linking to them.

## Test
`tests/gate/ai/test_r21_single_source_rules.py::test_r21_single_source_rules_ai` (`@pytest.mark.ai`)
- **Violation fixture:** a diff that adds `CONTRIBUTING.md` restating rules 1–3 (personal data, minors, retention) in its own words.
- **Compliant fixture:** a diff that adds `CONTRIBUTING.md` with setup steps and the line "Team rules: see AGENTS.md".
- **Expect:**
  - violation: a Low `AGENTS#21` finding on `CONTRIBUTING.md`;
  - compliant: no `AGENTS#21` finding.
