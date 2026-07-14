"""Tests for scripts/ingest_examples.py."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest

from scripts import ingest_examples as mod


def _budget(budget_id: str = "BUD-TEST") -> dict:
    return {
        "budget_id": budget_id,
        "client_metadata": {"name": "Acme", "sector": "finance", "country": "ES"},
        "project_summary": "API",
        "main_technology": "fastapi",
        "year": 2024,
        "total_estimated_hours": 10,
        "components": [
            {
                "component_id": "C1",
                "name": "Auth",
                "description": "OAuth",
                "tech_stack": ["fastapi"],
                "estimated_hours": 10,
                "complexity": "low",
                "dependencies": [],
            }
        ],
    }


def test_source_path_for() -> None:
    assert mod.source_path_for("BUD-2024-014") == "data/budgets_sample.json#BUD-2024-014"


def test_load_budgets_reads_sample_file() -> None:
    budgets = mod.load_budgets()
    assert len(budgets) == 15
    assert budgets[0]["budget_id"].startswith("BUD-")


def test_ingest_budget_returns_200_body() -> None:
    body = {"document_id": 1, "chunks_created": 1, "embedding_dimension": 1536, "ingestion_time_ms": 10}
    response = MagicMock()
    response.status = 200
    response.read.return_value = json.dumps(body).encode()
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)

    opener = MagicMock()
    opener.open.return_value = response

    status, parsed = mod.ingest_budget(_budget(), base_url="http://api:8000", opener=opener)
    assert status == 200
    assert parsed == body
    request = opener.open.call_args.args[0]
    assert request.full_url == "http://api:8000/embeddings/ingest"
    assert json.loads(request.data.decode())["source_path"].endswith("#BUD-TEST")


def test_ingest_budget_handles_http_error_json() -> None:
    import urllib.error

    err = urllib.error.HTTPError(
        url="http://localhost:8000/embeddings/ingest",
        code=409,
        msg="Conflict",
        hdrs=None,  # type: ignore[arg-type]
        fp=io.BytesIO(json.dumps({"detail": "Document already ingested", "document_id": 9}).encode()),
    )
    opener = MagicMock()
    opener.open.side_effect = err

    status, body = mod.ingest_budget(_budget(), opener=opener)
    assert status == 409
    assert body["document_id"] == 9


def test_ingest_budget_handles_http_error_non_json() -> None:
    import urllib.error

    err = urllib.error.HTTPError(
        url="http://localhost:8000/embeddings/ingest",
        code=500,
        msg="Error",
        hdrs=None,  # type: ignore[arg-type]
        fp=io.BytesIO(b"not-json"),
    )
    opener = MagicMock()
    opener.open.side_effect = err

    status, body = mod.ingest_budget(_budget("BUD-X"), opener=opener)
    assert status == 500
    assert body == {"detail": "not-json"}


def test_ingest_all_prints_ok_skip_and_fail(capsys: pytest.CaptureFixture[str]) -> None:
    budgets = [_budget("A"), _budget("B"), _budget("C")]

    def _fake(budget: dict, **kwargs: object) -> tuple[int, dict]:
        mapping = {
            "A": (200, {"document_id": 1, "chunks_created": 2}),
            "B": (409, {"document_id": 2}),
            "C": (500, {"detail": "boom"}),
        }
        return mapping[budget["budget_id"]]

    with patch.object(mod, "ingest_budget", side_effect=_fake):
        outcomes = mod.ingest_all(budgets)

    assert [o[1] for o in outcomes] == [200, 409, 500]
    captured = capsys.readouterr()
    assert "OK  A:" in captured.out
    assert "SKIP B:" in captured.out
    assert "FAIL C:" in captured.err


def test_main_returns_zero_when_all_ok_or_skip(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(mod, "load_budgets", return_value=[_budget("A"), _budget("B")]),
        patch.object(
            mod,
            "ingest_all",
            return_value=[
                ("A", 200, {"document_id": 1}),
                ("B", 409, {"document_id": 2}),
            ],
        ),
        patch.dict("os.environ", {"API_BASE_URL": "http://example:8000"}, clear=False),
    ):
        assert mod.main([]) == 0
    assert "2 budgets processed" in capsys.readouterr().out


def test_main_returns_one_on_failures(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch.object(mod, "load_budgets", return_value=[_budget("A")]),
        patch.object(mod, "ingest_all", return_value=[("A", 500, {})]),
    ):
        assert mod.main() == 1
    assert "failed" in capsys.readouterr().err


def test_ingest_budget_handles_http_error_empty_body() -> None:
    import urllib.error

    err = urllib.error.HTTPError(
        url="http://localhost:8000/embeddings/ingest",
        code=502,
        msg="Bad Gateway",
        hdrs=None,  # type: ignore[arg-type]
        fp=io.BytesIO(b""),
    )
    opener = MagicMock()
    opener.open.side_effect = err

    status, body = mod.ingest_budget(_budget(), opener=opener)
    assert status == 502
    assert body == {}
