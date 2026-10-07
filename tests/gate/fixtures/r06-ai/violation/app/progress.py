def completion_percentage(completed_lesson_ids: list[str], total_lessons: int) -> int:
    """Percentage of the catalog completed, 0-100. Duplicate completions count once."""
    if total_lessons == 0:
        return 0
    return round(100 * len(set(completed_lesson_ids)) / total_lessons)
