"""Conversational session API — multi-turn estimation with memory."""

import structlog
from fastapi import APIRouter

from app.schemas.session import SessionCreateResponse
from app.sessions import session_store

log = structlog.get_logger()

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionCreateResponse)
async def create_session() -> SessionCreateResponse:
    """Create an empty conversational session and return its identifier."""
    session = session_store.create()
    log.info("session_created", session_id=session.session_id)
    return SessionCreateResponse(session_id=session.session_id)
