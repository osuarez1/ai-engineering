"""Embedding ingestion API router."""

import structlog
from fastapi import APIRouter, HTTPException

from app.embedding_pipeline.chunker import JSONStructuralChunker
from app.embedding_pipeline.embedder import OpenAIEmbedder
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
        embed_result = embedder.embed_many(chunks)
    except Exception as exc:
        log.error("embedding_ingest_error", error=str(exc))
        raise HTTPException(status_code=500, detail="Embedding ingestion failed") from exc

    return IngestResponse(
        chunks=embed_result.chunks,
        stats=IngestStats(
            total_budgets=len(request.budgets),
            total_chunks=len(embed_result.chunks),
            total_tokens=embed_result.total_tokens,
            estimated_cost_usd=embed_result.estimated_cost_usd,
        ),
    )
