"""Tests for ingest request/response schemas and router wiring."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.embedding_pipeline.schemas import (
    DocumentAlreadyIngestedDetail,
    IngestRequest,
    IngestResponse,
)


def test_ingest_request_accepts_source_path_and_budget_content() -> None:
    sample = json.loads(Path("data/budgets_sample.json").read_text())
    request = IngestRequest(
        source_path="data/budgets_sample.json#BUD-2024-014",
        document_type="historical_budget",
        content=sample[0],
    )
    assert request.source_path.endswith("BUD-2024-014")
    assert request.document_type == "historical_budget"
    assert request.content.budget_id == "BUD-2024-014"


def test_ingest_request_rejects_empty_source_path() -> None:
    sample = json.loads(Path("data/budgets_sample.json").read_text())
    with pytest.raises(ValidationError):
        IngestRequest(
            source_path="",
            document_type="historical_budget",
            content=sample[0],
        )


def test_ingest_response_and_conflict_detail_shape() -> None:
    response = IngestResponse(
        document_id=42,
        chunks_created=17,
        embedding_dimension=1536,
        ingestion_time_ms=1240,
    )
    assert response.model_dump() == {
        "document_id": 42,
        "chunks_created": 17,
        "embedding_dimension": 1536,
        "ingestion_time_ms": 1240,
    }

    conflict = DocumentAlreadyIngestedDetail(document_id=42)
    assert conflict.detail == "Document already ingested"
    assert conflict.document_id == 42


def test_ingest_endpoint_validates_new_contract(client: TestClient) -> None:
    response = client.post("/embeddings/ingest", json={"budgets": []})
    assert response.status_code == 422


def test_ingest_endpoint_delegates_to_service(client: TestClient) -> None:
    sample = json.loads(Path("data/budgets_sample.json").read_text())
    payload = {
        "source_path": "data/budgets_sample.json#BUD-2024-014",
        "document_type": "historical_budget",
        "content": sample[0],
    }
    expected = IngestResponse(
        document_id=7,
        chunks_created=4,
        embedding_dimension=1536,
        ingestion_time_ms=12,
    )
    with patch(
        "app.embedding_pipeline.router.ingest_document",
        new_callable=AsyncMock,
        return_value=expected,
    ) as mock_ingest:
        response = client.post("/embeddings/ingest", json=payload)

    assert response.status_code == 200
    assert response.json() == expected.model_dump()
    mock_ingest.assert_awaited_once()


def test_ingest_endpoint_returns_409_for_duplicate(client: TestClient) -> None:
    from app.embedding_pipeline.ingest_service import DocumentAlreadyIngestedError

    sample = json.loads(Path("data/budgets_sample.json").read_text())
    payload = {
        "source_path": "data/budgets_sample.json#BUD-2024-014",
        "document_type": "historical_budget",
        "content": sample[0],
    }
    with patch(
        "app.embedding_pipeline.router.ingest_document",
        new_callable=AsyncMock,
        side_effect=DocumentAlreadyIngestedError(42),
    ):
        response = client.post("/embeddings/ingest", json=payload)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Document already ingested",
        "document_id": 42,
    }


def test_ingest_endpoint_returns_500_on_failure(client: TestClient) -> None:
    sample = json.loads(Path("data/budgets_sample.json").read_text())
    payload = {
        "source_path": "data/budgets_sample.json#BUD-2024-014",
        "document_type": "historical_budget",
        "content": sample[0],
    }
    with patch(
        "app.embedding_pipeline.router.ingest_document",
        new_callable=AsyncMock,
        side_effect=RuntimeError("boom"),
    ):
        response = client.post("/embeddings/ingest", json=payload)

    assert response.status_code == 500
    assert response.json()["detail"] == "Embedding ingestion failed"
