"""Step 7 integration tests — httpx.AsyncClient against the session API."""

import httpx
import pytest

from app.services import session_estimation
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
