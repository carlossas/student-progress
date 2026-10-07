from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI()
LESSONS = {"l-01": "Greetings"}


class ProgressIn(BaseModel):
    lesson_id: str
    score: int = Field(0, ge=0, le=100)


@app.post("/students/{student_id}/progress")
def record_progress(student_id: str, payload: ProgressIn):
    try:
        return {"ok": LESSONS[payload.lesson_id]}
    except KeyError as e:
        raise HTTPException(status_code=422, detail="unknown lesson") from e
