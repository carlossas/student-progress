# student-progress

Open English LMS service that tracks lesson progress, plus an **AI quality gate** that reviews every PR against the team rules.
**Some students are minors.** Read [AGENTS.md](AGENTS.md) before changing anything.

## Get the code

The gate and the deliverables live on **`develop`**. `main` is the untouched seed, so clone `develop`:

```bash
git clone -b develop https://github.com/carlossas/student-progress.git
cd student-progress
```

## Running locally

Requires **Python 3.11+** and git:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-gate.txt
uvicorn app.main:app --reload
pytest
```

- **Windows:** `py -m venv .venv`, then `.venv\Scripts\activate` (PowerShell) or `source .venv/Scripts/activate` (Git Bash).
- `uvicorn` keeps the terminal busy. Open http://127.0.0.1:8000/health, then run `pytest` in a second terminal.

CI runs these exact commands on a clean machine (AGENTS#16). Measured from a fresh clone: about a minute.

## Endpoints

`GET /health` · `GET /lessons` · `GET /students/{id}/progress` · `POST /students/{id}/progress` (`{"lesson_id": "...", "score": 0-100}`). Data lives in memory. Details: [docs/API-AND-BUSINESS-RULES.md](docs/API-AND-BUSINESS-RULES.md).

## Run the quality gate

**0. Gemini key (only for `--ai`), once:** copy the template and put your key in it. `.env` is gitignored and the gate loads it on every run.

```bash
cp .env.example .env          # Windows CMD: copy .env.example .env
```

Then edit `.env`: `GEMINI_API_KEY=your-key` ([get one](https://aistudio.google.com/apikey)). A variable already set in your shell wins over the file. Without a key the AI step is skipped and the scripts decide on their own.

**1. On the 8 golden PRs (the challenge's test set):**

```bash
python -m gate eval                       # scripts only, free: verdict + precision/recall per PR
python -m gate eval --ai                  # + Gemini (needs GEMINI_API_KEY), what EVAL.md reports
```

**2. On one PR, with the full report** (severity, rule, file:line, suggested fix). The PR branches don't contain the gate, so check the PR out next to this repo and point the gate at it:

```bash
git worktree add ../pr-email feature/email-reminders
python -m gate check --repo ../pr-email --base main          # add --ai for Gemini
```

Exit code 1 means the PR would be blocked. Try `feature/lessons-pagination` for one that passes.

**3. On your own branch, before opening a PR:**

```bash
python -m gate all                        # lint, tests + coverage, both pipelines, one verdict
npm install                               # optional: pre-commit / pre-push hooks (needs Node)
```

Critical/High block, Medium/Low only comment. On GitHub it runs in `enforce` on `develop`; `main` doesn't have it yet.

`gate eval` refreshes the cached results in `eval/results/`. Run `git checkout -- eval/results` before switching branches if you don't want to keep them.

| Doc | What |
|---|---|
| [PIPELINE_README.md](PIPELINE_README.md) | How to run everything, locally and on GitHub |
| [EVAL.md](EVAL.md) | Ground truth, metrics, failure analysis, trust policy |
| [DECISIONS.md](DECISIONS.md) | Trade-offs and what was left out |
| [AI-USAGE.md](AI-USAGE.md) | How AI was used to build this |
| [docs/PIPELINES.md](docs/PIPELINES.md) | What each pipeline checks, cost |
