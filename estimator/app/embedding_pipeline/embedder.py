"""OpenAI embedding client for the ingestion pipeline."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog
from openai import OpenAI, RateLimitError

from app.config import get_settings
from app.embedding_pipeline.schemas import Chunk, EmbeddedChunk

if TYPE_CHECKING:
    from openai import OpenAI as OpenAIClient

log = structlog.get_logger()

# OpenAI text-embedding-3-small input pricing (USD per 1M tokens) as of Session 07.
PRICE_PER_1M_TOKENS_USD = 0.02
EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100
RATE_LIMIT_BACKOFF_SECONDS = (1, 2, 4)


def estimate_cost_usd(total_tokens: int) -> float:
    """Estimate embedding API cost from total input tokens."""
    return total_tokens * PRICE_PER_1M_TOKENS_USD / 1_000_000


class OpenAIEmbedder:
    """Generate embeddings via OpenAI's embeddings API."""

    def __init__(self, client: OpenAIClient | None = None, batch_size: int = BATCH_SIZE) -> None:
        if client is not None:
            self._client = client
        else:
            settings = get_settings()
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY is required for embeddings")
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self._batch_size = batch_size

    def embed_one(self, text: str) -> list[float]:
        """Embed a single text and return its vector."""
        response = self._create_embeddings([text])
        return response[0]

    def embed_many(self, chunks: list[Chunk]) -> list[EmbeddedChunk]:
        """Embed chunks in batches and return vectorized results."""
        if not chunks:
            return []

        embedded: list[EmbeddedChunk] = []
        for start in range(0, len(chunks), self._batch_size):
            batch = chunks[start : start + self._batch_size]
            vectors = self._create_embeddings([chunk.text for chunk in batch])
            batch_tokens = sum(chunk.token_count for chunk in batch)
            embedded.extend(
                EmbeddedChunk(
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    metadata=chunk.metadata,
                    token_count=chunk.token_count,
                    embedding=vector,
                )
                for chunk, vector in zip(batch, vectors, strict=True)
            )
            log.info(
                "embedding_batch_processed",
                model=EMBEDDING_MODEL,
                chunks_processed=len(batch),
                token_total=batch_tokens,
                latency_ms=round(self._last_batch_latency_ms, 1),
            )
        return embedded

    def _create_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Call the embeddings API with rate-limit backoff."""
        started = time.perf_counter()

        def _call() -> list[list[float]]:
            response = self._client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts,
            )
            return [item.embedding for item in response.data]

        vectors = _call_with_rate_limit_backoff(_call)
        self._last_batch_latency_ms = (time.perf_counter() - started) * 1000
        return vectors


def _call_with_rate_limit_backoff(callable_fn) -> list[list[float]]:
    """Retry on RateLimitError with 1s, 2s, and 4s delays."""
    for attempt, delay in enumerate((*RATE_LIMIT_BACKOFF_SECONDS, None)):
        try:
            return callable_fn()
        except RateLimitError:
            if delay is None:
                raise
            time.sleep(delay)
            log.warning("embedding_rate_limited", retry_attempt=attempt + 1, delay_seconds=delay)
    raise RuntimeError("unreachable")
