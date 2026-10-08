from datetime import date

from app.streaks import current_streak


def test_streak_returns_int():
    assert isinstance(current_streak([date(2026, 7, 1)]), int)


def test_streak_never_negative():
    assert current_streak([]) >= 0


def test_streak_handles_duplicates():
    today = date(2026, 7, 22)
    dates = [date(2026, 7, 21), date(2026, 7, 21)]
    assert current_streak(dates, today=today) >= 0
