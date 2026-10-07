# R08-A — Secrets only in environment variables (deterministic)

**Rule:** AGENTS#8 · **Pipeline:** A · **Check:** A1 · **Severity:** Critical · **Depends on:** R11-A

## Scope
- `gitleaks` with `.gitleaks.toml` (default rules plus Google API key and `.env` file rules).
- Scans the PR diff and the full history of the PR commits.
- The remediation suggestion is "remove, rotate the key, read it from an environment variable".
- Fixture files are allowlisted individually in `.gitleaks.toml` so the repo-wide scan stays clean.

## Test
`tests/gate/deterministic/test_r08_secrets.py::test_r08_secrets`
- **Violation fixture:** `config.py` with `GEMINI_API_KEY = "AIzaFAKE..."` (a fake key that matches the pattern), plus a committed `.env` file.
- **Compliant fixture:** `GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]`.
- **Expect:**
  - violation: Critical `AGENTS#8` findings on the key line and on `.env`;
  - compliant: zero `AGENTS#8` findings.
- The test runs gitleaks with `--no-git` directly on the fixture directory, so the allowlist doesn't apply.
