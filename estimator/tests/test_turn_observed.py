import pytest
from fastapi.testclient import TestClient

from app.services import session_estimation
from app.services.session_estimation import run_session_estimation
from app.sessions import Session, session_store

TRANSCRIPT = (
    "The project is called Nimbus. Budget 30000 EUR approved. "
    "We need auth and multi-tenant support."
)
ESTIMATION_TEXT = "## Project estimate\n\nTotal: 120 hours · 7,500 EUR"


def _fake_llm_result(*, cache_hit_kind: str = "none") -> dict:
    return {
        "text": ESTIMATION_TEXT,
        "prompt_version": "v2",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
        "finish_reason": "stop",
        "latency_ms": 42,
        "cost_usd": 0.0001,
        "cache_hit_kind": cache_hit_kind,
    }


def test_run_session_estimation_emits_all_turn_observed_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Session()
    monkeypatch.setattr(
        session_estimation,
        "generate_estimation_from_messages",
        lambda *args, **kwargs: _fake_llm_result(),
    )

    run_session_estimation(
        session,
        TRANSCRIPT,
        version="v2",
        attachments_total_chars=500,
    )

    observed = session.last_turn_observed
    assert observed is not None
    assert set(observed.keys()) == {
        "turn_index",
        "session_id",
        "enriched_transcript_chars",
        "attachments_total_chars",
        "messages_in_window",
        "anchors_count",
        "summary_chars",
        "tokens_in",
        "tokens_out",
        "cost_usd",
        "latency_ms",
        "cache_hit_kind",
        "last_resolved_tier",
    }
    assert observed["turn_index"] == 1
    assert observed["session_id"] == session.session_id
    assert observed["enriched_transcript_chars"] == len(TRANSCRIPT)
    assert observed["attachments_total_chars"] == 500
    assert observed["messages_in_window"] == 2
    assert observed["anchors_count"] == len(session.anchors)
    assert observed["summary_chars"] == len(session.summary)
    assert observed["tokens_in"] == 100
    assert observed["tokens_out"] == 50
    assert observed["cost_usd"] == pytest.approx(0.0001)
    assert observed["latency_ms"] == 42
    assert observed["cache_hit_kind"] == "none"
    assert observed["last_resolved_tier"] == "low"


def test_run_session_estimation_increments_turn_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Session()
    monkeypatch.setattr(
        session_estimation,
        "generate_estimation_from_messages",
        lambda *args, **kwargs: _fake_llm_result(),
    )

    run_session_estimation(session, TRANSCRIPT, attachments_total_chars=0)
    run_session_estimation(session, TRANSCRIPT + " More scope.", attachments_total_chars=0)

    assert session.turn_index == 2
    assert session.last_turn_observed is not None
    assert session.last_turn_observed["turn_index"] == 2
    assert session.last_turn_observed["messages_in_window"] == 4


def test_run_session_estimation_logs_turn_observed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Session()
    logged: list[tuple] = []

    def capture_info(event: str, **kwargs) -> None:
        logged.append((event, kwargs))

    monkeypatch.setattr(
        session_estimation,
        "generate_estimation_from_messages",
        lambda *args, **kwargs: _fake_llm_result(),
    )
    monkeypatch.setattr(session_estimation.log, "info", capture_info)

    run_session_estimation(session, TRANSCRIPT)

    assert logged[-1][0] == "turn_observed"
    assert logged[-1][1]["turn_index"] == 1
    assert logged[-1][1]["session_id"] == session.session_id


def test_estimate_endpoint_populates_last_turn_observed(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        session_estimation,
        "generate_estimation_from_messages",
        lambda *args, **kwargs: _fake_llm_result(cache_hit_kind="exact"),
    )

    session_id = client.post("/sessions").json()["session_id"]
    response = client.post(
        f"/sessions/{session_id}/estimate",
        data={"transcript": TRANSCRIPT},
    )
    assert response.status_code == 200

    snapshot = client.get(f"/sessions/{session_id}").json()
    observed = snapshot["last_turn_observed"]
    assert observed["turn_index"] == 1
    assert observed["session_id"] == session_id
    assert observed["attachments_total_chars"] == 0
    assert observed["cache_hit_kind"] == "exact"
    assert observed["tokens_in"] == 100
    assert observed["cost_usd"] == pytest.approx(0.0001)

    session = session_store.get_or_raise(session_id)
    assert session.last_turn_observed == observed
