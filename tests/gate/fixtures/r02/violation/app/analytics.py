import httpx

ANALYTICS_URL = "https://analytics.example.com/events"


def report_progress(s, lesson_id: str) -> None:
    httpx.post(ANALYTICS_URL, json={"birthdate": s.birthdate, "is_minor": s.is_minor})  # expect: P2 outbound
