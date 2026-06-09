import pytest

from app.context.examples import CANONICAL_EXAMPLES
from app.services import llm_service
from app.services.llm_service import generate_estimation

WELL_FORMED_MD = CANONICAL_EXAMPLES[0].estimation_markdown
TRANSCRIPTION = (
    "We need a small CRM with auth, contacts and roles. MVP delivery in six weeks."
)


def test_generate_estimation_gemini(monkeypatch: pytest.MonkeyPatch, gemini_settings: None) -> None:
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
        assert messages[-1]["content"] == TRANSCRIPTION
        assert "software consultant" in system
        return {
            "estimation": WELL_FORMED_MD,
            "model": model,
            "provider": "gemini",
            "finish_reason": "stop",
            "usage": {"input_tokens": 321, "output_tokens": 99, "total_tokens": 420},
        }

    monkeypatch.setattr(llm_service, "_call_gemini", fake_call)

    result = generate_estimation(TRANSCRIPTION)

    assert result["provider"] == "gemini"
    assert result["model"] == "gemini-2.0-flash"
    assert result["estimation"] == WELL_FORMED_MD
    assert len(calls) == 1
    assert calls[0]["messages"][0]["role"] == "user"
