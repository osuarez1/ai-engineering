"""In-memory exact + lightweight semantic cache for LLM estimations.

Exact hits key on ``sha256(model + json.dumps(messages))``. Semantic hits
compare bag-of-words cosine similarity of the last user message against prior
entries for the same model. Disabled when ``LLM_CACHE_ENABLED`` is false.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Literal

from app.config import get_settings

CacheHitKind = Literal["none", "exact", "semantic"]

_exact_cache: dict[str, dict] = {}
_semantic_entries: list[tuple[str, str, dict]] = []


def clear_cache() -> None:
    """Reset all cached entries (used in tests)."""
    _exact_cache.clear()
    _semantic_entries.clear()


def _exact_cache_key(model: str, messages: list[dict[str, str]]) -> str:
    raw = json.dumps((model, messages), sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _last_user_message(messages: list[dict[str, str]]) -> str | None:
    for message in reversed(messages):
        if message.get("role") == "user":
            return message.get("content", "")
    return None


def _bag_of_words(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for word in text.lower().split():
        counts[word] = counts.get(word, 0) + 1
    return counts


def _cosine_similarity(left: dict[str, int], right: dict[str, int]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(left.get(word, 0) * right.get(word, 0) for word in set(left) | set(right))
    norm_left = math.sqrt(sum(value * value for value in left.values()))
    norm_right = math.sqrt(sum(value * value for value in right.values()))
    if norm_left == 0.0 or norm_right == 0.0:
        return 0.0
    return dot / (norm_left * norm_right)


def lookup(model: str, messages: list[dict[str, str]]) -> tuple[dict | None, CacheHitKind]:
    """Return a cached provider result and hit kind, or ``(None, "none")``."""
    settings = get_settings()
    if not settings.LLM_CACHE_ENABLED:
        return None, "none"

    exact_key = _exact_cache_key(model, messages)
    exact_hit = _exact_cache.get(exact_key)
    if exact_hit is not None:
        return exact_hit, "exact"

    last_user = _last_user_message(messages)
    if not last_user:
        return None, "none"

    query_bow = _bag_of_words(last_user)
    threshold = settings.SEMANTIC_CACHE_THRESHOLD
    for cached_model, cached_message, cached_result in _semantic_entries:
        if cached_model != model:
            continue
        similarity = _cosine_similarity(query_bow, _bag_of_words(cached_message))
        if similarity >= threshold:
            return cached_result, "semantic"

    return None, "none"


def store(model: str, messages: list[dict[str, str]], result: dict) -> None:
    """Persist a provider result for future exact and semantic lookups."""
    settings = get_settings()
    if not settings.LLM_CACHE_ENABLED:
        return

    exact_key = _exact_cache_key(model, messages)
    _exact_cache[exact_key] = result

    last_user = _last_user_message(messages)
    if last_user:
        _semantic_entries.append((model, last_user, result))
