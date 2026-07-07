"""Pydantic schemas for the embedding ingestion pipeline."""

from typing import Any, Literal

from pydantic import BaseModel, Field


Sector = Literal["finance", "ecommerce", "healthcare", "industrial"]
Complexity = Literal["low", "medium", "high"]


class ClientMetadata(BaseModel):
    """Client context attached to a historical budget proposal."""

    name: str
    sector: Sector
    country: str = Field(min_length=2, max_length=2, description="ISO 3166-1 alpha-2 code")


class BudgetComponent(BaseModel):
    """A single deliverable component within a budget proposal."""

    component_id: str
    name: str
    description: str = Field(min_length=1)
    tech_stack: list[str] = Field(min_length=1)
    estimated_hours: int = Field(ge=1)
    complexity: Complexity
    dependencies: list[str] = Field(default_factory=list)


class Budget(BaseModel):
    """A complete historical budget proposal."""

    budget_id: str
    client_metadata: ClientMetadata
    project_summary: str = Field(min_length=1)
    main_technology: str = Field(min_length=1)
    year: int = Field(ge=2000, le=2100)
    total_estimated_hours: int = Field(ge=1)
    components: list[BudgetComponent] = Field(min_length=1)


class Chunk(BaseModel):
    """A text fragment ready for embedding."""

    chunk_id: str
    text: str = Field(min_length=1)
    metadata: dict[str, Any]
    token_count: int = Field(ge=0)


class EmbeddedChunk(Chunk):
    """A chunk with its embedding vector."""

    embedding: list[float] = Field(min_length=1)


class IngestRequest(BaseModel):
    """Request body for ``POST /embeddings/ingest``."""

    budgets: list[Budget] = Field(min_length=1)


class IngestStats(BaseModel):
    """Aggregated ingestion statistics returned with embedded chunks."""

    total_budgets: int = Field(ge=0)
    total_chunks: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0.0)


class IngestResponse(BaseModel):
    """Response body for ``POST /embeddings/ingest``."""

    chunks: list[EmbeddedChunk]
    stats: IngestStats
