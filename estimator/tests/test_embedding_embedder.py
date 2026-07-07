from unittest.mock import MagicMock, patch

import pytest
from openai import RateLimitError

from app.embedding_pipeline import embedder as embedder_module
from app.embedding_pipeline.embedder import (
    BATCH_SIZE,
    OpenAIEmbedder,
    _call_with_rate_limit_backoff,
    estimate_cost_usd,
)
from app.embedding_pipeline.schemas import Chunk


def _make_chunk(index: int) -> Chunk:
    return Chunk(
        chunk_id=f"BUD::{index}",
        text=f"component text {index}",
        metadata={"component_id": str(index)},
        token_count=10,
    )


def test_estimate_cost_usd() -> None:
    assert estimate_cost_usd(1_000_000) == 0.02
    assert estimate_cost_usd(0) == 0.0


def test_embed_one_returns_first_vector() -> None:
    mock_client = MagicMock()
    mock_client.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=[0.1, 0.2, 0.3])]
    )
    embedder = OpenAIEmbedder(client=mock_client)
    assert embedder.embed_one("hello") == [0.1, 0.2, 0.3]


def test_embed_many_empty_list() -> None:
    embedder = OpenAIEmbedder(client=MagicMock())
    assert embedder.embed_many([]) == []


def test_embed_many_batches_when_over_batch_size() -> None:
    mock_client = MagicMock()
    chunks = [_make_chunk(index) for index in range(BATCH_SIZE + 5)]
    mock_client.embeddings.create.side_effect = [
        MagicMock(data=[MagicMock(embedding=[float(i)]) for i in range(BATCH_SIZE)]),
        MagicMock(data=[MagicMock(embedding=[float(i)]) for i in range(5)]),
    ]
    embedder = OpenAIEmbedder(client=mock_client, batch_size=BATCH_SIZE)
    result = embedder.embed_many(chunks)
    assert len(result) == BATCH_SIZE + 5
    assert mock_client.embeddings.create.call_count == 2
    assert result[0].embedding == [0.0]
    assert result[-1].chunk_id == f"BUD::{BATCH_SIZE + 4}"


def test_rate_limit_backoff_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_client = MagicMock()
    mock_client.embeddings.create.side_effect = [
        RateLimitError("rate limited", response=MagicMock(), body=None),
        MagicMock(data=[MagicMock(embedding=[1.0, 2.0])]),
    ]
    sleeps: list[float] = []
    monkeypatch.setattr(embedder_module.time, "sleep", lambda seconds: sleeps.append(seconds))
    embedder = OpenAIEmbedder(client=mock_client)
    assert embedder.embed_one("retry") == [1.0, 2.0]
    assert sleeps == [1]


def test_rate_limit_backoff_exhausts_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_client = MagicMock()
    mock_client.embeddings.create.side_effect = RateLimitError(
        "rate limited", response=MagicMock(), body=None
    )
    monkeypatch.setattr(embedder_module.time, "sleep", lambda _seconds: None)
    embedder = OpenAIEmbedder(client=mock_client)
    with pytest.raises(RateLimitError):
        embedder.embed_one("fail")


def test_openai_embedder_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_settings = MagicMock()
    mock_settings.OPENAI_API_KEY = None
    monkeypatch.setattr(embedder_module, "get_settings", lambda: mock_settings)
    with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
        OpenAIEmbedder()


def test_openai_embedder_builds_client_from_settings() -> None:
    with patch("app.embedding_pipeline.embedder.OpenAI") as mock_openai:
        OpenAIEmbedder()
    mock_openai.assert_called_once_with(api_key="sk-test")


def test_unreachable_runtime_error_when_retry_loop_exits() -> None:
    with patch("builtins.enumerate", return_value=iter(())):
        with pytest.raises(RuntimeError, match="unreachable"):
            _call_with_rate_limit_backoff(lambda: [[1.0]])
