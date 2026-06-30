"""LLM cost estimation for stress-test observability.

Pricing is expressed in USD per 1M tokens. Unknown models return 0.0 so
callers can still emit turn_observed without failing on new model ids.
"""

from __future__ import annotations

MODEL_COSTS: dict[str, dict[str, float]] = {
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
}


def compute_cost_usd(model: str, usage: dict) -> float:
    """Return estimated USD cost for a single LLM call."""
    rates = MODEL_COSTS.get(model)
    if rates is None:
        for known_model, known_rates in MODEL_COSTS.items():
            if model.startswith(known_model):
                rates = known_rates
                break
    if rates is None:
        return 0.0

    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000
