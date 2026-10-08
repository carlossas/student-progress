import logging

from fastapi import FastAPI, HTTPException

from app import store
from app.privacy import redact

logger = logging.getLogger("student-progress")
app = FastAPI()


def _get_student(student_id: str):
    student = store.STUDENTS.get(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="student not found")
    return student


@app.get("/students/{student_id}/contact")
def get_contact(student_id: str):
    s = _get_student(student_id)
    logger.info("contact lookup %s", redact({"student_id": s.id, "email": s.email}))
    return {"student_id": s.id}


@app.post("/students/{student_id}/sync")
def sync(student_id: str):
    student = _get_student(student_id)
    logger.info("sync %s", student.id)
    raise HTTPException(status_code=409, detail=f"conflict for {student.id}")
