"""Pydantic schemas for conversational session endpoints."""

from pydantic import BaseModel, Field


class SessionCreateResponse(BaseModel):
    """Response body for ``POST /sessions``."""

    session_id: str = Field(description="UUID v4 identifier for the new session")
