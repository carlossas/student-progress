"""Lookup context for support agents, to speed up tickets."""


def support_context(student, records) -> dict:
    return {
        "student_id": student.id,
        "name": student.full_name,
        "email": student.email,
        "birthdate": student.birthdate,
        "completed": sum(1 for r in records if r.completed),
    }
