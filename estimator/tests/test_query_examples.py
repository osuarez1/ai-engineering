"""Tests for root-level query_examples.py."""

from __future__ import annotations

import io
import json
from unittest.mock import MagicMock, patch

import pytest

import query_examples as mod


def test_queries_cover_five_archetypes() -> None:
    assert len(mod.QUERIES) == 5
    labels = [label for label, _ in mod.QUERIES]
    assert "direct component" in labels[0].lower()
    assert "reformulation" in labels[1].lower()
    assert "domain" in labels[2].lower()
    assert "ambiguous" in labels[3].lower()
    assert "specific" in labels[4].lower()


def test_preview_content_truncates() -> None:
    short = "hello"
    assert mod.preview_content(short) == "hello"
    long = "x" * 200
    preview = mod.preview_content(long, limit=20)
    assert len(preview) == 20
    assert preview.endswith("…")


def test_format_results_readable() -> None:
    body = {
        "search_time_ms": 42,
        "results": [
            {
                "chunk_id": 7,
                "distance": 0.123456,
                "chunk_type": "budget_component",
                "content": "OAuth 2.0 authentication backend for mobile banking",
            }
        ],
    }
    text = mod.format_results("1. Known", "REST API", body)
    assert "chunk_id=7" in text
    assert "distance=0.1235" in text
    assert "budget_component" in text
    assert "OAuth 2.0" in text


def test_format_results_empty() -> None:
    text = mod.format_results("label", "q", {"results": []})
    assert "(no results)" in text


def test_search_returns_json_body() -> None:
    payload = {"query": "q", "k": 5, "results": []}
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode()
    response.__enter__ = MagicMock(return_value=response)
    response.__exit__ = MagicMock(return_value=False)
    opener = MagicMock()
    opener.open.return_value = response

    body = mod.search("q", base_url="http://api:8000/", opener=opener)
    assert body == payload
    request = opener.open.call_args.args[0]
    assert request.full_url == "http://api:8000/search"


def test_search_raises_on_http_error() -> None:
    import urllib.error

    err = urllib.error.HTTPError(
        url="http://localhost:8000/search",
        code=500,
        msg="Error",
        hdrs=None,  # type: ignore[arg-type]
        fp=io.BytesIO(json.dumps({"detail": "boom"}).encode()),
    )
    opener = MagicMock()
    opener.open.side_effect = err
    with pytest.raises(RuntimeError, match="HTTP 500"):
        mod.search("q", opener=opener)


def test_search_raises_on_non_json_http_error() -> None:
    import urllib.error

    err = urllib.error.HTTPError(
        url="http://localhost:8000/search",
        code=502,
        msg="Bad Gateway",
        hdrs=None,  # type: ignore[arg-type]
        fp=io.BytesIO(b"upstream"),
    )
    opener = MagicMock()
    opener.open.side_effect = err
    with pytest.raises(RuntimeError, match="upstream"):
        mod.search("q", opener=opener)


def test_run_all_concatenates_reports() -> None:
    fake_body = {"search_time_ms": 1, "results": []}
    with patch.object(mod, "search", return_value=fake_body) as mock_search:
        report = mod.run_all(base_url="http://x")
    assert mock_search.call_count == 5
    assert report.count("search_time_ms:") == 5


def test_main_success_and_failure(capsys: pytest.CaptureFixture[str]) -> None:
    with patch.object(mod, "run_all", return_value="REPORT\n"):
        assert mod.main([]) == 0
    assert capsys.readouterr().out == "REPORT\n"

    with patch.object(mod, "run_all", side_effect=RuntimeError("down")):
        assert mod.main() == 1
    assert "failed" in capsys.readouterr().err
