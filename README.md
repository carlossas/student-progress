# student-progress

Open English LMS service that tracks students' lesson progress.
**Some students are minors** — read `TEAM-STANDARDS.md` before making any changes.

## Running locally

Requires **Python 3.11+** (a virtual environment is recommended):

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest
```

## Endpoints

- `GET /health`
- `GET /lessons`
- `GET /students/{id}/progress`
- `POST /students/{id}/progress` — body: `{"lesson_id": "...", "score": 0-100}`

Data is held in memory (see `app/store.py`). There is no database: the focus of this repository is the review process, not persistence.
