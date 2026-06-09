"""Pure helpers for the Streamlit chat UI — no Streamlit imports."""

from app.context.examples import format_examples_for_prompt, select_examples
from app.services.llm_service import GenerationOptions, build_system_prompt

ChatMessage = dict[str, str]
LastCall = dict[str, str | int | None]


def default_generation_options() -> GenerationOptions:
    """Return default GenerationOptions for a new chat session."""
    return GenerationOptions()


def initial_session_state() -> dict[str, list[ChatMessage] | LastCall | None]:
    """Return the initial Streamlit session_state keys for the chat UI."""
    return {
        "messages": [],
        "last_call": None,
    }


def to_api_messages(messages: list[ChatMessage]) -> list[dict[str, str]]:
    """Convert chat history to the message list expected by stream_estimation."""
    return [
        {"role": message["role"], "content": message["content"]}
        for message in messages
        if message.get("role") in ("user", "assistant") and message.get("content")
    ]


def build_last_call(meta: dict, latency_ms: int | None = None) -> LastCall:
    """Build sidebar metrics from stream meta or a generate_estimation result."""
    usage = meta.get("usage") or {}
    return {
        "model": meta.get("model", ""),
        "provider": meta.get("provider", ""),
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "latency_ms": latency_ms if latency_ms is not None else meta.get("latency_ms", 0),
        "finish_reason": meta.get("finish_reason"),
    }


def sidebar_system_prompt(opts: GenerationOptions) -> str:
    """Return the read-only system prompt shown in the sidebar."""
    return build_system_prompt(
        example_format=opts.example_format,
        num_examples=opts.num_examples,
        use_examples=opts.use_examples,
        inline_cleaning=(opts.preprocessing == "inline_cleaning"),
    )


def sidebar_cag_context(opts: GenerationOptions) -> str:
    """Return the read-only CAG examples block for the sidebar."""
    if not opts.use_examples or opts.num_examples <= 0:
        return ""
    return format_examples_for_prompt(
        select_examples(opts.num_examples),
        opts.example_format,
    )
