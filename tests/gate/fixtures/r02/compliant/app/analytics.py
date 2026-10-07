import httpx

ANALYTICS_URL = "https://analytics.example.com/events"


def report_progress(s, lesson_id: str) -> None:
    httpx.post(ANALYTICS_URL, json={"student_id": s.id, "lesson_id": lesson_id})
