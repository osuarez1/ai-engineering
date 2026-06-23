"""Orchestration for multi-turn session estimations."""

from app.config import get_settings
from app.prompts.loader import render_session_system_prompt, render_session_user_prompt
from app.schemas.request_form import DetailLevel, EstimationRequest, OutputFormat, ProjectType
from app.services.llm_service import generate_estimation_from_messages
from app.services.metadata_extractor import update_metadata_heuristic
from app.sessions import Session


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
) -> dict:
    """Generate an estimate using session history, then update memory."""
    messages = build_session_messages(session, enriched_transcript, version=version)
    result = generate_estimation_from_messages(messages, version=version)
    user_content_sent = messages[-1]["content"]
    session.project_metadata = update_metadata_heuristic(
        session.project_metadata,
        enriched_transcript,
        result["text"],
    )
    session.history.add_turn(user_content_sent, result["text"])
    session.touch()
    return result
