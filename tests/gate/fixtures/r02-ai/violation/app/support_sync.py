"""Pushes per-student progress to the support tool so agents have context."""

import httpx

from app import store

SUPPORT_URL = "https://support.example.com/api/contacts"


def push_progress(student_id: str) -> None:
    s = store.STUDENTS[student_id]
    records = [r for r in store.PROGRESS if r.student_id == student_id]
    httpx.post(SUPPORT_URL, json={"country": s.country, "dob": s.birthdate, "lessons": len(records)})
