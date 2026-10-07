# API and business rules

What the service does today on `main` (`app/main.py`). Team rules live in [AGENTS.md](../AGENTS.md); architecture in [ARCHITECTURE.md](ARCHITECTURE.md).

## Endpoints

| Method | Path | Request body | Response 200 | Errors |
|--------|------|--------------|--------------|--------|
| GET | `/health` | — | `{"status": "ok"}` | — |
| GET | `/lessons` | — | List of `{id, title, level}` (5 lessons, no pagination) | — |
| GET | `/students/{id}/progress` | — | `{student_id, completed, total, percentage}` | 404 unknown student |
| POST | `/students/{id}/progress` | `{"lesson_id": "l-01", "score": 80}` | `{"ok": true}` | 404 unknown student |

Example: `GET /students/s-003/progress` → `{"student_id": "s-003", "completed": 3, "total": 5, "percentage": 60}`

## Business rules

| # | Rule | Where |
|---|------|-------|
| BR-1 | Unknown student → 404 on every student endpoint. | `_get_student` |
| BR-2 | Every recorded progress event is a completion (`completed = true`). | `record_progress` |
| BR-3 | `score` is optional, defaults to `0`, coerced to `int`. | `record_progress` |
| BR-4 | `percentage = round(100 * completed / total_lessons)`; `0` if there are no lessons. | `get_progress` |
| BR-5 | Responses never include student personal data. | `get_progress` |
| BR-6 | Progress logs go through `redact()`, which masks `full_name`, `email`, `birthdate` and `is_minor`. | `record_progress`, `privacy.redact` |

## Known gaps

Current behavior, not intended rules. Useful when reviewing PRs that touch this logic.

- `lesson_id` is not checked against the catalog: unknown lessons count as completed.
- `score` is not range-checked: negative or >100 values are accepted.
- Missing `lesson_id` or non-numeric `score` → HTTP 500 instead of 4xx (no Pydantic schema).
- Duplicate completions are counted twice, so `percentage` can exceed 100.
- No authentication: anyone can read or write any student's progress.
- `RETENTION_DAYS` is declared but nothing expires records.

## Seed data

| Student | Country | Minor | Completed lessons (score) |
|---------|---------|-------|---------------------------|
| `s-001` | CO | yes | l-01 (92), l-02 (85) |
| `s-002` | MX | yes | l-01 (78) |
| `s-003` | AR | no | l-01 (95), l-02 (88), l-03 (91) |
| `s-004` | PE | no | — |
