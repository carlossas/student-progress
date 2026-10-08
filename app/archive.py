"""Archivo para cohort analytics.

Copiamos cada registro de progreso junto con los atributos del estudiante para
que el equipo de analytics pueda cortar cohortes sin hacer joins. Se conserva
indefinidamente para poder comparar year-over-year.
"""

ARCHIVE: list[dict] = []


def archive_progress(student, record) -> None:
    ARCHIVE.append(
        {
            "student_id": student.id,
            "full_name": student.full_name,
            "birthdate": student.birthdate,
            "country": student.country,
            "is_minor": student.is_minor,
            "lesson_id": record.lesson_id,
            "score": record.score,
        }
    )
