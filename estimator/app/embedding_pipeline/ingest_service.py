"""Transactional document ingestion into Postgres + pgvector."""

from __future__ import annotations

import asyncio
import time
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EMBEDDING_DIMENSION, Document
from app.db.models import Chunk as ChunkRow
from app.db.session import AsyncSessionLocal
from app.embedding_pipeline.chunker import JSONStructuralChunker
from app.embedding_pipeline.embedder import OpenAIEmbedder
from app.embedding_pipeline.schemas import IngestRequest, IngestResponse

log = structlog.get_logger()

CHUNK_TYPE_BUDGET_COMPONENT = "budget_component"


class DocumentAlreadyIngestedError(Exception):
    """Raised when a document with the same source_path already exists."""

    def __init__(self, document_id: int) -> None:
        self.document_id = document_id
        super().__init__(f"Document already ingested: id={document_id}")


def _document_metadata(request: IngestRequest) -> dict[str, Any]:
    """Stable document-level metadata derived from the budget payload."""
    budget = request.content
    return {
        "budget_id": budget.budget_id,
        "sector": budget.client_metadata.sector,
        "country": budget.client_metadata.country,
        "year": budget.year,
        "main_technology": budget.main_technology,
        "total_estimated_hours": budget.total_estimated_hours,
    }


async def ingest_document(
    request: IngestRequest,
    *,
    session: AsyncSession | None = None,
    chunker: JSONStructuralChunker | None = None,
    embedder: OpenAIEmbedder | None = None,
) -> IngestResponse:
    """Persist one document and its embedded chunks in a single transaction.

    1. Reject duplicate ``source_path`` (caller maps to HTTP 409).
    2. Insert ``documents`` row.
    3. Structurally chunk the budget JSON.
    4. Batch-embed via ``OpenAIEmbedder.embed_many`` (sync, off event loop).
    5. ``add_all`` chunk rows and commit.

    A failure after insert and before commit rolls back so no orphan document remains.
    """
    owns_session = session is None
    db = session or AsyncSessionLocal()
    chunker = chunker or JSONStructuralChunker()
    embedder = embedder or OpenAIEmbedder()
    started = time.perf_counter()

    try:
        existing_id = await db.scalar(
            select(Document.id).where(Document.source_path == request.source_path)
        )
        if existing_id is not None:
            raise DocumentAlreadyIngestedError(int(existing_id))

        document = Document(
            source_path=request.source_path,
            document_type=request.document_type,
            metadata_=_document_metadata(request),
        )
        db.add(document)
        await db.flush()

        pipeline_chunks = chunker.chunk([request.content])
        loop = asyncio.get_running_loop()
        embed_result = await loop.run_in_executor(None, embedder.embed_many, pipeline_chunks)

        chunk_rows = [
            ChunkRow(
                document_id=document.id,
                chunk_type=CHUNK_TYPE_BUDGET_COMPONENT,
                content=embedded.text,
                embedding=embedded.embedding,
                metadata_=dict(embedded.metadata),
            )
            for embedded in embed_result.chunks
        ]
        db.add_all(chunk_rows)
        await db.commit()

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        log.info(
            "document_ingested",
            document_id=document.id,
            chunks_created=len(chunk_rows),
            source_path=request.source_path,
            ingestion_time_ms=elapsed_ms,
        )
        return IngestResponse(
            document_id=document.id,
            chunks_created=len(chunk_rows),
            embedding_dimension=EMBEDDING_DIMENSION,
            ingestion_time_ms=elapsed_ms,
        )
    except DocumentAlreadyIngestedError:
        if owns_session:
            await db.rollback()
        raise
    except Exception:
        await db.rollback()
        log.error(
            "document_ingest_failed",
            source_path=request.source_path,
            exc_info=True,
        )
        raise
    finally:
        if owns_session:
            await db.close()
