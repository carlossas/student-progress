# student-progress

Open English LMS service that tracks lesson progress, plus an **AI quality gate** that reviews every PR against the team rules.
**Some students are minors.** Read [AGENTS.md](AGENTS.md) before changing anything.

## Running locally

Requires **Python 3.11+** and git:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-gate.txt
uvicorn app.main:app --reload
pytest
```

On Windows: `py -m venv .venv` and `.venv\Scripts\activate`. CI runs these exact commands on a clean machine (AGENTS#16).

## Endpoints

`GET /health` · `GET /lessons` · `GET /students/{id}/progress` · `POST /students/{id}/progress` (`{"lesson_id": "...", "score": 0-100}`). Data lives in memory. Details: [docs/API-AND-BUSINESS-RULES.md](docs/API-AND-BUSINESS-RULES.md).

## Quality gate in 2 minutes

```bash
python -m gate all                        # everything before a PR: hooks, lint, tests, both pipelines
python -m gate check --base main          # scripts only, free
python -m gate check --base main --ai     # + Gemini (needs GEMINI_API_KEY)
python -m gate eval                       # score the gate on the 8 golden PRs
npm install                               # optional: pre-commit / pre-push hooks
```

Exit code 1 = the PR would be blocked. Critical/High block, Medium/Low comment. It runs in `enforce` on `develop`; `main` doesn't have it yet.

| Doc | What |
|---|---|
| [PIPELINE_README.md](PIPELINE_README.md) | How to run everything, locally and on GitHub |
| [EVAL.md](EVAL.md) | Ground truth, metrics, failure analysis, trust policy |
| [DECISIONS.md](DECISIONS.md) | Trade-offs and what was left out |
| [AI-USAGE.md](AI-USAGE.md) | How AI was used to build this |
| [docs/PIPELINES.md](docs/PIPELINES.md) | What each pipeline checks, cost |
