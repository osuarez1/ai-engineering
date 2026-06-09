from app.context.examples import CANONICAL_EXAMPLES
from app.services.llm_service import GenerationOptions
from app.ui import streamlit_helpers


def test_default_generation_options_returns_defaults() -> None:
    opts = streamlit_helpers.default_generation_options()
    assert opts == GenerationOptions()


def test_initial_session_state() -> None:
    state = streamlit_helpers.initial_session_state()
    assert state == {"messages": [], "last_call": None}


def test_to_api_messages_filters_roles_and_empty_content() -> None:
    messages = [
        {"role": "user", "content": "Estimate this project"},
        {"role": "assistant", "content": "Here is the breakdown"},
        {"role": "system", "content": "ignored"},
        {"role": "user", "content": ""},
    ]
    assert streamlit_helpers.to_api_messages(messages) == [
        {"role": "user", "content": "Estimate this project"},
        {"role": "assistant", "content": "Here is the breakdown"},
    ]


def test_build_last_call_from_stream_meta() -> None:
    meta = {
        "model": "gpt-4o-mini",
        "provider": "openai",
        "finish_reason": "stop",
        "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
    }
    assert streamlit_helpers.build_last_call(meta, latency_ms=250) == {
        "model": "gpt-4o-mini",
        "provider": "openai",
        "input_tokens": 100,
        "output_tokens": 50,
        "latency_ms": 250,
        "finish_reason": "stop",
    }


def test_build_last_call_from_generate_estimation_result() -> None:
    result = {
        "model": "claude-haiku-4-5",
        "provider": "anthropic",
        "finish_reason": "end_turn",
        "latency_ms": 900,
        "usage": {"input_tokens": 200, "output_tokens": 80, "total_tokens": 280},
    }
    assert streamlit_helpers.build_last_call(result) == {
        "model": "claude-haiku-4-5",
        "provider": "anthropic",
        "input_tokens": 200,
        "output_tokens": 80,
        "latency_ms": 900,
        "finish_reason": "end_turn",
    }


def test_sidebar_system_prompt_includes_role_and_rates() -> None:
    opts = GenerationOptions(num_examples=0, use_examples=False)
    prompt = streamlit_helpers.sidebar_system_prompt(opts)
    assert "senior software consultant" in prompt
    assert "62.50 EUR/hour" in prompt


def test_sidebar_cag_context_empty_when_examples_disabled() -> None:
    opts = GenerationOptions(use_examples=False, num_examples=3)
    assert streamlit_helpers.sidebar_cag_context(opts) == ""


def test_sidebar_cag_context_renders_markdown_examples() -> None:
    opts = GenerationOptions(num_examples=1, example_format="markdown")
    context = streamlit_helpers.sidebar_cag_context(opts)
    assert CANONICAL_EXAMPLES[0].title in context
    assert "| Task | Hours | Cost (EUR) |" in context
