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


class SessionSnapshotResponse(BaseModel):
    """Response body for ``GET /sessions/{session_id}``."""

    session_id: str
    message_count: int
    anchors_count: int
    anchors: list[str]
    summary_chars: int
    summary: str
    last_resolved_tier: str
    last_tier_rule: str
    project_metadata: ProjectMetadata
    last_turn_observed: dict | None
