"""Tests for POST /search — schemas, service, and HTTP contract.

HTTP cases mock AsyncSessionLocal + embedder under the real search_chunks path
(same pattern as ingest router tests).
"""

from __future__ import annotations

from collections.abc import Mapping
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import Chunk as ChunkRow
from app.embedding_pipeline.schemas import SearchRequest, SearchResponse, SearchResultItem
from app.embedding_pipeline.search_service import search_chunks

_MISSING = object()


def _row(
    *,
    chunk_id: int = 1,
    document_id: int = 2,
    distance: float = 0.2,
    content: str = "Backend JWT auth",
    metadata: object = _MISSING,
) -> MagicMock:
    row = MagicMock()
    row.id = chunk_id
    row.document_id = document_id
    row.chunk_type = "budget_component"
    row.content = content
    row.distance = distance
    row.metadata_ = {"scope": "backend"} if metadata is _MISSING else metadata
    return row


def _mock_loop(vector: list[float] | None = None) -> MagicMock:
    loop = MagicMock()
    loop.run_in_executor = AsyncMock(return_value=vector or ([0.1] * 1536))
    return loop


@pytest.mark.asyncio
async def test_search_chunks_returns_ranked_hits() -> None:
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = [
        _row(chunk_id=10, document_id=3, distance=0.11),
        _row(chunk_id=11, document_id=3, distance=0.22, content="Other"),
    ]
    session.execute = AsyncMock(return_value=result)

    with patch(
        "app.embedding_pipeline.search_service.asyncio.get_running_loop",
        return_value=_mock_loop(),
    ):
        response = await search_chunks(
            SearchRequest(query="OAuth for fintech", k=2),
            session=session,
            embedder=MagicMock(),
        )

    assert response.query == "OAuth for fintech"
    assert response.k == 2
    assert [item.chunk_id for item in response.results] == [10, 11]
    assert response.results[0].distance == pytest.approx(0.11)
    assert response.results[0].metadata == {"scope": "backend"}
    assert response.search_time_ms >= 0
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_chunks_statement_uses_cosine_distance_and_limit() -> None:
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    query_vector = [0.25] * 1536

    with patch(
        "app.embedding_pipeline.search_service.asyncio.get_running_loop",
        return_value=_mock_loop(query_vector),
    ):
        await search_chunks(
            SearchRequest(query="REST API", k=7),
            session=session,
            embedder=MagicMock(),
        )

    stmt = session.execute.await_args.args[0]
    assert stmt._limit_clause is not None
    assert stmt._limit_clause.value == 7

    distance = ChunkRow.embedding.cosine_distance(query_vector)
    expected = (
        select(
            ChunkRow.id,
            ChunkRow.document_id,
            ChunkRow.chunk_type,
            ChunkRow.content,
            ChunkRow.metadata_,
            distance.label("distance"),
        )
        .order_by(distance)
        .limit(7)
    )
    assert str(stmt) == str(expected)


@pytest.mark.asyncio
async def test_search_chunks_owns_and_closes_session() -> None:
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    session.close = AsyncMock()

    with (
        patch(
            "app.embedding_pipeline.search_service.AsyncSessionLocal",
            return_value=session,
        ),
        patch(
            "app.embedding_pipeline.search_service.asyncio.get_running_loop",
            return_value=_mock_loop([0.0] * 1536),
        ),
        patch("app.embedding_pipeline.search_service.OpenAIEmbedder"),
    ):
        response = await search_chunks(SearchRequest(query="anything"))

    assert response.results == []
    assert response.k == 5  # default
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_chunks_raises_and_closes_owned_session() -> None:
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=RuntimeError("db down"))
    session.close = AsyncMock()

    with (
        patch(
            "app.embedding_pipeline.search_service.AsyncSessionLocal",
            return_value=session,
        ),
        patch(
            "app.embedding_pipeline.search_service.asyncio.get_running_loop",
            return_value=_mock_loop(),
        ),
        patch("app.embedding_pipeline.search_service.OpenAIEmbedder"),
        pytest.raises(RuntimeError, match="db down"),
    ):
        await search_chunks(SearchRequest(query="q"))

    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_chunks_normalizes_null_and_mapping_metadata() -> None:
    class _Meta(Mapping):
        def __init__(self) -> None:
            self._data = {"tech": "fastapi"}

        def __getitem__(self, key: str) -> object:
            return self._data[key]

        def __iter__(self):
            return iter(self._data)

        def __len__(self) -> int:
            return len(self._data)

    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = [_row(metadata=None), _row(chunk_id=2, metadata=_Meta())]
    session.execute = AsyncMock(return_value=result)

    with patch(
        "app.embedding_pipeline.search_service.asyncio.get_running_loop",
        return_value=_mock_loop(),
    ):
        response = await search_chunks(
            SearchRequest(query="q", k=2),
            session=session,
            embedder=MagicMock(),
        )

    assert response.results[0].metadata == {}
    assert response.results[1].metadata == {"tech": "fastapi"}


