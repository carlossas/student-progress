"""Racha de dias consecutivos con actividad, para gamification."""
from datetime import date, timedelta


def current_streak(activity_dates: list[date], today: date | None = None) -> int:
    """Cantidad de dias consecutivos con actividad, terminando hoy."""
    today = today or date.today()
    days = set(activity_dates)
    streak = 0
    day = today - timedelta(days=1)
    while day in days:
        streak += 1
        day -= timedelta(days=1)
    return streak
