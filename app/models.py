"""Modelos de dominio.

Clasificación de PII según TEAM-STANDARDS.md §3:
`full_name`, `email`, `birthdate` son `pii`; si `is_minor` es True, son `pii-minor`.
"""
from dataclasses import dataclass


@dataclass
class Student:
    id: str
    full_name: str  # pii / pii-minor
    email: str      # pii / pii-minor
    birthdate: str  # pii-minor sensible: revela edad
    country: str
    is_minor: bool


@dataclass
class Lesson:
    id: str
    title: str
    level: str


@dataclass
class ProgressRecord:
    student_id: str
    lesson_id: str
    completed: bool
    score: int
