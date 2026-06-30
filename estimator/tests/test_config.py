import pytest
from pydantic import ValidationError

from app.config import Settings


@pytest.mark.parametrize(
    ("provider", "field", "key"),
    [
        ("openai", "OPENAI_API_KEY", "sk-test"),
        ("anthropic", "ANTHROPIC_API_KEY", "sk-ant-test"),
        ("gemini", "GEMINI_API_KEY", "gemini-test-key"),
    ],
)
def test_valid_api_key_passes_for_provider(provider: str, field: str, key: str) -> None:
    settings = Settings(LLM_PROVIDER=provider, **{field: key})
    assert settings.LLM_PROVIDER == provider


@pytest.mark.parametrize(
    ("provider", "field", "message"),
    [
        ("openai", "OPENAI_API_KEY", "OPENAI_API_KEY is required when LLM_PROVIDER is 'openai'"),
        (
            "anthropic",
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_API_KEY is required when LLM_PROVIDER is 'anthropic'",
        ),
        ("gemini", "GEMINI_API_KEY", "GEMINI_API_KEY is required when LLM_PROVIDER is 'gemini'"),
    ],
)
def test_missing_api_key_raises_for_provider(
    provider: str, field: str, message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        Settings(LLM_PROVIDER=provider, **{field: None})


def test_max_conversation_turns_default() -> None:
    settings = Settings(
        LLM_PROVIDER="openai",
        OPENAI_API_KEY="sk-test",
    )
    assert settings.MAX_CONVERSATION_TURNS == 6


def test_stress_test_config_defaults() -> None:
    settings = Settings(
        LLM_PROVIDER="openai",
        OPENAI_API_KEY="sk-test",
    )
    assert settings.MAX_ATTACHMENT_CHARS == 60_000
    assert settings.LLM_CACHE_ENABLED is True
    assert settings.SEMANTIC_CACHE_THRESHOLD == 0.85
    assert settings.TIER_MEDIUM_CHARS == 8_000
    assert settings.TIER_HIGH_CHARS == 20_000
