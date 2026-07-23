"""Datos en memoria para el ejercicio."""
from app.models import Lesson, ProgressRecord, Student

STUDENTS = {
    "s-001": Student("s-001", "Valentina Rojas", "valen.rojas@example.com", "2013-04-02", "CO", True),
    "s-002": Student("s-002", "Mateo Fernández", "mateo.f@example.com", "2011-11-19", "MX", True),
    "s-003": Student("s-003", "Lucía Pereyra", "lucia.pereyra@example.com", "1994-06-30", "AR", False),
    "s-004": Student("s-004", "Jorge Salas", "jsalas@example.com", "1988-01-12", "PE", False),
}

LESSONS = [
    Lesson("l-01", "Greetings & Introductions", "A1"),
    Lesson("l-02", "Present Simple", "A1"),
    Lesson("l-03", "Food & Ordering", "A2"),
    Lesson("l-04", "Past Simple", "A2"),
    Lesson("l-05", "Making Plans", "B1"),
]

PROGRESS = [
    ProgressRecord("s-001", "l-01", True, 92),
    ProgressRecord("s-001", "l-02", True, 85),
    ProgressRecord("s-002", "l-01", True, 78),
    ProgressRecord("s-003", "l-01", True, 95),
    ProgressRecord("s-003", "l-02", True, 88),
    ProgressRecord("s-003", "l-03", True, 91),
]
