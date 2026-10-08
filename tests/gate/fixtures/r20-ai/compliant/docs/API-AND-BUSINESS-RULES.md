# API and business rules

What the service does today on `main`.

## Endpoints

| Method | Path | Response 200 | Errors |
|--------|------|--------------|--------|
| GET | `/health` | `{"status": "ok"}` | — |
| GET | `/students/{id}/streak` | `{"student_id", "streak"}` | — |

## Business rules

| # | Rule |
|---|------|
| BR-1 | Unknown student → 404 on every student endpoint. |
| BR-2 | Streak = number of distinct days with at least one recorded completion for the student. |
