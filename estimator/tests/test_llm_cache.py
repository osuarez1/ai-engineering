from types import SimpleNamespace

import pytest

from app.services import llm_cache
from app.services.llm_cache import _cosine_similarity, clear_cache, lookup, store

MESSAGES = [
    {"role": "system", "content": "system"},
    {"role": "user", "content": "estimate crm with auth roles and csv export"},
]

SEMANTIC_MESSAGES = [
    {"role": "system", "content": "system"},
    {"role": "user", "content": "estimate crm with auth roles and csv export feature"},
]

CACHED_RESULT = {
    "estimation": "## Estimate\n\nTotal: 80 hours",
    "model": "gpt-4o-mini",
    "provider": "openai",
    "finish_reason": "stop",
    "usage": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
}


@pytest.fixture(autouse=True)
def _reset_cache() -> None:
    clear_cache()


def test_lookup_returns_none_when_cache_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        llm_cache,
        "get_settings",
        lambda: SimpleNamespace(LLM_CACHE_ENABLED=False, SEMANTIC_CACHE_THRESHOLD=0.85),
    )
    store("gpt-4o-mini", MESSAGES, CACHED_RESULT)
    hit, kind = lookup("gpt-4o-mini", MESSAGES)
    assert hit is None
    assert kind == "none"


def test_store_skips_when_cache_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        llm_cache,
        "get_settings",
        lambda: SimpleNamespace(LLM_CACHE_ENABLED=False, SEMANTIC_CACHE_THRESHOLD=0.85),
    )
    store("gpt-4o-mini", MESSAGES, CACHED_RESULT)
    hit, kind = lookup("gpt-4o-mini", MESSAGES)
    assert hit is None
    assert kind == "none"


def test_exact_cache_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        llm_cache,
        "get_settings",
        lambda: SimpleNamespace(LLM_CACHE_ENABLED=True, SEMANTIC_CACHE_THRESHOLD=0.85),
    )
    store("gpt-4o-mini", MESSAGES, CACHED_RESULT)
    hit, kind = lookup("gpt-4o-mini", MESSAGES)
    assert hit == CACHED_RESULT
    assert kind == "exact"


def test_semantic_cache_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        llm_cache,
        "get_settings",
        lambda: SimpleNamespace(LLM_CACHE_ENABLED=True, SEMANTIC_CACHE_THRESHOLD=0.85),
    )
    store("gpt-4o-mini", MESSAGES, CACHED_RESULT)
    hit, kind = lookup("gpt-4o-mini", SEMANTIC_MESSAGES)
    assert hit == CACHED_RESULT
    assert kind == "semantic"


def test_semantic_cache_misses_different_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        llm_cache,
        "get_settings",
        lambda: SimpleNamespace(LLM_CACHE_ENABLED=True, SEMANTIC_CACHE_THRESHOLD=0.85),
    )
    store("gpt-4o-mini", MESSAGES, CACHED_RESULT)
    hit, kind = lookup("claude-haiku-4-5", SEMANTIC_MESSAGES)
    assert hit is None
    assert kind == "none"


def test_semantic_cache_misses_below_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        llm_cache,
        "get_settings",
        lambda: SimpleNamespace(LLM_CACHE_ENABLED=True, SEMANTIC_CACHE_THRESHOLD=0.99),
    )
    store("gpt-4o-mini", MESSAGES, CACHED_RESULT)
    hit, kind = lookup("gpt-4o-mini", SEMANTIC_MESSAGES)
    assert hit is None
    assert kind == "none"


def test_lookup_miss_without_user_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        llm_cache,
        "get_settings",
        lambda: SimpleNamespace(LLM_CACHE_ENABLED=True, SEMANTIC_CACHE_THRESHOLD=0.85),
    )
    messages = [{"role": "system", "content": "system"}]
    hit, kind = lookup("gpt-4o-mini", messages)
    assert hit is None
    assert kind == "none"


def test_cosine_similarity_handles_empty_bag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        llm_cache,
        "get_settings",
        lambda: SimpleNamespace(LLM_CACHE_ENABLED=True, SEMANTIC_CACHE_THRESHOLD=0.85),
    )
    empty_user_messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "   "},
    ]
    store("gpt-4o-mini", empty_user_messages, CACHED_RESULT)
    hit, kind = lookup("gpt-4o-mini", empty_user_messages)
    assert hit == CACHED_RESULT
    assert kind == "exact"


def test_clear_cache_removes_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        llm_cache,
        "get_settings",
        lambda: SimpleNamespace(LLM_CACHE_ENABLED=True, SEMANTIC_CACHE_THRESHOLD=0.85),
    )
    store("gpt-4o-mini", MESSAGES, CACHED_RESULT)
    clear_cache()
    hit, kind = lookup("gpt-4o-mini", MESSAGES)
    assert hit is None
    assert kind == "none"


def test_cosine_similarity_returns_zero_for_empty_vectors() -> None:
    assert _cosine_similarity({}, {"a": 1}) == 0.0
    assert _cosine_similarity({"a": 1}, {}) == 0.0


def test_cosine_similarity_returns_zero_for_zero_norm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(llm_cache.math, "sqrt", lambda _value: 0.0)
    assert _cosine_similarity({"a": 1}, {"a": 1}) == 0.0
