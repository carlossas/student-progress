from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app import store
from app.models import ProgressRecord

app = FastAPI()


class ProgressIn(BaseModel):
    lesson_id: str
    score: int


@app.post("/students/{student_id}/progress")
def record_progress(student_id: str, payload: ProgressIn):
    if student_id not in store.STUDENTS:
        raise HTTPException(status_code=404, detail="student not found")
    store.PROGRESS.append(ProgressRecord(student_id, payload.lesson_id, True, payload.score))
    return {"ok": True}
