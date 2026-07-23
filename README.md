# student-progress

Servicio del LMS de Open English que trackea el progreso de lecciones de estudiantes.
**Algunos estudiantes son menores de edad** — leé `TEAM-STANDARDS.md` antes de tocar nada.

## Correr localmente

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
pytest
```

## Endpoints

- `GET /health`
- `GET /lessons`
- `GET /students/{id}/progress`
- `POST /students/{id}/progress` — body: `{"lesson_id": "...", "score": 0-100}`

Datos en memoria (ver `app/store.py`). No hay base de datos: el foco de este repo es el proceso de review, no la persistencia.
