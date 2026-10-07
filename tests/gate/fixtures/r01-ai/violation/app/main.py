from datetime import date

from fastapi import FastAPI

from app import notify, store

app = FastAPI()


@app.post("/students/{student_id}/reminder")
def queue_reminder(student_id: str):
    s = store.STUDENTS[student_id]
    contact = s.email
    notify.log_contact(contact)
    return {"ok": True}


@app.get("/students/{student_id}/profile")
def profile(student_id: str):
    s = store.STUDENTS[student_id]
    born = date.fromisoformat(s.birthdate)
    return {"student_id": s.id, "age": date.today().year - born.year}


@app.get("/students/juniors")
def juniors():
    return [sid for sid, s in store.STUDENTS.items() if s.is_minor]
