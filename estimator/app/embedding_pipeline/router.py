"""Embedding ingestion API router."""

import structlog
from fastapi import APIRouter, HTTPException

from app.embedding_pipeline.schemas import IngestRequest, IngestResponse

log = structlog.get_logger()

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_embeddings(request: IngestRequest) -> IngestResponse:
    """Persist chunked embeddings for one document (implemented in ingest service)."""
    # Stub until transactional persistence is wired (ingest-service todo).
    log.warning(
        "ingest_not_implemented",
        source_path=request.source_path,
        document_type=request.document_type,
    )
    raise HTTPException(
        status_code=501,
        detail="Ingest persistence not implemented yet",
    )
