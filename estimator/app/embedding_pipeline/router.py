"""Embedding ingestion API router."""

import structlog
from fastapi import APIRouter, HTTPException

from app.embedding_pipeline.chunker import JSONStructuralChunker
from app.embedding_pipeline.embedder import OpenAIEmbedder, estimate_cost_usd
from app.embedding_pipeline.schemas import IngestRequest, IngestResponse, IngestStats

log = structlog.get_logger()

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_embeddings(request: IngestRequest) -> IngestResponse:
    """Chunk budget proposals and return vectorized components."""
    chunker = JSONStructuralChunker()
    embedder = OpenAIEmbedder()

    try:
        chunks = chunker.chunk(request.budgets)
        embedded_chunks = embedder.embed_many(chunks)
    except Exception as exc:
        log.error("embedding_ingest_error", error=str(exc))
        raise HTTPException(status_code=500, detail="Embedding ingestion failed") from exc

    total_tokens = sum(chunk.token_count for chunk in chunks)
    return IngestResponse(
        chunks=embedded_chunks,
        stats=IngestStats(
            total_budgets=len(request.budgets),
            total_chunks=len(embedded_chunks),
            total_tokens=total_tokens,
            estimated_cost_usd=estimate_cost_usd(total_tokens),
        ),
    )
