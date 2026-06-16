import pytest

from app.schemas.request_form import (
    DetailLevel,
    EstimationRequest,
    OutputFormat,
    ProjectType,
)
from app.services import llm_service
from app.services.llm_service import generate_estimation_from_request

ESTIMATION_TEXT = "## Estimate\n\nTotal: 120 hours · 7,500 EUR"

REQUEST = EstimationRequest(
    description="We need a small CRM with auth, contacts and roles. MVP in six weeks.",
    project_type=ProjectType.WEB_SAAS,
    detail_level=DetailLevel.MEDIUM,
    output_format=OutputFormat.PHASES_TABLE,
)


def test_generate_estimation_from_request_gemini(
    monkeypatch: pytest.MonkeyPatch, gemini_settings: None
) -> None:
    calls: list[dict] = []

    def fake_call(
        system: str,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
    ) -> dict:
        calls.append(
            {
                "system": system,
                "messages": messages,
                "model": model,
                "max_tokens": max_tokens,
            }
        )
        assert REQUEST.description in messages[-1]["content"]
        assert "software consultant" in system
        return {
            "estimation": ESTIMATION_TEXT,
            "model": model,
            "provider": "gemini",
            "finish_reason": "stop",
            "usage": {"input_tokens": 321, "output_tokens": 99, "total_tokens": 420},
        }

    monkeypatch.setattr(llm_service, "_call_gemini", fake_call)

    result = generate_estimation_from_request(REQUEST)

    assert result["provider"] == "gemini"
    assert result["model"] == "gemini-2.0-flash"
    assert result["text"] == ESTIMATION_TEXT
    assert result["prompt_version"] == "v1"
    assert len(calls) == 1
    assert calls[0]["messages"][0]["role"] == "user"
