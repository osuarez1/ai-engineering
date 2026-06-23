from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.schemas.request_form import (
    DetailLevel,
    EstimationRequest,
    OutputFormat,
    ProjectType,
)
from app.services import llm_service
from app.services.llm_service import (
    LLMServiceError,
    GenerationOptions,
    _call_anthropic,
    _call_gemini,
    _call_openai,
    _gemini_usage_dict,
    _normalize_gemini_finish_reason,
    _to_gemini_contents,
    generate_estimation_from_request,
    generate_session_estimation,
)
from app.sessions import ProjectMetadata

REQUEST = EstimationRequest(
    description="We need a small CRM with auth, contacts and roles. MVP in six weeks.",
    project_type=ProjectType.WEB_SAAS,
    detail_level=DetailLevel.MEDIUM,
    output_format=OutputFormat.PHASES_TABLE,
)

ESTIMATION_TEXT = "## Estimate\n\nTotal: 120 hours · 7,500 EUR"


def _provider_result(provider: str) -> dict:
    return {
        "estimation": ESTIMATION_TEXT,
        "model": "test-model",
        "provider": provider,
        "finish_reason": "stop",
        "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
    }


def test_generate_estimation_from_request_openai(
    monkeypatch: pytest.MonkeyPatch, openai_settings: None
) -> None:
    monkeypatch.setattr(
        llm_service,
        "_call_openai",
        lambda messages, model, max_tokens: _provider_result("openai"),
    )

    result = generate_estimation_from_request(REQUEST)

    assert result["provider"] == "openai"
    assert result["text"] == ESTIMATION_TEXT


def test_generate_session_estimation_openai(
    monkeypatch: pytest.MonkeyPatch, openai_settings: None
) -> None:
    monkeypatch.setattr(
        llm_service,
        "_call_openai",
        lambda messages, model, max_tokens: _provider_result("openai"),
    )

    metadata = ProjectMetadata(project_name="BookFlow")
    result = generate_session_estimation(REQUEST, metadata, version="v2")

    assert result["provider"] == "openai"
    assert result["text"] == ESTIMATION_TEXT
    assert result["prompt_version"] == "v2"


def test_generate_session_estimation_anthropic(
    monkeypatch: pytest.MonkeyPatch, anthropic_settings: None
) -> None:
    monkeypatch.setattr(
        llm_service,
        "_call_anthropic",
        lambda **kwargs: _provider_result("anthropic"),
    )

    result = generate_session_estimation(REQUEST, ProjectMetadata(), version="v2")
    assert result["provider"] == "anthropic"


def test_generate_session_estimation_gemini(
    monkeypatch: pytest.MonkeyPatch, gemini_settings: None
) -> None:
    monkeypatch.setattr(
        llm_service,
        "_call_gemini",
        lambda **kwargs: _provider_result("gemini"),
    )

    result = generate_session_estimation(REQUEST, ProjectMetadata(), version="v2")
    assert result["provider"] == "gemini"


def test_generate_session_estimation_thinking_budget_ignored_for_openai(
    monkeypatch: pytest.MonkeyPatch, openai_settings: None
) -> None:
    monkeypatch.setattr(
        llm_service,
        "_call_openai",
        lambda messages, model, max_tokens: _provider_result("openai"),
    )

    result = generate_session_estimation(
        REQUEST,
        ProjectMetadata(),
        version="v2",
        opts=GenerationOptions(thinking_budget=1000),
    )
    assert result["provider"] == "openai"


def test_generate_session_estimation_thinking_budget_ignored_for_gemini(
    monkeypatch: pytest.MonkeyPatch, gemini_settings: None
) -> None:
    monkeypatch.setattr(
        llm_service,
        "_call_gemini",
        lambda **kwargs: _provider_result("gemini"),
    )

    result = generate_session_estimation(
        REQUEST,
        ProjectMetadata(),
        version="v2",
        opts=GenerationOptions(thinking_budget=1000),
    )
    assert result["provider"] == "gemini"


def test_generate_session_estimation_unsupported_provider_raises(
    monkeypatch: pytest.MonkeyPatch, openai_settings: None
) -> None:
    settings = SimpleNamespace(
        LLM_PROVIDER="unsupported",
        LLM_MODEL="test-model",
        OPENAI_API_KEY="sk-test",
    )
    monkeypatch.setattr(llm_service, "get_settings", lambda: settings)

    with pytest.raises(LLMServiceError, match="Unsupported LLM_PROVIDER"):
        generate_session_estimation(REQUEST, ProjectMetadata(), version="v2")


def test_generate_session_estimation_generic_exception_wrapped(
    monkeypatch: pytest.MonkeyPatch, openai_settings: None
) -> None:
    def boom(*args, **kwargs):
        raise RuntimeError("network timeout")

    monkeypatch.setattr(llm_service, "_call_openai", boom)

    with pytest.raises(LLMServiceError, match="LLM call failed: network timeout"):
        generate_session_estimation(REQUEST, ProjectMetadata(), version="v2")


def test_generate_estimation_from_request_anthropic(
    monkeypatch: pytest.MonkeyPatch, anthropic_settings: None
) -> None:
    monkeypatch.setattr(
        llm_service,
        "_call_anthropic",
        lambda **kwargs: _provider_result("anthropic"),
    )

    result = generate_estimation_from_request(REQUEST)

    assert result["provider"] == "anthropic"
    assert result["text"] == ESTIMATION_TEXT


def test_thinking_budget_ignored_for_openai(
    monkeypatch: pytest.MonkeyPatch, openai_settings: None
) -> None:
    monkeypatch.setattr(
        llm_service,
        "_call_openai",
        lambda messages, model, max_tokens: _provider_result("openai"),
    )

    result = generate_estimation_from_request(
        REQUEST,
        opts=GenerationOptions(thinking_budget=512),
    )

    assert result["text"] == ESTIMATION_TEXT


