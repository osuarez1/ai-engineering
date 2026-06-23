from collections.abc import AsyncIterator, Iterator
from io import BytesIO

import httpx
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject

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


@pytest.fixture
async def async_client() -> AsyncIterator[httpx.AsyncClient]:
    """Provide an httpx AsyncClient wired to the FastAPI ASGI app."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


def make_pdf_with_text(text: str) -> bytes:
    """Build a minimal PDF whose text ``pypdf`` can extract in tests."""
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    stream_data = f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode()
    content = StreamObject()
    content._data = stream_data
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
    )
    page[NameObject("/Resources")] = resources
    page[NameObject("/Contents")] = content
    buffer = BytesIO()
    writer.write(buffer)
    return buffer.getvalue()
