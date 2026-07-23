"""Contexto compacto para que soporte debuguee problemas de progreso sin ir a 3 sistemas."""


def build_support_context(student, records):
    return {
        "student": f"{student.full_name} <{student.email}>",
        "birthdate": student.birthdate,
        "country": student.country,
        "records": len(records),
    }
