def completion_percentage(completed_lesson_ids: list[str], total_lessons: int) -> int:
    """Percentage of the lesson catalog the student completed, from 0 to 100."""
    x2 = len(completed_lesson_ids)
    if total_lessons == 0:
        return 0
    return round(100 * x2 / total_lessons)
