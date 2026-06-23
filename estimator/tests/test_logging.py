import pytest

from app.config import get_settings
from app.logging import configure_logging


def test_configure_logging_development(openai_settings: None) -> None:
    configure_logging()


def test_configure_logging_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    configure_logging()
    get_settings.cache_clear()


def test_configure_logging_respects_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    configure_logging()
    get_settings.cache_clear()
