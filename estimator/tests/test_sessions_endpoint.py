from io import BytesIO

import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.config import get_settings
from app.services import llm_service, session_estimation
from app.services.llm_service import LLMServiceError
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
    }


def _make_docx(paragraph: str) -> bytes:
    document = Document()
    document.add_paragraph(paragraph)
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@pytest.fixture
def session_id(client: TestClient) -> str:
    return client.post("/sessions").json()["session_id"]


def test_estimate_session_returns_estimation(
    client: TestClient,
    session_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        session_estimation,
        "generate_estimation_from_messages",
        lambda *args, **kwargs: _fake_llm_result(),
    )

    response = client.post(
        f"/sessions/{session_id}/estimate",
        data={"transcript": TRANSCRIPT},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["text"] == ESTIMATION_TEXT
    assert body["prompt_version"] == "v2"
    assert body["project_metadata"]["project_name"] is None

    session = session_store.get(session_id)
    assert session is not None
    assert len(session.history.messages) == 2


def test_estimate_session_with_docx_attachment(
    client: TestClient,
    session_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[list[dict]] = []

    def fake_generate(messages, *, version: str = "v2", opts=None) -> dict:
        captured.append(messages)
        return _fake_llm_result()

    monkeypatch.setattr(session_estimation, "generate_estimation_from_messages", fake_generate)

    docx_bytes = _make_docx("Architecture requires PostgreSQL and Redis.")
    response = client.post(
        f"/sessions/{session_id}/estimate",
        data={"transcript": TRANSCRIPT},
        files=[("attachments", ("spec.docx", docx_bytes, "application/vnd.openxmlformats"))],
    )

    assert response.status_code == 200
    assert "=== attachment: spec.docx ===" in captured[0][-1]["content"]
    assert "PostgreSQL and Redis" in captured[0][-1]["content"]


def test_estimate_session_unknown_session_returns_404(client: TestClient) -> None:
    response = client.post(
        "/sessions/00000000-0000-0000-0000-000000000000/estimate",
        data={"transcript": TRANSCRIPT},
    )
    assert response.status_code == 404


def test_estimate_session_short_transcript_returns_422(
    client: TestClient,
    session_id: str,
) -> None:
    response = client.post(
        f"/sessions/{session_id}/estimate",
        data={"transcript": "too short"},
    )
    assert response.status_code == 422


def test_estimate_session_unsupported_attachment_returns_422(
    client: TestClient,
    session_id: str,
) -> None:
    response = client.post(
        f"/sessions/{session_id}/estimate",
        data={"transcript": TRANSCRIPT},
        files=[("attachments", ("notes.txt", b"plain", "text/plain"))],
    )
    assert response.status_code == 422
    assert "Unsupported attachment type" in response.json()["detail"]


def test_estimate_session_updates_project_metadata(
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
        "The project is called BookFlow. We need a CRM with auth and contacts. "
        "Stack is Rails and React with PostgreSQL."
    )
    response = client.post(
        f"/sessions/{session_id}/estimate",
        data={"transcript": transcript},
    )

    assert response.status_code == 200
    metadata = response.json()["project_metadata"]
    assert metadata["project_name"] == "BookFlow"
    assert "Rails" in metadata["mentioned_technologies"]
    assert "React" in metadata["mentioned_technologies"]


def test_estimate_session_sliding_window_caps_llm_history(
    client: TestClient,
    session_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_CONVERSATION_TURNS", "6")
    get_settings.cache_clear()

    call_log: list[list[dict]] = []

    def fake_openai(messages, model, max_tokens):
        call_log.append(messages)
        return {
            "estimation": ESTIMATION_TEXT,
            "model": "gpt-4o-mini",
            "provider": "openai",
            "finish_reason": "stop",
            "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
        }

    monkeypatch.setattr(llm_service, "_call_openai", fake_openai)

    for index in range(8):
        response = client.post(
            f"/sessions/{session_id}/estimate",
            data={"transcript": f"Turn {index}: we need a CRM with auth and roles."},
        )
        assert response.status_code == 200

    last_messages = call_log[-1]
    non_system = [message for message in last_messages if message["role"] != "system"]
    assert len(non_system) <= get_settings().MAX_CONVERSATION_TURNS * 2

    get_settings.cache_clear()


def test_estimate_session_llm_error_returns_500(
    client: TestClient,
    session_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*args, **kwargs):
        raise LLMServiceError("provider unavailable")

    monkeypatch.setattr(session_estimation, "generate_estimation_from_messages", boom)

    response = client.post(
        f"/sessions/{session_id}/estimate",
        data={"transcript": TRANSCRIPT},
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "provider unavailable"
