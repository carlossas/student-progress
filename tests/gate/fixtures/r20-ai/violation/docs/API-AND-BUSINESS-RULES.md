# API and business rules

What the service does today on `main`.

## Endpoints

| Method | Path | Response 200 | Errors |
|--------|------|--------------|--------|
| GET | `/health` | `{"status": "ok"}` | — |

## Business rules

| # | Rule |
|---|------|
| BR-1 | Unknown student → 404 on every student endpoint. |
