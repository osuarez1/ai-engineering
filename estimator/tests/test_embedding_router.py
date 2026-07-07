import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.embedding_pipeline.schemas import EmbedManyResult, EmbeddedChunk


def _embedded_chunk(chunk_id: str, token_count: int) -> EmbeddedChunk:
    return EmbeddedChunk(
        chunk_id=chunk_id,
        text="chunk text",
        metadata={"component_id": "AUTH-001"},
        token_count=token_count,
        embedding=[0.1, 0.2],
    )


def test_ingest_returns_embedded_chunks(client: TestClient) -> None:
    sample = json.loads(Path("data/budgets_sample.json").read_text())
    payload = {"budgets": [sample[0]]}

    with patch("app.embedding_pipeline.router.OpenAIEmbedder") as mock_embedder_cls:
        mock_embedder_cls.return_value.embed_many.return_value = EmbedManyResult(
            chunks=[
                _embedded_chunk("BUD-2024-014::AUTH-001", 99),
                _embedded_chunk("BUD-2024-014::API-002", 88),
                _embedded_chunk("BUD-2024-014::PSD2-003", 77),
                _embedded_chunk("BUD-2024-014::MOB-004", 66),
            ],
            total_tokens=330,
            estimated_cost_usd=0.0000066,
        )
        response = client.post("/embeddings/ingest", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["stats"]["total_budgets"] == 1
    assert body["stats"]["total_chunks"] == 4
    assert body["stats"]["total_tokens"] == 330
    assert body["stats"]["estimated_cost_usd"] == 0.0000066
    assert len(body["chunks"]) == 4


def test_ingest_returns_422_for_invalid_payload(client: TestClient) -> None:
    response = client.post("/embeddings/ingest", json={"budgets": []})
    assert response.status_code == 422


def test_ingest_returns_500_when_embedding_fails(client: TestClient) -> None:
    sample = json.loads(Path("data/budgets_sample.json").read_text())
    payload = {"budgets": [sample[0]]}

    with patch("app.embedding_pipeline.router.OpenAIEmbedder") as mock_embedder_cls:
        mock_embedder_cls.return_value.embed_many.side_effect = RuntimeError("api down")
        response = client.post("/embeddings/ingest", json=payload)

    assert response.status_code == 500
    assert response.json()["detail"] == "Embedding ingestion failed"
