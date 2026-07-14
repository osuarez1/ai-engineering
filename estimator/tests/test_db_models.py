"""Tests for the database ORM models and async session wiring."""

from collections.abc import AsyncGenerator
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import (
    EMBEDDING_DIMENSION,
    AsyncSessionLocal,
    Base as PackageBase,
    Chunk,
    Document,
    engine,
    get_session,
)
from app.db.models import Base


def test_declarative_base_registers_document_and_chunk_tables() -> None:
    """Base metadata must include documents and chunks for Alembic."""
    assert PackageBase is Base
    assert set(Base.metadata.tables) == {"documents", "chunks"}


def test_document_and_chunk_schema_columns() -> None:
    """ORM columns match the exercise schema (including renamed metadata_)."""
    document_cols = {c.name for c in Document.__table__.columns}
    chunk_cols = {c.name for c in Chunk.__table__.columns}

    assert document_cols == {"id", "source_path", "document_type", "ingested_at", "metadata"}
    assert chunk_cols == {
        "id",
        "document_id",
        "chunk_type",
        "content",
        "embedding",
        "metadata",
        "created_at",
    }
    assert Document.metadata_.property.columns[0].name == "metadata"
    assert Chunk.metadata_.property.columns[0].name == "metadata"
    assert EMBEDDING_DIMENSION == 1536
    assert Chunk.__table__.c.embedding.type.dim == EMBEDDING_DIMENSION
    assert Chunk.__table__.c.document_id.nullable is False
    assert Chunk.__table__.c.embedding.nullable is True


def test_chunk_cascade_foreign_key() -> None:
    """Deleting a document must cascade to its chunks at the FK level."""
    fk = next(iter(Chunk.__table__.c.document_id.foreign_keys))
    assert fk.column.table.name == "documents"
    assert fk.ondelete == "CASCADE"


def test_session_module_exports_engine_and_factory() -> None:
    """Async engine and sessionmaker are constructed at import time."""
    assert engine.url.drivername == "postgresql+asyncpg"
    assert AsyncSessionLocal is not None



@pytest.mark.asyncio
async def test_get_session_yields_async_session() -> None:
    """get_session yields an AsyncSession and closes it on exit."""
    mock_session = MagicMock(spec=AsyncSession)

    class _SessionCM:
        async def __aenter__(self) -> AsyncSession:
            return mock_session

        async def __aexit__(self, *args: object) -> None:
            return None

    with patch("app.db.session.AsyncSessionLocal", return_value=_SessionCM()):
        agen: AsyncGenerator[AsyncSession, None] = get_session()
        session = await agen.__anext__()
        assert session is mock_session
        await agen.aclose()
