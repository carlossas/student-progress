import logging

logger = logging.getLogger("student-progress.notify")


def log_contact(addr: str) -> None:
    logger.info("reminder queued to=%s", addr)
