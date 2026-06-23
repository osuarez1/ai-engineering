"""Pure helpers for the Streamlit conversational session UI — no Streamlit imports.

Session 5 replaces the Session 4 typed form with a multi-turn client that talks
to ``POST /sessions`` and ``POST /sessions/{session_id}/estimate``. These helpers
hold HTTP calls, session-state defaults, and transcript validation so
``streamlit_app.py`` stays thin and unit-testable.
"""

from __future__ import annotations

from collections.abc import Callable

import httpx

from app.schemas.session import SessionEstimationResponse
from app.sessions import ProjectMetadata

API_BASE_DEFAULT = "http://localhost:8000"
DEFAULT_SESSION_PROMPT_VERSION = "v2"
SUPPORTED_PROMPT_VERSIONS = ("v1", "v2")
MIN_TRANSCRIPT_LENGTH = 20


def empty_project_metadata() -> dict:
    """Return an empty ``project_metadata`` payload for session state."""
    return ProjectMetadata().model_dump()


def initial_session_state() -> dict:
    """Return the initial Streamlit ``session_state`` keys for the session UI."""
    return {
        "session_id": None,
        "project_metadata": empty_project_metadata(),
        "prompt_version": DEFAULT_SESSION_PROMPT_VERSION,
        "last_estimation": None,
    }


def validate_transcript(transcript: str) -> str | None:
    """Return an error message when the transcript is too short, else ``None``."""
    if len(transcript.strip()) < MIN_TRANSCRIPT_LENGTH:
        return f"Transcript must be at least {MIN_TRANSCRIPT_LENGTH} characters."
    return None


def create_session(
    api_base: str = API_BASE_DEFAULT,
    *,
    timeout: float = 30.0,
    post: Callable[..., httpx.Response] = httpx.post,
) -> str:
    """Create a server-side conversational session and return its id."""
    response = post(f"{api_base.rstrip('/')}/sessions", timeout=timeout)
    response.raise_for_status()
    return response.json()["session_id"]


def submit_session_estimate(
    session_id: str,
    transcript: str,
    attachments: list[tuple[str, bytes, str]],
    *,
    api_base: str = API_BASE_DEFAULT,
    prompt_version: str = DEFAULT_SESSION_PROMPT_VERSION,
    timeout: float = 120.0,
    post: Callable[..., httpx.Response] = httpx.post,
) -> SessionEstimationResponse:
    """POST a multipart estimate for the current session turn."""
    url = f"{api_base.rstrip('/')}/sessions/{session_id}/estimate"
    files = [
        ("attachments", (filename, content, mime_type))
        for filename, content, mime_type in attachments
    ]
    kwargs: dict = {
        "data": {"transcript": transcript},
        "params": {"prompt_version": prompt_version},
        "timeout": timeout,
    }
    if files:
        kwargs["files"] = files
    response = post(url, **kwargs)
    response.raise_for_status()
    return SessionEstimationResponse.model_validate(response.json())


def prepare_attachment_payloads(
    uploads: list | None,
) -> list[tuple[str, bytes, str]]:
    """Normalise Streamlit ``UploadedFile`` objects into multipart tuples."""
    if not uploads:
        return []
    payloads: list[tuple[str, bytes, str]] = []
    for upload in uploads:
        if not upload.name:
            continue
        content = upload.getvalue()
        mime_type = upload.type or "application/octet-stream"
        payloads.append((upload.name, content, mime_type))
    return payloads


def ensure_session_id(
    session_state: dict,
    *,
    api_base: str = API_BASE_DEFAULT,
    create_session_fn: Callable[[str], str] | None = None,
) -> str:
    """Create a session on first load and persist ``session_id`` in state."""
    if session_state.get("session_id"):
        return session_state["session_id"]

    for key, value in initial_session_state().items():
        session_state.setdefault(key, value)

    create = create_session_fn or create_session
    session_state["session_id"] = create(api_base)
    return session_state["session_id"]


def reset_conversation_state(
    session_state: dict,
    *,
    api_base: str = API_BASE_DEFAULT,
    create_session_fn: Callable[[str], str] | None = None,
) -> str:
    """Start a fresh server session and clear local conversational state."""
    create = create_session_fn or create_session
    session_state["session_id"] = create(api_base)
    session_state["project_metadata"] = empty_project_metadata()
    session_state["last_estimation"] = None
    return session_state["session_id"]
