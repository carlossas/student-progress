"""Lesson completion events for funnel analytics.

Purpose: measure which lessons students drop out of. Holds only the pseudonymous
student_id and lesson facts. Retention: RETENTION_DAYS["cohort_events"] (90 days).
"""

COHORT_EVENTS: list[dict] = []


def snapshot(student_id: str, lesson_id: str, score: int) -> None:
    COHORT_EVENTS.append({"student_id": student_id, "lesson_id": lesson_id, "score": score})
