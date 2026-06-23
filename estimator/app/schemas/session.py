"""Pydantic schemas for conversational session endpoints."""

from pydantic import BaseModel, Field

from app.sessions import ProjectMetadata


class SessionCreateResponse(BaseModel):
    """Response body for ``POST /sessions``."""

    session_id: str = Field(description="UUID v4 identifier for the new session")


class SessionEstimationResponse(BaseModel):
    """Response body for ``POST /sessions/{session_id}/estimate``."""

    text: str
    prompt_version: str
    project_metadata: ProjectMetadata
