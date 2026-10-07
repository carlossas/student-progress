def completion_percentage(completed_lesson_ids: list[str], total_lessons: int) -> int:
    """Percentage of the lesson catalog the student completed, from 0 to 100."""
    if total_lessons == 0:
        return 0
    distinct_completed = len(set(completed_lesson_ids))
    return round(100 * distinct_completed / total_lessons)
