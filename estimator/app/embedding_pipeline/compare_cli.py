"""CLI helpers for comparing embedding similarity between two texts."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from app.embedding_pipeline.embedder import OpenAIEmbedder
from app.embedding_pipeline.similarity import cosine_similarity


def compare_texts(
    text_a: str,
    text_b: str,
    *,
    embedder: OpenAIEmbedder | None = None,
) -> float:
    """Embed two texts and return their cosine similarity."""
    active_embedder = embedder or OpenAIEmbedder()
    vec_a = active_embedder.embed_one(text_a)
    vec_b = active_embedder.embed_one(text_b)
    return cosine_similarity(vec_a, vec_b)


def format_compare_output(text_a: str, text_b: str, similarity: float) -> str:
    """Render CLI output for a similarity comparison."""
    return (
        f"Text A: {text_a}\n"
        f"Text B: {text_b}\n"
        f"Cosine similarity: {similarity:.4f}\n"
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the compare CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Compare cosine similarity of two texts via OpenAI embeddings.",
    )
    parser.add_argument("--text-a", required=True, help="First text to embed")
    parser.add_argument("--text-b", required=True, help="Second text to embed")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the compare CLI."""
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    similarity = compare_texts(args.text_a, args.text_b)
    print(format_compare_output(args.text_a, args.text_b, similarity), end="")
    return 0
