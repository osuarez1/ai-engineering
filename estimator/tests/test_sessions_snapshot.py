import pytest
from fastapi.testclient import TestClient

from app.services import session_estimation
from app.sessions import session_store

TRANSCRIPT = "We need a small CRM with auth, contacts and roles. MVP in six weeks."
ESTIMATION_TEXT = "## Project estimate\n\nTotal: 120 hours · 7,500 EUR"


def _fake_llm_result() -> dict:
    return {
        "text": ESTIMATION_TEXT,
        "prompt_version": "v2",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        "finish_reason": "stop",
        "latency_ms": 42,
        "cost_usd": 0.0001,
        "cache_hit_kind": "none",
    }


@pytest.fixture
def session_id(client: TestClient) -> str:
    return client.post("/sessions").json()["session_id"]


def test_get_session_snapshot_empty_session(client: TestClient, session_id: str) -> None:
    response = client.get(f"/sessions/{session_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == session_id
    assert body["message_count"] == 0
    assert body["anchors_count"] == 0
    assert body["anchors"] == []
    assert body["summary_chars"] == 0
    assert body["summary"] == ""
    assert body["last_resolved_tier"] == ""
    assert body["last_tier_rule"] == ""
    assert body["project_metadata"]["project_name"] is None
    assert body["last_turn_observed"] is None


def test_get_session_snapshot_after_estimate(
    client: TestClient,
    session_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        session_estimation,
        "generate_estimation_from_messages",
        lambda *args, **kwargs: _fake_llm_result(),
    )

    transcript = (
        "The project is called Nimbus. Budget 30000 EUR approved. "
        "We need auth and multi-tenant support."
    )
    estimate_response = client.post(
        f"/sessions/{session_id}/estimate",
        data={"transcript": transcript},
    )
    assert estimate_response.status_code == 200

    response = client.get(f"/sessions/{session_id}")
    assert response.status_code == 200
    body = response.json()

    assert body["message_count"] == 2
    assert body["anchors_count"] >= 2
    assert any("Nimbus" in anchor for anchor in body["anchors"])
    assert body["summary_chars"] > 0
    assert "Nimbus" in body["summary"]
    assert body["last_resolved_tier"] == "low"
    assert body["project_metadata"]["project_name"] == "Nimbus"
    assert body["project_metadata"]["budget_eur"] == 30000


def test_get_session_snapshot_includes_last_turn_observed(
    client: TestClient,
    session_id: str,
) -> None:
    session = session_store.get_or_raise(session_id)
    session.last_turn_observed = {
        "turn_index": 1,
        "session_id": session_id,
        "cost_usd": 0.01,
        "cache_hit_kind": "none",
    }

    response = client.get(f"/sessions/{session_id}")
    assert response.status_code == 200
    assert response.json()["last_turn_observed"]["turn_index"] == 1
    assert response.json()["last_turn_observed"]["cost_usd"] == 0.01


def test_get_session_snapshot_unknown_session_returns_404(client: TestClient) -> None:
    response = client.get("/sessions/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"