def test_search_http_200_with_mocked_session_and_embedder(client: TestClient) -> None:
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = [
        _row(chunk_id=156, document_id=12, distance=0.231, content="JWT auth…")
    ]
    session.execute = AsyncMock(return_value=result)
    session.close = AsyncMock()

    with (
        patch(
            "app.embedding_pipeline.search_service.AsyncSessionLocal",
            return_value=session,
        ),
        patch("app.embedding_pipeline.search_service.OpenAIEmbedder"),
        patch(
            "app.embedding_pipeline.search_service.asyncio.get_running_loop",
            return_value=_mock_loop(),
        ),
    ):
        response = client.post(
            "/search",
            json={"query": "REST API with OAuth authentication for fintech sector", "k": 5},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "REST API with OAuth authentication for fintech sector"
    assert body["k"] == 5
    assert body["search_time_ms"] >= 0
    assert len(body["results"]) == 1
    assert body["results"][0]["chunk_id"] == 156
    assert body["results"][0]["document_id"] == 12
    assert body["results"][0]["chunk_type"] == "budget_component"
    assert body["results"][0]["distance"] == pytest.approx(0.231)
    session.close.assert_awaited_once()


def test_search_http_defaults_k_to_five(client: TestClient) -> None:
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    session.close = AsyncMock()

    with (
        patch(
            "app.embedding_pipeline.search_service.AsyncSessionLocal",
            return_value=session,
        ),
        patch("app.embedding_pipeline.search_service.OpenAIEmbedder"),
        patch(
            "app.embedding_pipeline.search_service.asyncio.get_running_loop",
            return_value=_mock_loop(),
        ),
    ):
        response = client.post("/search", json={"query": "integration with external system"})

    assert response.status_code == 200
    assert response.json()["k"] == 5
    stmt = session.execute.await_args.args[0]
    assert stmt._limit_clause.value == 5


def test_search_http_returns_500_when_service_fails(client: TestClient) -> None:
    with patch(
        "app.embedding_pipeline.search_router.search_chunks",
        new_callable=AsyncMock,
        side_effect=RuntimeError("db down"),
    ):
        response = client.post("/search", json={"query": "REST API"})

    assert response.status_code == 500
    assert response.json()["detail"] == "Semantic search failed"


def test_search_http_returns_422_for_invalid_payloads(client: TestClient) -> None:
    assert client.post("/search", json={"query": "", "k": 5}).status_code == 422
    assert client.post("/search", json={"query": "ok", "k": 0}).status_code == 422
    assert client.post("/search", json={"query": "ok", "k": 51}).status_code == 422
    assert client.post("/search", json={}).status_code == 422


def test_search_http_returns_mocked_service_payload(client: TestClient) -> None:
    expected = SearchResponse(
        query="REST API",
        k=5,
        search_time_ms=12,
        results=[
            SearchResultItem(
                chunk_id=1,
                document_id=2,
                chunk_type="budget_component",
                content="text",
                distance=0.2,
                metadata={},
            )
        ],
    )
    with patch(
        "app.embedding_pipeline.search_router.search_chunks",
        new_callable=AsyncMock,
        return_value=expected,
    ):
        response = client.post("/search", json={"query": "REST API", "k": 5})

    assert response.status_code == 200
    assert response.json() == expected.model_dump()
