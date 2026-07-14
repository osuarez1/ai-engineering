"""Embedding ingestion API router."""

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.embedding_pipeline.ingest_service import (
    DocumentAlreadyIngestedError,
    ingest_document,
)
from app.embedding_pipeline.schemas import IngestRequest, IngestResponse

log = structlog.get_logger()

router = APIRouter(prefix="/embeddings", tags=["embeddings"])


@router.post("/ingest", response_model=IngestResponse)
async def ingest_embeddings(
    request: IngestRequest,
) -> IngestResponse | JSONResponse:
    """Chunk, embed, and persist one document in a single DB transaction."""
    try:
        return await ingest_document(request)
    except DocumentAlreadyIngestedError as exc:
        return JSONResponse(
            status_code=409,
            content={
                "detail": "Document already ingested",
                "document_id": exc.document_id,
            },
        )
    except Exception as exc:
        log.error("embedding_ingest_error", error=str(exc))
        raise HTTPException(status_code=500, detail="Embedding ingestion failed") from exc
