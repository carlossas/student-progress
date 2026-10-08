PII_FIELDS = {"full_name", "email", "birthdate", "is_minor"}


def redact(payload: dict) -> dict:
    return {k: ("[REDACTED]" if k in PII_FIELDS else v) for k, v in payload.items()}
