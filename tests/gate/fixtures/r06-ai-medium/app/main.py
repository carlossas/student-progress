from fastapi import FastAPI, HTTPException

from app import store

app = FastAPI()


@app.post("/students/{student_id}/progress")
def record_progress(student_id: str, lesson_id: str, score: int = 0):
    if lesson_id not in {lesson.id for lesson in store.LESSONS}:
        raise HTTPException(status_code=422, detail="unknown lesson")
    if score < 0 or score > 100:
        raise HTTPException(status_code=422, detail="score must be between 0 and 100")
    store.PROGRESS.append((student_id, lesson_id, score))
    return {"ok": True}
