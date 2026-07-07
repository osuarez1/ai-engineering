"""Structural chunker for JSON budget proposals."""

from functools import lru_cache

import tiktoken

from app.embedding_pipeline.schemas import Budget, BudgetComponent, Chunk

EMBEDDING_MODEL = "text-embedding-3-small"


@lru_cache(maxsize=1)
def _get_token_encoder() -> tiktoken.Encoding:
    """Return a cached tokenizer for the embedding model."""
    return tiktoken.encoding_for_model(EMBEDDING_MODEL)


def count_tokens(text: str) -> int:
    """Count tokens in text using the embedding model tokenizer."""
    return len(_get_token_encoder().encode(text))


def _build_chunk_text(budget: Budget, component: BudgetComponent) -> str:
    """Render a component chunk with parent proposal context."""
    sector = budget.client_metadata.sector
    tech_stack = ", ".join(component.tech_stack)
    return (
        f"[Project: {budget.project_summary}]\n"
        f"[Client sector: {sector} | Year: {budget.year} | Main tech: {budget.main_technology}]\n"
        "\n"
        f"Component: {component.name}\n"
        f"Description: {component.description}\n"
        f"Tech stack: {tech_stack}\n"
        f"Complexity: {component.complexity}\n"
        f"Estimated hours: {component.estimated_hours}\n"
    )


def _build_chunk_metadata(budget: Budget, component: BudgetComponent) -> dict[str, str | int]:
    """Build filterable metadata for a component chunk."""
    return {
        "budget_id": budget.budget_id,
        "component_id": component.component_id,
        "client_sector": budget.client_metadata.sector,
        "main_technology": budget.main_technology,
        "year": budget.year,
        "complexity": component.complexity,
        "estimated_hours": component.estimated_hours,
    }


class JSONStructuralChunker:
    """Split budget proposals into one chunk per component."""

    def chunk(self, budgets: list[Budget]) -> list[Chunk]:
        """Yield one chunk per budget component."""
        chunks: list[Chunk] = []
        for budget in budgets:
            for component in budget.components:
                text = _build_chunk_text(budget, component)
                chunks.append(
                    Chunk(
                        chunk_id=f"{budget.budget_id}::{component.component_id}",
                        text=text,
                        metadata=_build_chunk_metadata(budget, component),
                        token_count=count_tokens(text),
                    )
                )
        return chunks
