# student-progress

Open English LMS service that tracks students' lesson progress, plus the **AI quality gate** that reviews every pull request against the team's golden rules.
**Some students are minors** — read [AGENTS.md](AGENTS.md) before making any changes.

## Running locally

Requires **Python 3.11+** and git (a virtual environment is recommended):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-gate.txt
uvicorn app.main:app --reload
pytest
```

On Windows use `py -m venv .venv` and `.venv\Scripts\activate`. The quality gate CI job runs these exact commands on a clean machine (AGENTS#16).

## Endpoints

- `GET /health`
- `GET /lessons`
- `GET /students/{id}/progress`
- `POST /students/{id}/progress` — body: `{"lesson_id": "...", "score": 0-100}`

Data is held in memory (see `app/store.py`). Details: [docs/API-AND-BUSINESS-RULES.md](docs/API-AND-BUSINESS-RULES.md).

## Quality gate

Two pipelines review every PR against [AGENTS.md](AGENTS.md):

| Pipeline | What | Runs on |
|----------|------|---------|
| **A — Deterministic** | Secrets, personal-data flow (logs, responses, outbound, copies), retention, input validation, lint, TODOs, tests + 85% changed-line coverage, docs/tests touched, README smoke test | Every PR, and locally in git hooks |
| **B — AI (Gemini)** | Renamed/derived personal data, minors' data leaving the service, minimization, business validation, test quality, logic bugs, doc accuracy | PRs into `develop` and `main` |

| Severity | Effect on the PR |
|----------|------------------|
| Critical | Check fails (`quality-gate/critical`), inline comment with the fix, merge blocked |
| High | Request-changes review (`quality-gate/high`), merge blocked |
| Medium / Low | Comment only, merge allowed |

Pipeline details, AI cost and model outlook: [docs/PIPELINES.md](docs/PIPELINES.md). How it was designed and measured: [plans/quality-gate-classification.md](plans/quality-gate-classification.md), [EVAL.md](EVAL.md), [DECISIONS.md](DECISIONS.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#quality-gate).

**Developer guide (local + GitHub, one command to check everything): [PIPELINE_README.md](PIPELINE_README.md).**

### Run it locally (2 minutes)

After the setup above, from the repo root, on a feature branch:

```bash
python -m gate check --base main            # Pipeline A on your branch vs main
python -m gate check --base main --ai       # + Gemini review (needs GEMINI_API_KEY; costs credits)
```

Same output as CI: each finding with its severity, rule, location and suggested fix. Exit code 1 means the PR would be blocked.

### Git hooks (husky)

```bash
npm install
```

Installs [husky](https://typicode.github.io/husky/) and activates two hooks:

- **pre-commit**: fast deterministic checks on staged files (secrets, personal data, retention, validation, lint, TODOs). Blocks on Critical/High.
- **pre-push**: tests + changed-line coverage against `origin/develop` (or `origin/main`).

The hooks use `.venv` when present (override with `GATE_PYTHON`). Self-review with [AGENTS.md](AGENTS.md) before opening a PR (AGENTS#17).

### CI setup (once per repository)

1. **Secret** `GEMINI_API_KEY` (Settings → Secrets and variables → Actions). Never commit it (AGENTS#8).
2. **Variables** (optional): `GEMINI_MODEL` (default `gemini-3.8-flash`), `GEMINI_THINKING_LEVEL` (default `LOW`), `GEMINI_MAX_OUTPUT_TOKENS` (default `2048`), `GATE_MODE` (`shadow` by default; set to `enforce` once [EVAL.md](EVAL.md) validates the gate, AGENTS#14).
3. **Branch protection** on `develop` and `main`, requiring `quality-gate/critical`, `quality-gate/high` and 1 approving review:
   ```bash
   bash gate/setup/branch_protection.sh
   ```
4. **Override** (production approvers only): comment `/gate-override <reason>` on a blocked PR. Allowed for repo `admin`/`maintain` permission, or for members of the team in the `GATE_OVERRIDE_TEAM` variable (`org/team`, with a `GATE_ORG_TOKEN` secret that can read org teams). The override applies to the current commit and is recorded on the PR.

Workflows: [quality-gate.yml](.github/workflows/quality-gate.yml) (the gate), [gate-override.yml](.github/workflows/gate-override.yml), [gate-eval.yml](.github/workflows/gate-eval.yml) (evaluation + AI tests), [ci.yml](.github/workflows/ci.yml).

### Evaluate the gate

```bash
python -m gate eval                 # deterministic pipeline on the 8 golden PRs (free)
python -m gate eval --ai --write    # + Gemini, and update EVAL.md
pytest -m ai                        # AI tests (one per AI rule; need GEMINI_API_KEY)
```

### Layout

```
gate/
  deterministic/   Pipeline A checks (one module per rule family)
  ai/              Pipeline B: Gemini client, prompts/, validation
  report/          finding schema, severity policy, GitHub publishing, override
  eval/            golden-set harness
  hooks/ setup/    husky entry point, branch protection script
  config/          ruff policy, rule map, secret allowlist
eval/              ground truth + cached results
tests/gate/        one test per rule and pipeline (+ fixtures/)
```
