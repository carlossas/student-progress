from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_pagination_slice():
    lessons = client.get("/lessons", params={"limit": 2, "offset": 1}).json()
    assert [lesson["id"] for lesson in lessons] == ["l-02", "l-03"]


def test_pagination_defaults_return_all():
    assert len(client.get("/lessons").json()) == 5


def test_pagination_invalid_params():
    assert client.get("/lessons", params={"limit": 0}).status_code == 422
    assert client.get("/lessons", params={"offset": -1}).status_code == 422
