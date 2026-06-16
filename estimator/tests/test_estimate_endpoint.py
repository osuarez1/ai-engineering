from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.services import llm_service

ESTIMATION_TEXT = "## Project estimate\n\nTotal: 120 hours · 7,500 EUR"

DEFAULT_PAYLOAD = {
    "description": "We need a small CRM with auth, contacts and roles. MVP in six weeks.",
    "project_type": "web_saas",
    "detail_level": "medium",
    "output_format": "phases_table",
}


def _fake_openai_response(*, estimation: str = ESTIMATION_TEXT, finish_reason: str = "stop") -> dict:
    return {
        "estimation": estimation,
        "model": "gpt-4o-mini",
        "provider": "openai",
        "finish_reason": finish_reason,
        "usage": {"input_tokens": 1234, "output_tokens": 567, "total_tokens": 1801},
    }


@pytest.fixture
def call_log(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict]]:
    """Replace _call_openai with a recording fake. Returns the list of calls made."""
    calls: list[dict] = []

    def fake(messages: list[dict], model: str, max_tokens: int) -> dict:
        calls.append({"messages": messages, "model": model, "max_tokens": max_tokens})
        return _fake_openai_response()

    monkeypatch.setattr(llm_service, "_call_openai", fake)
    yield calls


def test_default_request_returns_text_and_prompt_version(
    client: TestClient, call_log: list[dict]
) -> None:
    response = client.post("/api/v1/estimate", json=DEFAULT_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert body["text"] == ESTIMATION_TEXT
    assert body["prompt_version"] == "v1"
    assert len(call_log) == 1


def test_llm_receives_separate_system_and_user_messages(
    client: TestClient, call_log: list[dict]
) -> None:
    response = client.post("/api/v1/estimate", json=DEFAULT_PAYLOAD)
    assert response.status_code == 200

    messages = call_log[0]["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "senior software consultant" in messages[0]["content"]
    assert DEFAULT_PAYLOAD["description"] in messages[1]["content"]
    assert DEFAULT_PAYLOAD["description"] not in messages[0]["content"]


def test_output_format_affects_system_prompt(client: TestClient, call_log: list[dict]) -> None:
    payload = {**DEFAULT_PAYLOAD, "output_format": "narrative"}
    response = client.post("/api/v1/estimate", json=payload)
    assert response.status_code == 200

    system_msg = call_log[0]["messages"][0]["content"]
    assert "connected prose" in system_msg


def test_description_too_short_returns_422(client: TestClient) -> None:
    payload = {**DEFAULT_PAYLOAD, "description": "too short"}
    response = client.post("/api/v1/estimate", json=payload)
    assert response.status_code == 422


def test_llm_service_error_returns_500(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*args, **kwargs):
        raise llm_service.LLMServiceError("provider unavailable")

    monkeypatch.setattr(
        "app.routers.estimations.generate_estimation_from_request",
        boom,
    )

    response = client.post("/api/v1/estimate", json=DEFAULT_PAYLOAD)
    assert response.status_code == 500
    assert response.json()["detail"] == "provider unavailable"


def test_prompt_version_v2_uses_v2_templates(
    client: TestClient, call_log: list[dict]
) -> None:
    response = client.post(
        "/api/v1/estimate",
        params={"prompt_version": "v2"},
        json=DEFAULT_PAYLOAD,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["prompt_version"] == "v2"

    system_msg = call_log[0]["messages"][0]["content"]
    user_msg = call_log[0]["messages"][1]["content"]
    assert "pragmatic technical delivery lead" in system_msg
    assert "Reference deliveries" in system_msg
    assert "## Client brief" in user_msg
    assert "senior software consultant" not in system_msg


def test_unknown_prompt_version_returns_422(client: TestClient) -> None:
    response = client.post(
        "/api/v1/estimate",
        params={"prompt_version": "v99"},
        json=DEFAULT_PAYLOAD,
    )
    assert response.status_code == 422
