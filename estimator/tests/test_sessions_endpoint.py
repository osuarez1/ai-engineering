import uuid

from fastapi.testclient import TestClient

from app.sessions import session_store


def test_create_session_returns_uuid(client: TestClient) -> None:
    response = client.post("/sessions")
    assert response.status_code == 200
    body = response.json()
    assert "session_id" in body
    uuid.UUID(body["session_id"])
    assert session_store.get(body["session_id"]) is not None


def test_create_session_returns_unique_ids(client: TestClient) -> None:
    first = client.post("/sessions").json()["session_id"]
    second = client.post("/sessions").json()["session_id"]
    assert first != second
