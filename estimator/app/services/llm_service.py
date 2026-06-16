"""LLM service — form-based estimations via versioned Jinja2 prompts.

Session 4 replaced the legacy transcription + CAG path (``build_system_prompt``,
``generate_estimation``, ``stream_estimation``) with a single entrypoint that
renders prompts from ``app/prompts/`` and dispatches to the provider wrappers
below. Provider abstraction is unchanged from Session 3.
"""

import time
from dataclasses import dataclass

import structlog

from app.config import get_settings
from app.prompts.loader import render_estimation_prompt
from app.schemas.request_form import EstimationRequest

log = structlog.get_logger()

DEFAULT_MAX_TOKENS = 4000


class LLMServiceError(Exception):
    """Raised when the LLM provider call fails."""


@dataclass
class GenerationOptions:
    """Per-request knobs for the LLM call.

    Trimmed in Session 4: preprocessing, CAG example count/format, and
    ``use_examples`` moved into Jinja templates (``examples.j2``).
    """

    model: str | None = None
    max_tokens: int = DEFAULT_MAX_TOKENS
    thinking_budget: int | None = None


def generate_estimation_from_request(
    request: EstimationRequest,
    *,
    version: str = "v1",
    opts: GenerationOptions | None = None,
) -> dict:
    """Generate a software estimation from a typed form request.

    Prompts come from ``app/prompts/estimation/<version>/`` via Jinja2.
    Returns a dict shaped for ``request_form.EstimationResponse``.
    """
    opts = opts or GenerationOptions()
    settings = get_settings()
    t0 = time.perf_counter()

    system_prompt, user_input = render_estimation_prompt(request, version=version)
    model = opts.model or settings.LLM_MODEL

    log.info(
        "generating_estimation_from_request",
        provider=settings.LLM_PROVIDER,
        model=model,
        prompt_version=version,
        project_type=request.project_type.value,
        detail_level=request.detail_level.value,
        output_format=request.output_format.value,
        max_tokens=opts.max_tokens,
        thinking_budget=opts.thinking_budget,
    )

    # Each provider receives system and user as separate roles — never concatenated.
    try:
        if settings.LLM_PROVIDER == "openai":
            if opts.thinking_budget is not None:
                log.warning("thinking_budget_ignored_for_provider", provider="openai")
            result = _call_openai(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                model=model,
                max_tokens=opts.max_tokens,
            )
        elif settings.LLM_PROVIDER == "anthropic":
            result = _call_anthropic(
                system=system_prompt,
                user_message=user_input,
                model=model,
                max_tokens=opts.max_tokens,
                thinking_budget=opts.thinking_budget,
            )
        elif settings.LLM_PROVIDER == "gemini":
            if opts.thinking_budget is not None:
                log.warning("thinking_budget_ignored_for_provider", provider="gemini")
            result = _call_gemini(
                system=system_prompt,
                messages=[{"role": "user", "content": user_input}],
                model=model,
                max_tokens=opts.max_tokens,
            )
        else:
            raise LLMServiceError(f"Unsupported LLM_PROVIDER: {settings.LLM_PROVIDER}")
    except LLMServiceError:
        raise
    except Exception as exc:
        log.error("llm_call_failed", error=str(exc), provider=settings.LLM_PROVIDER)
        raise LLMServiceError(f"LLM call failed: {exc}") from exc

    # Map provider wrapper key ("estimation") to the form API contract ("text").
    return {
        "text": result["estimation"],
        "prompt_version": version,
        "model": result["model"],
        "provider": result["provider"],
        "usage": result["usage"],
        "finish_reason": result["finish_reason"],
        "latency_ms": int((time.perf_counter() - t0) * 1000),
    }


# ---------------------------------------------------------------------------
# Provider wrappers (Session 3 — unchanged dispatch surface)
#
# All three return the same dict shape so the entrypoint stays provider-agnostic.
# Streaming variants were removed with the legacy chat UI.
# ---------------------------------------------------------------------------


def _to_gemini_contents(messages: list[dict[str, str]]) -> list:
    """Map chat messages to Gemini Content objects (assistant -> model role)."""
    from google.genai import types

    contents = []
    for message in messages:
        role = message["role"]
        gemini_role = "user" if role == "user" else "model"
        contents.append(
            types.Content(
                role=gemini_role,
                parts=[types.Part.from_text(text=message["content"])],
            )
        )
    return contents


def _normalize_gemini_finish_reason(finish_reason: str | None) -> str:
    """Map Gemini finish reasons to the shared stop/length vocabulary."""
    if not finish_reason:
        return "stop"
    normalized = finish_reason.lower()
    if normalized in {"max_tokens", "length"}:
        return "length"
    return "stop"


def _gemini_usage_dict(usage_metadata) -> dict[str, int]:
    input_tokens = getattr(usage_metadata, "prompt_token_count", 0) or 0
    output_tokens = getattr(usage_metadata, "candidates_token_count", 0) or 0
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


def _call_openai(messages: list[dict], model: str, max_tokens: int) -> dict:
    """Send a chat completion request to the OpenAI API."""
    from openai import OpenAI

    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
    )

    usage = response.usage
    finish_reason = response.choices[0].finish_reason or "stop"

    log.info(
        "llm_response_received",
        provider="openai",
        model=response.model,
        finish_reason=finish_reason,
        input_tokens=usage.prompt_tokens,
        output_tokens=usage.completion_tokens,
    )

    return {
        "estimation": response.choices[0].message.content,
        "model": response.model,
        "provider": "openai",
        "finish_reason": finish_reason,
        "usage": {
            "input_tokens": usage.prompt_tokens,
            "output_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
        },
    }


def _call_anthropic(
    system: str,
    user_message: str,
    model: str,
    max_tokens: int,
    thinking_budget: int | None,
) -> dict:
    """Send a message request to the Anthropic API."""
    from anthropic import Anthropic

    settings = get_settings()
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    kwargs: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user_message}],
    }
    if thinking_budget is not None:
        kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
        kwargs["max_tokens"] = max(max_tokens, thinking_budget + 1024)

    response = client.messages.create(**kwargs)

    finish_reason = response.stop_reason or "stop"

    estimation_text = next(
        (block.text for block in response.content if getattr(block, "type", None) == "text"),
        "",
    )

    log.info(
        "llm_response_received",
        provider="anthropic",
        model=response.model,
        finish_reason=finish_reason,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )

    return {
        "estimation": estimation_text,
        "model": response.model,
        "provider": "anthropic",
        "finish_reason": finish_reason,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        },
    }


def _call_gemini(
    system: str,
    messages: list[dict[str, str]],
    model: str,
    max_tokens: int,
) -> dict:
    """Send a generate_content request to the Gemini API."""
    from google import genai
    from google.genai import types

    settings = get_settings()
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    response = client.models.generate_content(
        model=model,
        contents=_to_gemini_contents(messages),
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
        ),
    )

    finish_reason = "stop"
    if response.candidates:
        finish_reason = _normalize_gemini_finish_reason(response.candidates[0].finish_reason)

    usage = _gemini_usage_dict(response.usage_metadata)

    log.info(
        "llm_response_received",
        provider="gemini",
        model=response.model_version or model,
        finish_reason=finish_reason,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
    )

    return {
        "estimation": response.text or "",
        "model": response.model_version or model,
        "provider": "gemini",
        "finish_reason": finish_reason,
        "usage": usage,
    }
