"""Orchestration for multi-turn session estimations."""

import structlog

from app.config import get_settings
from app.prompts.loader import render_session_system_prompt, render_session_user_prompt
from app.schemas.request_form import DetailLevel, EstimationRequest, OutputFormat, ProjectType
from app.services.anchor_extractor import update_anchors
from app.services.llm_service import (
    DEFAULT_MAX_TOKENS,
    GenerationOptions,
    generate_estimation_from_messages,
)
from app.services.metadata_extractor import update_metadata_heuristic
from app.services.summarizer import update_summary
from app.services.tiers import adjust_max_tokens, resolve_tier
from app.sessions import Session

log = structlog.get_logger()


def build_session_estimation_request(enriched_transcript: str) -> EstimationRequest:
    """Map a session transcript (plus attachments) to the Jinja prompt contract.

    Typed form fields are fixed to sensible defaults for conversational mode;
    the exercise endpoint only accepts ``transcript`` and ``attachments``.
    ``model_construct`` skips the 2000-character cap on ``description`` so
    large extracted documents can flow through.
    """
    return EstimationRequest.model_construct(
        description=enriched_transcript,
        project_type=ProjectType.WEB_SAAS,
        detail_level=DetailLevel.MEDIUM,
        output_format=OutputFormat.PHASES_TABLE,
        reference_projects=None,
    )


def cap_outgoing_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Trim oldest user/assistant pairs so the LLM payload respects the window.

    The current user message is included in the cap — at most ``MAX_CONVERSATION_TURNS``
    user/assistant pairs worth of non-system content may be sent per call.
    """
    if not messages or messages[0]["role"] != "system":
        return messages

    max_non_system = get_settings().MAX_CONVERSATION_TURNS * 2
    system = messages[0]
    rest = messages[1:]
    while len(rest) > max_non_system:
        if len(rest) >= 2 and rest[0]["role"] == "user" and rest[1]["role"] == "assistant":
            rest = rest[2:]
        else:
            rest = rest[1:]
    return [system, *rest]


def build_session_messages(
    session: Session,
    enriched_transcript: str,
    *,
    version: str = "v2",
) -> list[dict[str, str]]:
    """Assemble the LLM message array for the current session turn.

    The system prompt is regenerated from the current ``project_metadata``.
    Prior turns come from ``ConversationHistory.to_messages_list()``; the new
    user message is appended last and is not stored until after the LLM responds.
    """
    request = build_session_estimation_request(enriched_transcript)
    system_prompt = render_session_system_prompt(
        request,
        session.project_metadata,
        version=version,
        anchors=session.anchors,
        summary=session.summary,
    )
    messages = session.history.to_messages_list(system_prompt)
    user_input = render_session_user_prompt(request, version=version)
    messages.append({"role": "user", "content": user_input})
    return cap_outgoing_messages(messages)


def run_session_estimation(
    session: Session,
    enriched_transcript: str,
    *,
    version: str = "v2",
    attachments_total_chars: int = 0,
) -> dict:
    """Generate an estimate using session history, then update memory."""
    messages = build_session_messages(session, enriched_transcript, version=version)
    messages_in_window = len(messages) - 1
    tier = resolve_tier(len(enriched_transcript), messages_in_window)
    session.last_resolved_tier = tier.label
    session.last_tier_rule = tier.rule
    opts = GenerationOptions(max_tokens=adjust_max_tokens(DEFAULT_MAX_TOKENS, tier))
    result = generate_estimation_from_messages(messages, version=version, opts=opts)
    user_content_sent = messages[-1]["content"]
    session.project_metadata = update_metadata_heuristic(
        session.project_metadata,
        enriched_transcript,
        result["text"],
    )
    session.anchors = update_anchors(
        session.anchors,
        enriched_transcript,
        result["text"],
        session.project_metadata,
    )
    session.summary = update_summary(session.summary, enriched_transcript, result["text"])
    session.history.add_turn(user_content_sent, result["text"])
    session.touch()

    turn_index = session.turn_index + 1
    session.turn_index = turn_index
    usage = result.get("usage") or {}
    turn_observed = {
        "turn_index": turn_index,
        "session_id": session.session_id,
        "enriched_transcript_chars": len(enriched_transcript),
        "attachments_total_chars": attachments_total_chars,
        "messages_in_window": len(session.history.messages),
        "anchors_count": len(session.anchors),
        "summary_chars": len(session.summary),
        "tokens_in": usage.get("input_tokens", 0),
        "tokens_out": usage.get("output_tokens", 0),
        "cost_usd": result.get("cost_usd", 0.0),
        "latency_ms": result.get("latency_ms", 0),
        "cache_hit_kind": result.get("cache_hit_kind", "none"),
        "last_resolved_tier": session.last_resolved_tier,
    }
    session.last_turn_observed = turn_observed
    log.info("turn_observed", **turn_observed)

    return result
