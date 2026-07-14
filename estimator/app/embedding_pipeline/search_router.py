"""Semantic search API router (``POST /search``)."""

import structlog
from fastapi import APIRouter, HTTPException

from app.embedding_pipeline.schemas import SearchRequest, SearchResponse
from app.embedding_pipeline.search_service import search_chunks

log = structlog.get_logger()

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """Return the k nearest chunks to the query by cosine distance."""
    try:
        return await search_chunks(request)
    except Exception as exc:
        log.error("search_endpoint_error", error=str(exc))
        raise HTTPException(status_code=500, detail="Semantic search failed") from exc
