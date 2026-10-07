from dataclasses import dataclass


@dataclass
class Student:
    id: str
    full_name: str
    email: str
    birthdate: str
    country: str
    is_minor: bool
    phone: str  # expect: P1
