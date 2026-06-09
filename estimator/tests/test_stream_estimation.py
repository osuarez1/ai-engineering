from collections.abc import Iterator

import pytest

from app.config import get_settings
from app.services import llm_service
from app.services.llm_service import stream_estimation


@pytest.fixture
def openai_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure OpenAI provider with a fake key."""
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def gemini_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure Gemini provider with a fake key."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-test-key")
    monkeypatch.setenv("LLM_MODEL", "gemini-2.0-flash")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def anthropic_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure Anthropic provider with a fake key."""
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("LLM_MODEL", "claude-haiku-4-5")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_stream_openai_yields_tokens_and_meta(
    monkeypatch: pytest.MonkeyPatch, openai_settings: None
) -> None:
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


def test_stream_anthropic_yields_tokens_and_meta(
    monkeypatch: pytest.MonkeyPatch, anthropic_settings: None
) -> None:
    meta: dict = {}

    def fake_stream(
        system: str,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        thinking_budget: int | None,
        meta: dict,
    ) -> Iterator[str]:
        assert "software consultant" in system
        assert messages[-1]["role"] == "user"
        assert model == "claude-haiku-4-5"
        assert max_tokens == 4000
        assert thinking_budget is None
        meta.update(
            {
                "model": model,
                "provider": "anthropic",
                "finish_reason": "end_turn",
                "usage": {"input_tokens": 200, "output_tokens": 80, "total_tokens": 280},
            }
        )
        yield from ["Estimate", " ready"]

    monkeypatch.setattr(llm_service, "_stream_anthropic", fake_stream)

    tokens = list(stream_estimation([{"role": "user", "content": "estimate this"}], meta=meta))

    assert tokens == ["Estimate", " ready"]
    assert meta["provider"] == "anthropic"
    assert meta["finish_reason"] == "end_turn"


def test_stream_gemini_yields_tokens_and_meta(
    monkeypatch: pytest.MonkeyPatch, gemini_settings: None
) -> None:
    meta: dict = {}

    def fake_stream(
        system: str,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        meta: dict,
    ) -> Iterator[str]:
        assert "software consultant" in system
        assert messages[-1]["role"] == "user"
        assert model == "gemini-2.0-flash"
        assert max_tokens == 4000
        meta.update(
            {
                "model": model,
                "provider": "gemini",
                "finish_reason": "stop",
                "usage": {"input_tokens": 150, "output_tokens": 60, "total_tokens": 210},
            }
        )
        yield from ["Gemini", " stream"]

    monkeypatch.setattr(llm_service, "_stream_gemini", fake_stream)

    tokens = list(stream_estimation([{"role": "user", "content": "estimate this"}], meta=meta))

    assert tokens == ["Gemini", " stream"]
    assert meta["provider"] == "gemini"
    assert meta["usage"]["total_tokens"] == 210


def test_to_gemini_contents_maps_assistant_to_model() -> None:
    contents = llm_service._to_gemini_contents(
        [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
    )
    assert contents[0].role == "user"
    assert contents[1].role == "model"
