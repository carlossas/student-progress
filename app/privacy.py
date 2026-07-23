"""Helpers de privacidad. Ver TEAM-STANDARDS.md §3 y §4."""

PII_FIELDS = {"full_name", "email", "birthdate"}

# Retención en días por categoría de dato. Todo dataset nuevo DEBE declarar
# su categoría acá. Datos de menores: bucket más estricto.
RETENTION_DAYS = {
    "progress": 365,
    "progress_minor": 90,
}


def redact(payload: dict) -> dict:
    """Copia de payload segura para loguear: campos PII enmascarados."""
    return {k: ("[REDACTED]" if k in PII_FIELDS else v) for k, v in payload.items()}
