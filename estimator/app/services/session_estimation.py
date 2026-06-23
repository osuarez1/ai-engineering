"""Orchestration for multi-turn session estimations."""

from app.schemas.request_form import DetailLevel, EstimationRequest, OutputFormat, ProjectType
from app.services.llm_service import generate_session_estimation
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


def run_session_estimation(
    session: Session,
    enriched_transcript: str,
    *,
    version: str = "v2",
) -> dict:
    """Generate an estimate, update memory, and append the turn to history."""
    request = build_session_estimation_request(enriched_transcript)
    result = generate_session_estimation(
        request,
        session.project_metadata,
        version=version,
    )
    session.project_metadata = update_metadata_heuristic(
        session.project_metadata,
        enriched_transcript,
        result["text"],
    )
    session.history.add_turn(enriched_transcript, result["text"])
    session.touch()
    return result
