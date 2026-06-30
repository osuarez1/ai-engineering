import pytest

from app.services.llm_wrapper import MODEL_COSTS, compute_cost_usd


@pytest.mark.parametrize(
    ("model", "usage", "expected"),
    [
        (
            "gpt-4o-mini",
            {"input_tokens": 1_000_000, "output_tokens": 0},
            0.15,
        ),
        (
            "gpt-4o-mini",
            {"input_tokens": 0, "output_tokens": 1_000_000},
            0.60,
        ),
        (
            "claude-haiku-4-5",
            {"input_tokens": 500_000, "output_tokens": 500_000},
            3.0,
        ),
        (
            "gemini-2.0-flash",
            {"input_tokens": 2_000_000, "output_tokens": 1_000_000},
            0.60,
        ),
    ],
)
def test_compute_cost_usd_known_models(model: str, usage: dict, expected: float) -> None:
    assert compute_cost_usd(model, usage) == pytest.approx(expected)


def test_compute_cost_usd_unknown_model_returns_zero() -> None:
    assert compute_cost_usd("unknown-model", {"input_tokens": 1000, "output_tokens": 1000}) == 0.0


def test_compute_cost_usd_missing_usage_keys_treated_as_zero() -> None:
    assert compute_cost_usd("gpt-4o-mini", {}) == 0.0


def test_model_costs_covers_default_models() -> None:
    assert set(MODEL_COSTS) == {"claude-haiku-4-5", "gpt-4o-mini", "gemini-2.0-flash"}
