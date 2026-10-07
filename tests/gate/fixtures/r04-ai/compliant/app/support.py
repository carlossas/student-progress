"""Lookup context for support agents, to speed up tickets."""


def support_context(student_id: str, records) -> dict:
    completed = [r for r in records if r.completed]
    return {
        "student_id": student_id,
        "completed": len(completed),
        "last_lesson": completed[-1].lesson_id if completed else None,
    }
