"""Unit tests for transactional ingest_document."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models import Document
from app.embedding_pipeline.ingest_service import (
    DocumentAlreadyIngestedError,
    ingest_document,
)
from app.embedding_pipeline.schemas import (
    Budget,
    BudgetComponent,
    ClientMetadata,
    EmbedManyResult,
    EmbeddedChunk,
    IngestRequest,
)


def _sample_request() -> IngestRequest:
    return IngestRequest(
        source_path="data/budgets_sample.json#BUD-TEST",
        document_type="historical_budget",
        content=Budget(
            budget_id="BUD-TEST",
            client_metadata=ClientMetadata(name="Acme", sector="finance", country="ES"),
            project_summary="API with OAuth",
            main_technology="fastapi",
            year=2024,
            total_estimated_hours=100,
            components=[
                BudgetComponent(
                    component_id="AUTH-001",
                    name="Auth",
                    description="OAuth backend",
                    tech_stack=["fastapi"],
                    estimated_hours=40,
                    complexity="high",
                )
            ],
        ),
    )


def _embedded(text: str = "chunk text") -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk_id="BUD-TEST::AUTH-001",
        text=text,
        metadata={"budget_id": "BUD-TEST", "component_id": "AUTH-001"},
        token_count=10,
        embedding=[0.1] * 1536,
    )


def _mock_loop(result: object) -> MagicMock:
    loop = MagicMock()
    loop.run_in_executor = AsyncMock(return_value=result)
    return loop


@pytest.mark.asyncio
async def test_ingest_document_persists_chunks_and_commits() -> None:
    request = _sample_request()
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=None)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()

    def _capture_document(obj: object) -> None:
        if isinstance(obj, Document):
            obj.id = 99

    session.add.side_effect = _capture_document

    chunker = MagicMock()
    chunker.chunk.return_value = [MagicMock()]
    embedder = MagicMock()
    embed_result = EmbedManyResult(
        chunks=[_embedded()],
        total_tokens=10,
        estimated_cost_usd=0.0,
    )
    embedder.embed_many.return_value = embed_result

    with patch(
        "app.embedding_pipeline.ingest_service.asyncio.get_running_loop",
        return_value=_mock_loop(embed_result),
    ):
        result = await ingest_document(
            request,
            session=session,
            chunker=chunker,
            embedder=embedder,
        )

    assert result.document_id == 99
    assert result.chunks_created == 1
    assert result.embedding_dimension == 1536
    session.add_all.assert_called_once()
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    session.close.assert_not_awaited()


@pytest.mark.asyncio
async def test_ingest_document_raises_on_duplicate_source_path() -> None:
    request = _sample_request()
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=42)
    session.rollback = AsyncMock()
    session.close = AsyncMock()

    with pytest.raises(DocumentAlreadyIngestedError) as exc_info:
        await ingest_document(request, session=session)

    assert exc_info.value.document_id == 42
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_document_rolls_back_when_embed_fails() -> None:
    request = _sample_request()
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=None)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.add = MagicMock(side_effect=lambda obj: setattr(obj, "id", 1))
    session.add_all = MagicMock()

    chunker = MagicMock()
    chunker.chunk.return_value = [MagicMock()]
    embedder = MagicMock()
    failing_loop = MagicMock()
    failing_loop.run_in_executor = AsyncMock(side_effect=RuntimeError("api down"))

    with patch(
        "app.embedding_pipeline.ingest_service.asyncio.get_running_loop",
        return_value=failing_loop,
    ):
        with pytest.raises(RuntimeError, match="api down"):
            await ingest_document(
                request,
                session=session,
                chunker=chunker,
                embedder=embedder,
            )

    session.rollback.assert_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_ingest_document_owns_session_rolls_back_on_duplicate() -> None:
    request = _sample_request()
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=7)
    session.rollback = AsyncMock()
    session.close = AsyncMock()

    with patch(
        "app.embedding_pipeline.ingest_service.AsyncSessionLocal",
        return_value=session,
    ):
        with pytest.raises(DocumentAlreadyIngestedError) as exc_info:
            await ingest_document(request)

    assert exc_info.value.document_id == 7
    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()

    request = _sample_request()
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=None)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.add = MagicMock(side_effect=lambda obj: setattr(obj, "id", 5))
    session.add_all = MagicMock()

    embed_result = EmbedManyResult(
        chunks=[_embedded()],
        total_tokens=10,
        estimated_cost_usd=0.0,
    )
    chunker = MagicMock()
    chunker.chunk.return_value = [MagicMock()]
    embedder = MagicMock()
    embedder.embed_many.return_value = embed_result

    with (
        patch(
            "app.embedding_pipeline.ingest_service.AsyncSessionLocal",
            return_value=session,
        ),
        patch(
            "app.embedding_pipeline.ingest_service.asyncio.get_running_loop",
            return_value=_mock_loop(embed_result),
        ),
    ):
        result = await ingest_document(request, chunker=chunker, embedder=embedder)

    assert result.document_id == 5
    session.close.assert_awaited_once()
