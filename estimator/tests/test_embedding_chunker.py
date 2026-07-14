import json
from pathlib import Path

import pytest

from app.embedding_pipeline.chunker import (
    JSONStructuralChunker,
    _build_chunk_metadata,
    _build_chunk_text,
    count_tokens,
)
from app.embedding_pipeline.schemas import Budget, BudgetComponent, ClientMetadata


@pytest.fixture
def sample_budget() -> Budget:
    return Budget(
        budget_id="BUD-TEST-001",
        client_metadata=ClientMetadata(name="TestCo", sector="finance", country="ES"),
        project_summary="Mobile banking API with OAuth 2.0 authentication",
        main_technology="ruby_on_rails",
        year=2024,
        total_estimated_hours=120,
        components=[
            BudgetComponent(
                component_id="AUTH-001",
                name="OAuth 2.0 authentication backend",
                description="Implementation of OAuth 2.0 flows",
                tech_stack=["ruby_on_rails", "postgresql", "redis"],
                estimated_hours=120,
                complexity="high",
                dependencies=[],
            )
        ],
    )


def test_chunker_produces_one_chunk_per_component(sample_budget: Budget) -> None:
    chunks = JSONStructuralChunker().chunk([sample_budget])
    assert len(chunks) == 1


def test_chunk_id_format(sample_budget: Budget) -> None:
    chunk = JSONStructuralChunker().chunk([sample_budget])[0]
    assert chunk.chunk_id == "BUD-TEST-001::AUTH-001"


def test_chunk_text_includes_contextual_header(sample_budget: Budget) -> None:
    component = sample_budget.components[0]
    text = _build_chunk_text(sample_budget, component)
    assert "[Project: Mobile banking API with OAuth 2.0 authentication]" in text
    assert "[Client sector: finance | Year: 2024 | Main tech: ruby_on_rails]" in text
    assert "Component: OAuth 2.0 authentication backend" in text
    assert "Tech stack: ruby_on_rails, postgresql, redis" in text


def test_chunk_metadata_fields(sample_budget: Budget) -> None:
    component = sample_budget.components[0]
    metadata = _build_chunk_metadata(sample_budget, component)
    assert metadata == {
        "budget_id": "BUD-TEST-001",
        "component_id": "AUTH-001",
        "client_sector": "finance",
        "main_technology": "ruby_on_rails",
        "year": 2024,
        "complexity": "high",
        "estimated_hours": 120,
    }


def test_token_count_matches_tiktoken(sample_budget: Budget) -> None:
    chunk = JSONStructuralChunker().chunk([sample_budget])[0]
    assert chunk.token_count == count_tokens(chunk.text)
    assert chunk.token_count > 0


def test_chunker_uses_sample_json_budgets() -> None:
    data = json.loads(Path("data/budgets_sample.json").read_text())
    budgets = [Budget.model_validate(item) for item in data[:2]]
    chunks = JSONStructuralChunker().chunk(budgets)
    assert len(chunks) == sum(len(budget.components) for budget in budgets)
