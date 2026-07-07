import io
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

import pytest

from app.embedding_pipeline.compare_cli import (
    build_parser,
    compare_texts,
    format_compare_output,
    main,
)


def test_compare_texts_uses_injected_embedder() -> None:
    mock_embedder = MagicMock()
    mock_embedder.embed_one.side_effect = [[1.0, 0.0], [1.0, 0.0]]
    similarity = compare_texts("alpha", "beta", embedder=mock_embedder)
    assert similarity == 1.0
    assert mock_embedder.embed_one.call_count == 2


def test_compare_texts_builds_default_embedder() -> None:
    with patch("app.embedding_pipeline.compare_cli.OpenAIEmbedder") as mock_cls:
        mock_cls.return_value.embed_one.side_effect = [[1.0, 0.0], [0.0, 1.0]]
        similarity = compare_texts("alpha", "beta")
    assert similarity == 0.0


def test_format_compare_output() -> None:
    output = format_compare_output("hello", "world", 0.5)
    assert output == "Text A: hello\nText B: world\nCosine similarity: 0.5000\n"


def test_build_parser_requires_text_arguments() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_main_prints_similarity() -> None:
    with patch("app.embedding_pipeline.compare_cli.compare_texts", return_value=0.8421):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = main(["--text-a", "OAuth", "--text-b", "JWT"])
    assert exit_code == 0
    assert "Cosine similarity: 0.8421" in buffer.getvalue()
