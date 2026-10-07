from app.privacy import redact


def test_redact_masks_every_personal_field():
    payload = {"student_id": "s-001", "full_name": "x", "email": "x", "birthdate": "x", "is_minor": True}

    redacted = redact(payload)

    for field in ("full_name", "email", "birthdate", "is_minor"):
        assert redacted[field] == "[REDACTED]"
    assert redacted["student_id"] == "s-001"
