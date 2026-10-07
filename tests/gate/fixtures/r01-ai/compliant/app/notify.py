import logging

from app.privacy import redact

logger = logging.getLogger("student-progress.notify")


def log_reminder(student_id: str) -> None:
    logger.info("reminder queued %s", redact({"student_id": student_id}))
