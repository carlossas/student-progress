# Architecture — student-progress

A small FastAPI service that tracks students' lesson progress for the Open English LMS.
All state lives in memory; there is no database, queue or external integration.
The repository also contains the **quality gate** that reviews every PR (see [Quality gate](#quality-gate)).

For endpoint contracts and business rules, see [API-AND-BUSINESS-RULES.md](API-AND-BUSINESS-RULES.md). Team rules live in [AGENTS.md](../AGENTS.md).

## Component diagram

```mermaid
flowchart LR
    client([HTTP client<br/>app / support / tests])

    subgraph service["student-progress (FastAPI process)"]
        direction LR
        main["app/main.py<br/>FastAPI routes<br/>+ _get_student()"]
        models["app/models.py<br/>Student · Lesson · ProgressRecord<br/>(dataclasses)"]
        privacy["app/privacy.py<br/>PII_FIELDS · redact()<br/>RETENTION_DAYS"]
        store[("app/store.py<br/>STUDENTS: dict<br/>LESSONS: list<br/>PROGRESS: list")]
        log[["stdout logger<br/>'student-progress'"]]
    end

    client -- "GET /health<br/>GET /lessons<br/>GET|POST /students/{id}/progress" --> main
    main -- "reads / appends" --> store
    main -- "builds ProgressRecord" --> models
    store -- "seeded with" --> models
    main -- "redact(payload)" --> privacy
    main -- "logger.info" --> log
```

## Module responsibilities

| Module | Responsibility |
|--------|----------------|
| `app/main.py` | FastAPI app, route handlers, 404 lookup helper `_get_student`, logger setup. |
| `app/models.py` | Domain dataclasses. Documents PII classification of `Student` fields. |
| `app/store.py` | In-memory seed data: 4 students (2 minors), 5 lessons (A1–B1), 6 progress records. Module-level mutable globals. |
| `app/privacy.py` | `PII_FIELDS` (`full_name`, `email`, `birthdate`, `is_minor`), `redact()` for log-safe payloads, `RETENTION_DAYS` registry per data category. |
| `tests/test_progress.py`, `tests/test_privacy.py` | Endpoint tests via `fastapi.testclient.TestClient`; `redact()` coverage of every personal field. |
| `gate/`, `tests/gate/`, `eval/` | The quality gate, its tests and its golden-set evaluation (below). |
| `AGENTS.md` / `TEAM-STANDARDS.md` | Team rules for agents and reviewers (`AGENTS.md` is the maintained summary). |
| `open_prs.sh` / `PULL_REQUESTS.md` | Tooling and catalog for the 8 open PRs under review. |

## Domain model

```mermaid
classDiagram
    class Student {
        +str id
        +str full_name  «pii / pii-minor»
        +str email      «pii / pii-minor»
        +str birthdate  «pii-minor sensitive»
        +str country
        +bool is_minor  «pii-minor marker»
    }
    class Lesson {
        +str id
        +str title
        +str level
    }
    class ProgressRecord {
        +str student_id
        +str lesson_id
        +bool completed
        +int score
    }
    Student "1" --> "0..*" ProgressRecord : student_id
    Lesson "1" --> "0..*" ProgressRecord : lesson_id (not enforced)
```

## Request flow — recording progress

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant M as main.record_progress
    participant S as store
    participant P as privacy.redact
    participant L as Logger

    C->>M: POST /students/{id}/progress {lesson_id, score}
    M->>S: STUDENTS.get(id)
    alt student not found
        M-->>C: 404 {"detail": "student not found"}
    else found
        M->>M: ProgressRecord(completed=True, score=int(score or 0))
        M->>S: PROGRESS.append(record)
        M->>P: redact({student_id, lesson_id})
        P-->>M: log-safe dict
        M->>L: "progress recorded {...}"
        M-->>C: 200 {"ok": true}
    end
```

## Request flow — reading progress

```mermaid
sequenceDiagram
    autonumber
    participant C as Client
    participant M as main.get_progress
    participant S as store

    C->>M: GET /students/{id}/progress
    M->>S: STUDENTS.get(id)
    alt student not found
        M-->>C: 404
    else found
        M->>S: filter PROGRESS by student_id
        M->>M: completed = count(records where completed)
        M->>M: total = len(LESSONS)
        M->>M: percentage = round(100*completed/total) or 0
        M-->>C: 200 {student_id, completed, total, percentage}
    end
```

## Runtime & tooling

- Python 3.11+, FastAPI 0.115, served with `uvicorn app.main:app`.
- Tests: `pytest` (`pythonpath = ["."]`, `testpaths = ["tests"]` in `pyproject.toml`).
- Lint: `ruff` (repo config in `pyproject.toml`; the gate applies its own `gate/config/ruff.toml`).
- Git hooks: husky (`package.json`, `.husky/`), calling `gate/hooks/run.sh`.
- Logging: stdlib `logging` at `INFO` to stdout, format `%(name)s %(levelname)s %(message)s`.

## Architectural constraints and caveats

- **Process-local state.** `store` globals are shared across all requests and all tests in a run; restarting the process resets data. Not safe for multiple workers.
- **No persistence layer.** `RETENTION_DAYS` is a declarative registry only — nothing purges data.
- **Single trust boundary.** No authentication/authorization; any caller can read or write any student's progress.
- **PII stays in-process.** `Student` PII is never returned by any endpoint and logs go through `redact()` (see [AGENTS.md](../AGENTS.md)).

## Quality gate

Reviews every pull request against [AGENTS.md](../AGENTS.md) in two pipelines and turns findings into PR actions by severity. Design: [plans/quality-gate-classification.md](../plans/quality-gate-classification.md); trade-offs: [DECISIONS.md](../DECISIONS.md).

```mermaid
flowchart TB
    pr([Pull request]) --> wf

    subgraph wf["GitHub Actions: quality-gate.yml"]
        direction TB
        det["deterministic job<br/>gate/deterministic/*<br/>secrets · PII flow · retention · validation<br/>ruff/vulture · TODO · pytest + coverage<br/>tests/docs touched · records"]
        smoke["smoke job<br/>README 'Running locally' on a clean runner"]
        ai["ai job (PRs into develop/main)<br/>gate/ai: prompt_builder → Gemini → validate"]
        report["report job<br/>merge + dedupe → severity policy (actions.py)<br/>→ statuses, sticky summary, review comments"]
        det -- "findings + signals" --> ai
        det --> report
        smoke --> report
        ai --> report
    end

    report -- "quality-gate/&lt;base&gt;/critical<br/>quality-gate/&lt;base&gt;/high" --> protect{{"branch protection<br/>develop · main"}}
    report -- "inline comments<br/>request changes" --> pr
    override(["/gate-override reason<br/>gate-override.yml"]) -. "production approver" .-> protect

    hooks["husky hooks<br/>pre-commit: fast checks · pre-push: tests"] -. "same Pipeline A code" .-> det
    eval["python -m gate eval<br/>8 golden PRs → EVAL.md"] -. "measures" .-> wf
```

| Module | Responsibility |
|--------|----------------|
| `gate/__main__.py`, `gate/local.py` | CLI: `all` (developer one-shot: pre-commit, lint, tests, both pipelines, one verdict), `lint`, `check`, `precommit`, `prepush`, `deterministic`, `smoke`, `ai`, `report`, `override`, `eval`. Wrappers: `scripts/check-all.sh`, `scripts/check-all.ps1`. |
| `gate/env.py` | Loads the developer's local `.env` (gitignored; template `.env.example`) at CLI and pytest start-up; real environment variables (CI secrets) win. |
| `gate/diff.py` | Changed files and lines from a git range, the index (hooks) or a fixture directory. |
| `gate/deterministic/` | Pipeline A, one module per rule family (incl. `vendor_channel.py`: scaffolding for third-party channels with personal data, and `prompt_injection.py`); `runner.py` turns a crashing check into a blocking gate error. |
| `gate/ai/` | Pipeline B: Gemini client with model fallback and output cap (`client.py`), prompts per rule (`prompts/`), structured output validation (`validate.py`), cost with prompt-cache pricing (`pricing.py`), result cache keyed by request hash (`review.py`). Details and cost strategy: [PIPELINES.md](PIPELINES.md). |
| `gate/report/` | Finding schema, tool adapters (`rule_map.yml`), severity → action policy (`actions.py`), pre-existing debt (`baseline.py`: a High code-quality finding on a line the PR only moved becomes Medium; privacy, secrets and tests are never demoted), GitHub publishing, override, per-run cost: AI + CI minutes (`cost.py`). |
| `gate/eval/` | Runs the gate on each golden PR in a temporary worktree and scores it against `eval/ground_truth.yaml`: the merge verdict per PR (every finding counts, process rules included), then precision/recall on AGENTS#1-9. |

Trust boundaries:
- The gate code, prompts and lint config come from the **base branch** checkout, so a PR cannot change the rules it is judged by (except the bootstrap PR that introduces the gate).
- The deterministic job runs the PR's tests but never sees the Gemini key; the AI job holds the key but never executes PR code.
- PR text and code are passed to Gemini as untrusted data; the system prompt forbids following instructions inside them, and a script (A17, `prompt_injection.py`) flags text aimed at the reviewer as High.
- Secrets are masked (`secrets_scan.mask_secrets`) in every file and in the PR text before the request leaves for Gemini.
