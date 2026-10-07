import logging
from dataclasses import asdict

from fastapi import FastAPI, HTTPException

from app import store

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
    logger.info("contact lookup for %s", s.email)  # expect: P2 log
    return {"email": s.email}  # expect: P2 response


@app.post("/students/{student_id}/sync")
def sync(student_id: str):
    student = _get_student(student_id)
    logger.info("sync %s", asdict(student))  # expect: P3 log
    raise HTTPException(status_code=409, detail=f"conflict for {student}")  # expect: P3 exception
