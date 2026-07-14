"""Run five representative POST /search queries and print top-5 hits.

Usage (API must be running with an ingested corpus)::

    uv run python query_examples.py
    docker compose exec estimator python query_examples.py

Set ``API_BASE_URL`` to override the default ``http://localhost:8000``.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_K = 5
CONTENT_PREVIEW_CHARS = 120

# Five archetypes adapted to the finance / ecommerce / healthcare / industrial corpus.
QUERIES: list[tuple[str, str]] = [
    (
        "1. Known direct component",
        "REST API development with JWT authentication for financial sector",
    ),
    (
        "2. Semantic reformulation",
        "secure backend service with token-based access control for banking applications",
    ),
    (
        "3. Different domain",
        "mobile application for restaurant reservations",
    ),
    (
        "4. Ambiguous query",
        "integration with external system",
    ),
    (
        "5. Very specific query",
        "migration from monolith to microservices architecture using Kubernetes",
    ),
]


def search(
    query: str,
    *,
    k: int = DEFAULT_K,
    base_url: str = DEFAULT_BASE_URL,
    opener: urllib.request.OpenerDirector | None = None,
) -> dict[str, Any]:
    """POST ``/search`` and return the parsed JSON body."""
    payload = {"query": query, "k": k}
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/search",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    open_fn = opener.open if opener is not None else urllib.request.urlopen
    try:
        with open_fn(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            detail = json.loads(raw) if raw else {"detail": exc.reason}
        except json.JSONDecodeError:
            detail = {"detail": raw}
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc


def preview_content(content: str, limit: int = CONTENT_PREVIEW_CHARS) -> str:
    """Truncate content for terminal-friendly display."""
    text = " ".join(content.split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def format_results(label: str, query: str, body: dict[str, Any]) -> str:
    """Render one archetype block with top-k hits."""
    lines = [
        "=" * 72,
        label,
        f"Query: {query}",
        f"search_time_ms: {body.get('search_time_ms', '?')}",
        "-" * 72,
    ]
    results = body.get("results") or []
    if not results:
        lines.append("(no results)")
    for index, hit in enumerate(results, start=1):
        distance = float(hit.get("distance", 0.0))
        lines.append(
            f"{index}. chunk_id={hit.get('chunk_id')}  "
            f"distance={distance:.4f}  "
            f"chunk_type={hit.get('chunk_type')}"
        )
        lines.append(f"   {preview_content(str(hit.get('content', '')))}")
    lines.append("")
    return "\n".join(lines)


def run_all(
    *,
    base_url: str = DEFAULT_BASE_URL,
    k: int = DEFAULT_K,
    opener: urllib.request.OpenerDirector | None = None,
) -> str:
    """Execute all archetype queries and return the combined report."""
    parts: list[str] = []
    for label, query in QUERIES:
        body = search(query, k=k, base_url=base_url, opener=opener)
        parts.append(format_results(label, query, body))
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint — print archetype search results to stdout."""
    _ = argv
    base_url = os.environ.get("API_BASE_URL", DEFAULT_BASE_URL)
    try:
        report = run_all(base_url=base_url)
    except Exception as exc:
        print(f"query_examples failed: {exc}", file=sys.stderr)
        return 1
    print(report, end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
