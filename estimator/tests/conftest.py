from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

PROVIDER_FAKE_ENV: dict[str, dict[str, str]] = {
    "openai": {
        "LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "sk-test",
        "LLM_MODEL": "gpt-4o-mini",
    },
    "anthropic": {
        "LLM_PROVIDER": "anthropic",
        "ANTHROPIC_API_KEY": "sk-ant-test",
        "LLM_MODEL": "claude-haiku-4-5",
    },
    "gemini": {
        "LLM_PROVIDER": "gemini",
        "GEMINI_API_KEY": "gemini-test-key",
        "LLM_MODEL": "gemini-2.0-flash",
    },
}


def _apply_provider_env(monkeypatch: pytest.MonkeyPatch, provider: str) -> None:
    for key, value in PROVIDER_FAKE_ENV[provider].items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def test_llm_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Default API tests to OpenAI with a fake key so Settings validates."""
    _apply_provider_env(monkeypatch, "openai")
    yield
    get_settings.cache_clear()


@pytest.fixture
def openai_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Configure OpenAI provider with a fake key."""
    _apply_provider_env(monkeypatch, "openai")
    yield
    get_settings.cache_clear()


@pytest.fixture
def anthropic_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Configure Anthropic provider with a fake key."""
    _apply_provider_env(monkeypatch, "anthropic")
    yield
    get_settings.cache_clear()


@pytest.fixture
def gemini_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Configure Gemini provider with a fake key."""
    _apply_provider_env(monkeypatch, "gemini")
    yield
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    """Provide a FastAPI test client configured with the application."""
    return TestClient(app)
