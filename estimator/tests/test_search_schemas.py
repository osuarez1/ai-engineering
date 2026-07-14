"""Unit tests for semantic search request/response schemas."""

import pytest
from pydantic import ValidationError

from app.embedding_pipeline.schemas import SearchRequest, SearchResponse, SearchResultItem


def test_search_request_defaults_k_to_five() -> None:
    request = SearchRequest(query="REST API with OAuth")
    assert request.k == 5


def test_search_request_rejects_empty_query_and_out_of_range_k() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(query="", k=5)
    with pytest.raises(ValidationError):
        SearchRequest(query="ok", k=0)
    with pytest.raises(ValidationError):
        SearchRequest(query="ok", k=51)


def test_search_response_shape() -> None:
    response = SearchResponse(
        query="secure backend",
        k=5,
        search_time_ms=87,
        results=[
            SearchResultItem(
                chunk_id=156,
                document_id=12,
                chunk_type="budget_component",
                content="Backend service with JWT...",
                distance=0.231,
                metadata={"scope": "backend"},
            )
        ],
    )
    assert response.model_dump() == {
        "query": "secure backend",
        "k": 5,
        "search_time_ms": 87,
        "results": [
            {
                "chunk_id": 156,
                "document_id": 12,
                "chunk_type": "budget_component",
                "content": "Backend service with JWT...",
                "distance": 0.231,
                "metadata": {"scope": "backend"},
            }
        ],
    }
