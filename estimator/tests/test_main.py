import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app, configure_logging, lifespan


def test_configure_logging_development(openai_settings: None) -> None:
    configure_logging()


def test_configure_logging_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    get_settings.cache_clear()
    configure_logging()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_lifespan(openai_settings: None) -> None:
    async with lifespan(app):
        pass


def test_health_includes_environment(client: TestClient) -> None:
    response = client.get("/health")
    assert response.json()["environment"] == "development"
