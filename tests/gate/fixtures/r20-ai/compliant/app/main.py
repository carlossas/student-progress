from fastapi import FastAPI

from app import store

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/students/{student_id}/streak")
def get_streak(student_id: str):
    """Number of distinct days with at least one recorded completion."""
    days = sorted({r.day for r in store.PROGRESS if r.student_id == student_id}, reverse=True)
    return {"student_id": student_id, "streak": len(days)}
