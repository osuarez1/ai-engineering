"""HTTP tests for POST /embeddings/ingest (persisted contract).

Mocks the DB session and embedder under the real ingest_document path so the
router is exercised end-to-end for 200, 409, and failure+rollback.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.db.models import Document
from app.embedding_pipeline.schemas import EmbedManyResult, EmbeddedChunk, IngestResponse


def _sample_payload() -> dict:
    sample = json.loads(Path("data/budgets_sample.json").read_text())
    return {
        "source_path": "data/budgets_sample.json#BUD-2024-014",
        "document_type": "historical_budget",
        "content": sample[0],
    }


def _embedded_chunks_for_budget(budget: dict) -> list[EmbeddedChunk]:
    chunks: list[EmbeddedChunk] = []
    for component in budget["components"]:
        chunks.append(
            EmbeddedChunk(
                chunk_id=f"{budget['budget_id']}::{component['component_id']}",
                text=f"chunk for {component['name']}",
                metadata={
                    "budget_id": budget["budget_id"],
                    "component_id": component["component_id"],
                },
                token_count=12,
                embedding=[0.1] * 1536,
            )
        )
    return chunks


def _mock_session(*, existing_id: int | None = None) -> AsyncMock:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=existing_id)
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()

    def _assign_id(obj: object) -> None:
        if isinstance(obj, Document):
            obj.id = 7

    session.add.side_effect = _assign_id
    return session


def _mock_loop(result: object) -> MagicMock:
    loop = MagicMock()
    loop.run_in_executor = AsyncMock(return_value=result)
    return loop


def test_ingest_returns_200_with_persistence_metrics(client: TestClient) -> None:
    payload = _sample_payload()
    embedded = _embedded_chunks_for_budget(payload["content"])
    embed_result = EmbedManyResult(
        chunks=embedded,
        total_tokens=sum(c.token_count for c in embedded),
        estimated_cost_usd=0.0,
    )
    session = _mock_session()

    with (
        patch(
            "app.embedding_pipeline.ingest_service.AsyncSessionLocal",
            return_value=session,
        ),
        patch(
            "app.embedding_pipeline.ingest_service.OpenAIEmbedder",
        ) as mock_embedder_cls,
        patch(
            "app.embedding_pipeline.ingest_service.asyncio.get_running_loop",
            return_value=_mock_loop(embed_result),
        ),
    ):
        mock_embedder_cls.return_value.embed_many.return_value = embed_result
        response = client.post("/embeddings/ingest", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body == IngestResponse(
        document_id=7,
        chunks_created=len(embedded),
        embedding_dimension=1536,
        ingestion_time_ms=body["ingestion_time_ms"],
    ).model_dump()
    assert body["chunks_created"] == len(payload["content"]["components"])
    session.add_all.assert_called_once()
    assert len(session.add_all.call_args.args[0]) == len(embedded)
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()
    session.close.assert_awaited_once()


def test_ingest_returns_409_when_source_path_exists(client: TestClient) -> None:
    payload = _sample_payload()
    session = _mock_session(existing_id=42)

    with patch(
        "app.embedding_pipeline.ingest_service.AsyncSessionLocal",
        return_value=session,
    ):
        response = client.post("/embeddings/ingest", json=payload)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Document already ingested",
        "document_id": 42,
    }
    session.commit.assert_not_called()
    session.add_all.assert_not_called()
    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()


def test_ingest_returns_500_and_rolls_back_when_embed_fails(client: TestClient) -> None:
    payload = _sample_payload()
    session = _mock_session()
    failing_loop = MagicMock()
    failing_loop.run_in_executor = AsyncMock(side_effect=RuntimeError("api down"))

    with (
        patch(
            "app.embedding_pipeline.ingest_service.AsyncSessionLocal",
            return_value=session,
        ),
        patch(
            "app.embedding_pipeline.ingest_service.OpenAIEmbedder",
        ),
        patch(
            "app.embedding_pipeline.ingest_service.asyncio.get_running_loop",
            return_value=failing_loop,
        ),
    ):
        response = client.post("/embeddings/ingest", json=payload)

    assert response.status_code == 500
    assert response.json()["detail"] == "Embedding ingestion failed"
    session.commit.assert_not_awaited()
    session.rollback.assert_awaited()
    session.close.assert_awaited_once()


def test_ingest_returns_422_for_legacy_budgets_payload(client: TestClient) -> None:
    response = client.post("/embeddings/ingest", json={"budgets": []})
    assert response.status_code == 422


def test_ingest_returns_422_when_content_missing(client: TestClient) -> None:
    response = client.post(
        "/embeddings/ingest",
        json={
            "source_path": "data/budgets_sample.json#BUD-2024-014",
            "document_type": "historical_budget",
        },
    )
    assert response.status_code == 422
