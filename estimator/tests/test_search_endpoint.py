"""Unit/HTTP smoke tests for POST /search (full suite expands in search-tests)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.embedding_pipeline.schemas import SearchRequest, SearchResponse, SearchResultItem
from app.embedding_pipeline.search_service import search_chunks


_MISSING = object()


def _row(
    *,
    chunk_id: int = 1,
    document_id: int = 2,
    distance: float = 0.2,
    metadata: object = _MISSING,
) -> MagicMock:
    row = MagicMock()
    row.id = chunk_id
    row.document_id = document_id
    row.chunk_type = "budget_component"
    row.content = "Backend JWT auth"
    row.distance = distance
    row.metadata_ = {"scope": "backend"} if metadata is _MISSING else metadata
    return row


@pytest.mark.asyncio
async def test_search_chunks_orders_by_cosine_distance() -> None:
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = [_row(chunk_id=10, distance=0.11)]
    session.execute = AsyncMock(return_value=result)
    session.close = AsyncMock()

    embedder = MagicMock()
    loop = MagicMock()
    loop.run_in_executor = AsyncMock(return_value=[0.1] * 1536)

    with patch(
        "app.embedding_pipeline.search_service.asyncio.get_running_loop",
        return_value=loop,
    ):
        response = await search_chunks(
            SearchRequest(query="OAuth for fintech", k=3),
            session=session,
            embedder=embedder,
        )

    assert response.query == "OAuth for fintech"
    assert response.k == 3
    assert len(response.results) == 1
    assert response.results[0].chunk_id == 10
    assert response.results[0].distance == pytest.approx(0.11)
    assert response.results[0].metadata == {"scope": "backend"}
    session.execute.assert_awaited_once()
    session.close.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_chunks_owns_and_closes_session() -> None:
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = []
    session.execute = AsyncMock(return_value=result)
    session.close = AsyncMock()

    loop = MagicMock()
    loop.run_in_executor = AsyncMock(return_value=[0.0] * 1536)

    with (
        patch(
            "app.embedding_pipeline.search_service.AsyncSessionLocal",
            return_value=session,
        ),
        patch(
            "app.embedding_pipeline.search_service.asyncio.get_running_loop",
            return_value=loop,
        ),
        patch("app.embedding_pipeline.search_service.OpenAIEmbedder"),
    ):
        response = await search_chunks(SearchRequest(query="anything"))

    assert response.results == []
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_chunks_normalizes_null_metadata() -> None:
    session = AsyncMock()
    result = MagicMock()
    result.all.return_value = [_row(metadata=None)]
    session.execute = AsyncMock(return_value=result)

    loop = MagicMock()
    loop.run_in_executor = AsyncMock(return_value=[0.0] * 1536)

    with patch(
        "app.embedding_pipeline.search_service.asyncio.get_running_loop",
        return_value=loop,
    ):
        response = await search_chunks(
            SearchRequest(query="q"),
            session=session,
            embedder=MagicMock(),
        )

    assert response.results[0].metadata == {}


def test_search_endpoint_returns_200(client: TestClient) -> None:
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


def test_search_endpoint_returns_500_on_failure(client: TestClient) -> None:
    with patch(
        "app.embedding_pipeline.search_router.search_chunks",
        new_callable=AsyncMock,
        side_effect=RuntimeError("db down"),
    ):
        response = client.post("/search", json={"query": "REST API"})

    assert response.status_code == 500
    assert response.json()["detail"] == "Semantic search failed"


def test_search_endpoint_returns_422_for_empty_query(client: TestClient) -> None:
    response = client.post("/search", json={"query": "", "k": 5})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_chunks_raises_and_closes_owned_session() -> None:
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=RuntimeError("db down"))
    session.close = AsyncMock()
    loop = MagicMock()
    loop.run_in_executor = AsyncMock(return_value=[0.0] * 1536)

    with (
        patch(
            "app.embedding_pipeline.search_service.AsyncSessionLocal",
            return_value=session,
        ),
        patch(
            "app.embedding_pipeline.search_service.asyncio.get_running_loop",
            return_value=loop,
        ),
        patch("app.embedding_pipeline.search_service.OpenAIEmbedder"),
        pytest.raises(RuntimeError, match="db down"),
    ):
        await search_chunks(SearchRequest(query="q"))

    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_chunks_accepts_mapping_metadata() -> None:
    from collections.abc import Mapping

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
    result.all.return_value = [_row(metadata=_Meta())]
    session.execute = AsyncMock(return_value=result)
    loop = MagicMock()
    loop.run_in_executor = AsyncMock(return_value=[0.0] * 1536)

    with patch(
        "app.embedding_pipeline.search_service.asyncio.get_running_loop",
        return_value=loop,
    ):
        response = await search_chunks(
            SearchRequest(query="q"),
            session=session,
            embedder=MagicMock(),
        )

    assert response.results[0].metadata == {"tech": "fastapi"}
