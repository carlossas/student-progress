"""Cohort snapshots for analytics.

Every progress event is copied together with the student's attributes so analytics can
slice cohorts without joins. Kept indefinitely for year-over-year comparisons.
"""

COHORT_EVENTS: list[dict] = []


def snapshot(student, record) -> None:
    event = {"student_id": student.id, "lesson_id": record.lesson_id, "score": record.score}
    event.update(country=student.country, birthdate=student.birthdate, is_minor=student.is_minor)
    COHORT_EVENTS.append(event)
