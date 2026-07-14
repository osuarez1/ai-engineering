"""Tests for ingest request/response schema validation and router stub."""

import json
from pathlib import Path

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


def test_ingest_endpoint_stub_returns_501_until_persistence(client: TestClient) -> None:
    sample = json.loads(Path("data/budgets_sample.json").read_text())
    payload = {
        "source_path": "data/budgets_sample.json#BUD-2024-014",
        "document_type": "historical_budget",
        "content": sample[0],
    }
    response = client.post("/embeddings/ingest", json=payload)
    assert response.status_code == 501
    assert response.json()["detail"] == "Ingest persistence not implemented yet"
