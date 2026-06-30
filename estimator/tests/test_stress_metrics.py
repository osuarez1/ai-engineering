from evals.stress.metrics import (
    CostBudgetMetric,
    LatencyBudgetMetric,
    MemoryDriftMetric,
    run_all_metrics,
)


def test_latency_budget_metric_passes_under_budget() -> None:
    result = LatencyBudgetMetric(budget_ms=4000).evaluate({"latency_ms": 2500})

    assert result.name == "latency_budget"
    assert result.passed is True
    assert result.score == 1.0
    assert "latency_ms=2500" in result.details


def test_cost_budget_metric_fails_over_budget() -> None:
    result = CostBudgetMetric(budget_usd=0.05).evaluate({"cost_usd": 0.08})

    assert result.name == "cost_budget"
    assert result.passed is False
    assert result.score == 0.0
    assert "cost_usd=0.080000" in result.details


def test_memory_drift_metric_finds_fact_in_anchors() -> None:
    snapshot = {
        "summary": "User discussed scope.",
        "anchors": ["project is called Nimbus", "budget 30000 EUR"],
        "project_metadata": {"project_name": "Nimbus"},
    }
    result = MemoryDriftMetric("Nimbus").evaluate(snapshot)

    assert result.passed is True
    assert result.score == 1.0
    assert result.details == "found in anchors"


def test_memory_drift_metric_empty_snapshot_edge_case() -> None:
    result = MemoryDriftMetric("Nimbus").evaluate(
        {"summary": "", "anchors": [], "project_metadata": {}},
    )

    assert result.passed is False
    assert result.score == 0.0
    assert "not found in summary, anchors, metadata" in result.details


def test_memory_drift_metric_is_case_insensitive() -> None:
    snapshot = {
        "summary": "Stack includes flutter for mobile.",
        "anchors": [],
        "project_metadata": {},
    }
    result = MemoryDriftMetric("FLUTTER").evaluate(snapshot)

    assert result.passed is True
    assert result.details == "found in summary"


def test_run_all_metrics_evaluates_budgets_and_pending_facts() -> None:
    observation = {"latency_ms": 100, "cost_usd": 0.01}
    snapshot = {
        "summary": "Earlier turn mentioned auth requirements.",
        "anchors": ["project is called Nimbus"],
        "project_metadata": {"project_name": "Nimbus"},
    }

    results = run_all_metrics(
        observation,
        snapshot,
        pending_facts=["auth", "Nimbus"],
        latency_budget_ms=4000,
        cost_budget_usd=0.05,
    )

    assert [result.name for result in results] == [
        "latency_budget",
        "cost_budget",
        "memory_drift:auth",
        "memory_drift:Nimbus",
    ]
    assert all(result.passed for result in results)
