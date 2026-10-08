from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_unknown_lesson_rejected():
    resp = client.post("/students/s-004/progress", params={"lesson_id": "l-99", "score": 50})
    assert resp.status_code == 422


def test_out_of_range_score_rejected():
    assert client.post("/students/s-004/progress", params={"lesson_id": "l-01", "score": 101}).status_code == 422
    assert client.post("/students/s-004/progress", params={"lesson_id": "l-01", "score": -5}).status_code == 422


def test_valid_score_accepted():
    resp = client.post("/students/s-004/progress", params={"lesson_id": "l-02", "score": 100})
    assert resp.json() == {"ok": True}
