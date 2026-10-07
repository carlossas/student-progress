"""Pushes daily completion totals (aggregates only, no student data) to the support dashboard."""

import httpx

from app import store

SUPPORT_URL = "https://support.example.com/api/daily-totals"


def push_daily_totals() -> None:
    completed = sum(1 for r in store.PROGRESS if r.completed)
    httpx.post(SUPPORT_URL, json={"completed_lessons": completed})
