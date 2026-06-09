from collections.abc import Iterator

import pytest

from app.config import get_settings
from app.services import llm_service
from app.services.llm_service import LLMServiceError, stream_estimation


@pytest.fixture(autouse=True)
def openai_test_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use OpenAI provider with a fake key for stream_estimation tests."""
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_stream_openai_yields_tokens_and_meta(monkeypatch: pytest.MonkeyPatch) -> None:
    meta: dict = {}

    def fake_stream(
        messages: list[dict], model: str, max_tokens: int, meta: dict
    ) -> Iterator[str]:
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert model == "gpt-4o-mini"
        assert max_tokens == 4000
        meta.update(
            {
                "model": model,
                "provider": "openai",
                "finish_reason": "stop",
                "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            }
        )
        yield from ["Hello", " world"]

    monkeypatch.setattr(llm_service, "_stream_openai", fake_stream)

    tokens = list(stream_estimation([{"role": "user", "content": "estimate this"}], meta=meta))

    assert tokens == ["Hello", " world"]
    assert meta["provider"] == "openai"
    assert meta["usage"]["output_tokens"] == 50


def test_stream_unsupported_provider_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    get_settings.cache_clear()

    with pytest.raises(LLMServiceError, match="Streaming not supported for provider: gemini"):
        list(stream_estimation([{"role": "user", "content": "hi"}]))
