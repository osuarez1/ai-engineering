"""Conversational session API — multi-turn estimation with memory."""

from typing import Literal

import structlog
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.schemas.session import SessionCreateResponse, SessionEstimationResponse
from app.services.attachments import (
    UnsupportedAttachmentError,
    collect_attachment_payloads,
    enrich_transcript,
)
from app.services.llm_service import LLMServiceError
from app.services.session_estimation import run_session_estimation
from app.sessions import SessionNotFoundError, session_store

log = structlog.get_logger()

router = APIRouter(prefix="/sessions", tags=["sessions"])

DEFAULT_SESSION_PROMPT_VERSION = "v2"
PromptVersion = Literal["v1", "v2"]

MIN_TRANSCRIPT_LENGTH = 20


@router.post("", response_model=SessionCreateResponse)
async def create_session() -> SessionCreateResponse:
    """Create an empty conversational session and return its identifier."""
    session = session_store.create()
    log.info("session_created", session_id=session.session_id)
    return SessionCreateResponse(session_id=session.session_id)


@router.post("/{session_id}/estimate", response_model=SessionEstimationResponse)
async def estimate_session(
    session_id: str,
    transcript: str = Form(..., description="Meeting transcript or project brief text"),
    attachments: list[UploadFile] = File(
        default=[],
        description="Optional PDF or Word documents with supplementary context",
    ),
    prompt_version: PromptVersion = Query(
        DEFAULT_SESSION_PROMPT_VERSION,
        description="Jinja prompt template set under app/prompts/estimation/",
    ),
) -> SessionEstimationResponse:
    """Estimate a project within a conversational session."""
    if len(transcript.strip()) < MIN_TRANSCRIPT_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"transcript must be at least {MIN_TRANSCRIPT_LENGTH} characters",
        )

    try:
        session = session_store.get_or_raise(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None

    file_payloads = await collect_attachment_payloads(attachments)

    try:
        enriched_transcript = enrich_transcript(transcript, file_payloads)
    except UnsupportedAttachmentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        result = run_session_estimation(
            session,
            enriched_transcript,
            version=prompt_version,
        )
    except LLMServiceError as exc:
        log.error("session_estimation_error", session_id=session_id, error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    log.info(
        "session_estimation_completed",
        session_id=session_id,
        prompt_version=prompt_version,
        attachment_count=len(file_payloads),
    )
    return SessionEstimationResponse(
        text=result["text"],
        prompt_version=result["prompt_version"],
        project_metadata=session.project_metadata,
    )
