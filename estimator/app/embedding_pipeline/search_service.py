"""Semantic search over persisted chunk embeddings (cosine distance)."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chunk as ChunkRow
from app.db.session import AsyncSessionLocal
from app.embedding_pipeline.embedder import OpenAIEmbedder
from app.embedding_pipeline.schemas import SearchRequest, SearchResponse, SearchResultItem

log = structlog.get_logger()


async def search_chunks(
    request: SearchRequest,
    *,
    session: AsyncSession | None = None,
    embedder: OpenAIEmbedder | None = None,
) -> SearchResponse:
    """Embed the query and return the k nearest chunks by cosine distance.

    Uses sequential scan (no vector index yet) — intentional Session 08 baseline.
    """
    owns_session = session is None
    db = session or AsyncSessionLocal()
    embedder = embedder or OpenAIEmbedder()
    started = time.perf_counter()

    try:
        loop = asyncio.get_running_loop()
        query_vector = await loop.run_in_executor(None, embedder.embed_one, request.query)

        distance = ChunkRow.embedding.cosine_distance(query_vector)
        stmt = (
            select(
                ChunkRow.id,
                ChunkRow.document_id,
                ChunkRow.chunk_type,
                ChunkRow.content,
                ChunkRow.metadata_,
                distance.label("distance"),
            )
            .order_by(distance)
            .limit(request.k)
        )
        result = await db.execute(stmt)
        rows = result.all()

        results = [
            SearchResultItem(
                chunk_id=int(row.id),
                document_id=int(row.document_id),
                chunk_type=row.chunk_type,
                content=row.content,
                distance=float(row.distance),
                metadata=_as_metadata(row.metadata_),
            )
            for row in rows
        ]
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        log.info(
            "semantic_search_completed",
            query_length=len(request.query),
            k=request.k,
            hits=len(results),
            search_time_ms=elapsed_ms,
        )
        return SearchResponse(
            query=request.query,
            k=request.k,
            search_time_ms=elapsed_ms,
            results=results,
        )
    except Exception:
        log.error("semantic_search_failed", query=request.query, exc_info=True)
        raise
    finally:
        if owns_session:
            await db.close()


def _as_metadata(value: Any) -> dict[str, Any]:
    """Normalize JSONB metadata to a plain dict for the response schema."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    return dict(value)
