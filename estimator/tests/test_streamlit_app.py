from collections.abc import Iterator
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from app.config import get_settings
from app.context.examples import CANONICAL_EXAMPLES
from app.services import llm_service
from app.services.llm_service import LLMServiceError

STREAMLIT_APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"
TRANSCRIPT = (
    "We need a small CRM with auth, contacts and roles. MVP delivery in six weeks."
)


def _load_app() -> AppTest:
    """Load the app script; Streamlit runs main() via the __main__ guard."""
    return AppTest.from_file(str(STREAMLIT_APP))


@pytest.fixture
def streamlit_app(openai_settings: None) -> AppTest:
    """Load the Streamlit app with fake OpenAI settings."""
    return _load_app()


def test_streamlit_app_module_is_importable_without_side_effects() -> None:
    import streamlit_app

    assert callable(streamlit_app.main)
    assert callable(streamlit_app.bootstrap)
    assert callable(streamlit_app.render_sidebar)
    assert callable(streamlit_app.render_chat)


def test_streamlit_app_loads(streamlit_app: AppTest) -> None:
    streamlit_app.run()

    assert not streamlit_app.exception
    assert streamlit_app.title[0].value == "Software Estimator"
    assert streamlit_app.sidebar.header[0].value == "Configuration"
    assert streamlit_app.chat_input


def test_streamlit_app_missing_api_key_shows_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    get_settings.cache_clear()

    app = _load_app()
    app.run()

    assert not app.exception
    assert any("LLM configuration error" in error.value for error in app.error)


def test_streamlit_app_chat_flow_streams_assistant_reply(
    monkeypatch: pytest.MonkeyPatch, openai_settings: None
) -> None:
    estimation = CANONICAL_EXAMPLES[0].estimation_markdown

    def fake_stream(
        messages: list[dict[str, str]],
        opts=None,
        meta: dict | None = None,
    ) -> Iterator[str]:
        assert messages[-1]["content"] == TRANSCRIPT
        if meta is not None:
            meta.update(
                {
                    "model": "gpt-4o-mini",
                    "provider": "openai",
                    "finish_reason": "stop",
                    "usage": {
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "total_tokens": 150,
                    },
                }
            )
        yield estimation

    monkeypatch.setattr(llm_service, "stream_estimation", fake_stream)

    app = _load_app()
    app.run()
    app.chat_input[0].set_value(TRANSCRIPT).run()

    assert not app.exception
    assert any(estimation[:40] in markdown.value for markdown in app.markdown)
    assert any(TRANSCRIPT in markdown.value for markdown in app.markdown)

    app.run()
    metric_labels = [metric.label for metric in app.sidebar.metric]
    assert metric_labels == ["Input tokens", "Output tokens", "Latency (ms)"]


def test_streamlit_app_shows_error_when_stream_fails(
    monkeypatch: pytest.MonkeyPatch, openai_settings: None
) -> None:
    def failing_stream(
        messages: list[dict[str, str]],
        opts=None,
        meta: dict | None = None,
    ) -> Iterator[str]:
        raise LLMServiceError("provider unavailable")
        yield ""  # pragma: no cover

    monkeypatch.setattr(llm_service, "stream_estimation", failing_stream)

    app = _load_app()
    app.run()
    app.chat_input[0].set_value(TRANSCRIPT).run()

    assert not app.exception
    assert any("Estimation failed" in error.value for error in app.error)
