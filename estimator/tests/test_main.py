import pytest
from fastapi.testclient import TestClient

from app.main import app, lifespan


@pytest.mark.asyncio
async def test_lifespan(openai_settings: None) -> None:
    async with lifespan(app):
        pass


def test_health_includes_environment(client: TestClient) -> None:
    response = client.get("/health")
    assert response.json()["environment"] == "development"
