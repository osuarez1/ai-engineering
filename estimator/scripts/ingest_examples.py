"""POST each sample budget to ``/embeddings/ingest`` (idempotent on 409).

Usage (API must be running)::

    uv run python scripts/ingest_examples.py
    docker compose run --rm estimator python scripts/ingest_examples.py

Set ``API_BASE_URL`` to override the default ``http://localhost:8000``.
Inside Compose, prefer ``http://estimator:8000`` when calling from another service,
or ``http://localhost:8000`` from the host.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = "http://localhost:8000"
DOCUMENT_TYPE = "historical_budget"
SAMPLE_PATH = Path(__file__).resolve().parents[1] / "data" / "budgets_sample.json"


def source_path_for(budget_id: str) -> str:
    """Build the synthetic source_path used for idempotent ingestion."""
    return f"data/budgets_sample.json#{budget_id}"


def load_budgets(path: Path = SAMPLE_PATH) -> list[dict]:
    """Load the sample budget corpus from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def ingest_budget(
    budget: dict,
    *,
    base_url: str = DEFAULT_BASE_URL,
    opener: urllib.request.OpenerDirector | None = None,
) -> tuple[int, dict]:
    """POST one budget to the ingest endpoint; return (status_code, body)."""
    payload = {
        "source_path": source_path_for(budget["budget_id"]),
        "document_type": DOCUMENT_TYPE,
        "content": budget,
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/embeddings/ingest",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    open_fn = opener.open if opener is not None else urllib.request.urlopen
    try:
        with open_fn(request, timeout=120) as response:
            body = json.loads(response.read().decode("utf-8"))
            return int(response.status), body
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            body = {"detail": raw}
        return int(exc.code), body


def ingest_all(
    budgets: list[dict],
    *,
    base_url: str = DEFAULT_BASE_URL,
    opener: urllib.request.OpenerDirector | None = None,
) -> list[tuple[str, int, dict]]:
    """Ingest every budget; treat 200 and 409 as success outcomes."""
    outcomes: list[tuple[str, int, dict]] = []
    for budget in budgets:
        budget_id = budget["budget_id"]
        status, body = ingest_budget(budget, base_url=base_url, opener=opener)
        outcomes.append((budget_id, status, body))
        if status == 200:
            print(
                f"OK  {budget_id}: document_id={body.get('document_id')} "
                f"chunks={body.get('chunks_created')}"
            )
        elif status == 409:
            print(
                f"SKIP {budget_id}: already ingested "
                f"(document_id={body.get('document_id')})"
            )
        else:
            print(f"FAIL {budget_id}: HTTP {status} {body}", file=sys.stderr)
    return outcomes


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint — return 0 when every budget is 200 or 409."""
    _ = argv  # reserved for future flags
    base_url = os.environ.get("API_BASE_URL", DEFAULT_BASE_URL)
    budgets = load_budgets()
    print(f"Ingesting {len(budgets)} budgets into {base_url} …")
    outcomes = ingest_all(budgets, base_url=base_url)
    failures = [o for o in outcomes if o[1] not in (200, 409)]
    if failures:
        print(f"{len(failures)} ingestion(s) failed", file=sys.stderr)
        return 1
    print(f"Done: {len(outcomes)} budgets processed")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
