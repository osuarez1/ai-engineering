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


class EmbedManyResult(BaseModel):
    """Result of batch embedding, including token and cost totals."""

    chunks: list[EmbeddedChunk]
    total_tokens: int = Field(ge=0)
    estimated_cost_usd: float = Field(ge=0.0)


class IngestRequest(BaseModel):
    """Request body for ``POST /embeddings/ingest`` (persisted pipeline)."""

    source_path: str = Field(min_length=1)
    document_type: str = Field(min_length=1, max_length=50)
    content: Budget


class IngestResponse(BaseModel):
    """Response body for successful document ingestion."""

    document_id: int
    chunks_created: int = Field(ge=0)
    embedding_dimension: int = Field(ge=1)
    ingestion_time_ms: int = Field(ge=0)


class DocumentAlreadyIngestedDetail(BaseModel):
    """409 Conflict body when ``source_path`` was already ingested."""

    detail: str = "Document already ingested"
    document_id: int


class SearchRequest(BaseModel):
    """Request body for ``POST /search``."""

    query: str = Field(min_length=1)
    k: int = Field(default=5, ge=1, le=50)


class SearchResultItem(BaseModel):
    """One nearest-chunk hit from semantic search."""

    chunk_id: int
    document_id: int
    chunk_type: str
    content: str
    distance: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Response body for ``POST /search``."""

    query: str
    k: int
    search_time_ms: int = Field(ge=0)
    results: list[SearchResultItem]
