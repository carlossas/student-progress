from fastapi import FastAPI

from app import notify, store

app = FastAPI()


@app.post("/students/{student_id}/reminder")
def queue_reminder(student_id: str):
    s = store.STUDENTS[student_id]
    notify.log_reminder(s.id)
    return {"ok": True}


@app.get("/students/{student_id}/profile")
def profile(student_id: str):
    s = store.STUDENTS[student_id]
    completed = sum(1 for r in store.PROGRESS if r.student_id == s.id and r.completed)
    return {"student_id": s.id, "completed_lessons": completed}
