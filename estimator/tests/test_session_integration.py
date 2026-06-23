"""Step 7 integration tests — httpx.AsyncClient against the session API."""

import httpx
import pytest

from app.config import get_settings
from app.services import llm_service, session_estimation
from tests.conftest import make_pdf_with_text

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


@pytest.fixture
async def async_session_id(async_client: httpx.AsyncClient) -> str:
    response = await async_client.post("/sessions")
    assert response.status_code == 200
    return response.json()["session_id"]


@pytest.mark.asyncio
async def test_multi_turn_metadata_updates(
    async_client: httpx.AsyncClient,
    async_session_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Two chained estimates should accumulate project_metadata across turns."""
    monkeypatch.setattr(
        session_estimation,
        "generate_estimation_from_messages",
        lambda *args, **kwargs: _fake_llm_result(),
    )

    first = await async_client.post(
        f"/sessions/{async_session_id}/estimate",
        data={
            "transcript": (
                "The project is called BookFlow. We need auth, contacts, and roles."
            ),
        },
    )
    assert first.status_code == 200
    assert first.json()["project_metadata"]["project_name"] == "BookFlow"

    second = await async_client.post(
        f"/sessions/{async_session_id}/estimate",
        data={
            "transcript": (
                "We have 3 full-time engineers and will use Redis for session caching."
            ),
        },
    )
    assert second.status_code == 200
    metadata = second.json()["project_metadata"]
    assert metadata["project_name"] == "BookFlow"
    assert metadata["assumed_team_size"] == 3
    assert "Redis" in metadata["mentioned_technologies"]


@pytest.mark.asyncio
async def test_pdf_attachment_influences_llm_context(
    async_client: httpx.AsyncClient,
    async_session_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A PDF attachment should enrich the user message sent to the LLM."""
    captured: list[list[dict]] = []

    def fake_generate(messages, *, version: str = "v2", opts=None) -> dict:
        captured.append(messages)
        return _fake_llm_result()

    monkeypatch.setattr(session_estimation, "generate_estimation_from_messages", fake_generate)

    pdf_bytes = make_pdf_with_text("PostgreSQL required for persistence.")
    response = await async_client.post(
        f"/sessions/{async_session_id}/estimate",
        data={"transcript": TRANSCRIPT},
        files=[("attachments", ("spec.pdf", pdf_bytes, "application/pdf"))],
    )

    assert response.status_code == 200
    user_message = captured[0][-1]["content"]
    assert "=== attachment: spec.pdf ===" in user_message
    assert "PostgreSQL required" in user_message


@pytest.mark.asyncio
async def test_eight_turn_sliding_window_caps_llm_history(
    async_client: httpx.AsyncClient,
    async_session_id: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """After eight turns the LLM payload must respect MAX_CONVERSATION_TURNS."""
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
        response = await async_client.post(
            f"/sessions/{async_session_id}/estimate",
            data={"transcript": f"Turn {index}: we need a CRM with auth and roles."},
        )
        assert response.status_code == 200

    last_messages = call_log[-1]
    non_system = [message for message in last_messages if message["role"] != "system"]
    assert len(non_system) <= get_settings().MAX_CONVERSATION_TURNS * 2

    get_settings.cache_clear()
