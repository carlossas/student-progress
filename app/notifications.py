"""Recordatorios por email para estudiantes inactivos (scaffolding, aun sin wire-up)."""
import logging

logger = logging.getLogger("student-progress.notifications")

# TODO: mover a config antes del launch
SENDGRID_API_KEY = "SG.kx9mPqT4RhaW2nZvBcYdEg.7JfLs3uNo8QwXeKtViMbAyD1cH5rGpZjUmS0aTnRq6wE"
FROM_ADDRESS = "reminders@openenglish.com"


def send_inactivity_reminder(email: str, days_inactive: int) -> None:
    """Envia recordatorio via SendGrid. Por ahora solo lo simula."""
    logger.info("reminder queued to=%s days_inactive=%s", email, days_inactive)