def test_thinking_budget_ignored_for_gemini(
    monkeypatch: pytest.MonkeyPatch, gemini_settings: None
) -> None:
    monkeypatch.setattr(
        llm_service,
        "_call_gemini",
        lambda **kwargs: _provider_result("gemini"),
    )

    result = generate_estimation_from_request(
        REQUEST,
        opts=GenerationOptions(thinking_budget=512),
    )

    assert result["provider"] == "gemini"


def test_unsupported_provider_raises(
    monkeypatch: pytest.MonkeyPatch, openai_settings: None
) -> None:
    settings = SimpleNamespace(
        LLM_PROVIDER="unsupported",
        LLM_MODEL="test-model",
        OPENAI_API_KEY="sk-test",
    )
    monkeypatch.setattr(llm_service, "get_settings", lambda: settings)

    with pytest.raises(LLMServiceError, match="Unsupported LLM_PROVIDER"):
        generate_estimation_from_request(REQUEST)


def test_llm_service_error_is_reraised(
    monkeypatch: pytest.MonkeyPatch, openai_settings: None
) -> None:
    def boom(*args, **kwargs):
        raise LLMServiceError("provider down")

    monkeypatch.setattr(llm_service, "_call_openai", boom)

    with pytest.raises(LLMServiceError, match="provider down"):
        generate_estimation_from_request(REQUEST)


def test_generic_exception_wrapped_as_llm_service_error(
    monkeypatch: pytest.MonkeyPatch, openai_settings: None
) -> None:
    def boom(*args, **kwargs):
        raise RuntimeError("network timeout")

    monkeypatch.setattr(llm_service, "_call_openai", boom)

    with pytest.raises(LLMServiceError, match="LLM call failed: network timeout"):
        generate_estimation_from_request(REQUEST)


def test_call_openai(monkeypatch: pytest.MonkeyPatch, openai_settings: None) -> None:
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content=ESTIMATION_TEXT), finish_reason="stop")
    ]
    mock_response.model = "gpt-4o-mini"
    mock_response.usage = MagicMock(prompt_tokens=11, completion_tokens=22, total_tokens=33)

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    monkeypatch.setattr("openai.OpenAI", lambda api_key: mock_client)

    result = _call_openai(
        [{"role": "user", "content": "hello"}],
        "gpt-4o-mini",
        1000,
    )

    assert result["estimation"] == ESTIMATION_TEXT
    assert result["provider"] == "openai"
    assert result["usage"]["total_tokens"] == 33


def test_call_anthropic(monkeypatch: pytest.MonkeyPatch, anthropic_settings: None) -> None:
    text_block = SimpleNamespace(type="text", text=ESTIMATION_TEXT)
    mock_response = SimpleNamespace(
        content=[text_block],
        stop_reason="end_turn",
        model="claude-haiku-4-5",
        usage=SimpleNamespace(input_tokens=5, output_tokens=7),
    )

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    monkeypatch.setattr("anthropic.Anthropic", lambda api_key: mock_client)

    result = _call_anthropic(
        system="system prompt",
        user_message="user prompt",
        model="claude-haiku-4-5",
        max_tokens=1000,
        thinking_budget=None,
    )

    assert result["estimation"] == ESTIMATION_TEXT
    assert result["provider"] == "anthropic"


def test_call_anthropic_with_thinking_budget(
    monkeypatch: pytest.MonkeyPatch, anthropic_settings: None
) -> None:
    text_block = SimpleNamespace(type="text", text=ESTIMATION_TEXT)
    mock_response = SimpleNamespace(
        content=[text_block],
        stop_reason="end_turn",
        model="claude-haiku-4-5",
        usage=SimpleNamespace(input_tokens=5, output_tokens=7),
    )

    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_response
    monkeypatch.setattr("anthropic.Anthropic", lambda api_key: mock_client)

    _call_anthropic(
        system="system prompt",
        user_message="user prompt",
        model="claude-haiku-4-5",
        max_tokens=1000,
        thinking_budget=500,
    )

    kwargs = mock_client.messages.create.call_args.kwargs
    assert kwargs["thinking"] == {"type": "enabled", "budget_tokens": 500}
    assert kwargs["max_tokens"] == 1524


def test_call_gemini(monkeypatch: pytest.MonkeyPatch, gemini_settings: None) -> None:
    mock_response = SimpleNamespace(
        text=ESTIMATION_TEXT,
        model_version="gemini-2.0-flash",
        candidates=[SimpleNamespace(finish_reason="STOP")],
        usage_metadata=SimpleNamespace(prompt_token_count=8, candidates_token_count=12),
    )

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    monkeypatch.setattr("google.genai.Client", lambda api_key: mock_client)

    result = _call_gemini(
        system="system prompt",
        messages=[{"role": "user", "content": "user prompt"}],
        model="gemini-2.0-flash",
        max_tokens=1000,
    )

    assert result["estimation"] == ESTIMATION_TEXT
    assert result["provider"] == "gemini"
    assert result["finish_reason"] == "stop"


def test_to_gemini_contents_maps_assistant_to_model() -> None:
    contents = _to_gemini_contents(
        [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
    )
    assert contents[0].role == "user"
    assert contents[1].role == "model"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, "stop"),
        ("MAX_TOKENS", "length"),
        ("length", "length"),
        ("STOP", "stop"),
    ],
)
def test_normalize_gemini_finish_reason(raw: str | None, expected: str) -> None:
    assert _normalize_gemini_finish_reason(raw) == expected


def test_gemini_usage_dict_handles_missing_metadata() -> None:
    assert _gemini_usage_dict(None) == {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }
