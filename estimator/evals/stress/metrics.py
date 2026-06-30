"""Stress-test metrics for turn observations and session snapshots."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

DEFAULT_MEMORY_WHERE: tuple[str, ...] = ("summary", "anchors", "metadata")


@dataclass(frozen=True)
class MetricResult:
    name: str
    score: float
    passed: bool
    details: str


class LatencyBudgetMetric:
    """Pass when ``latency_ms`` in the observation is within budget."""

    def __init__(self, budget_ms: int = 4000) -> None:
        self.budget_ms = budget_ms

    def evaluate(self, observation: dict[str, Any]) -> MetricResult:
        latency_ms = int(observation.get("latency_ms", 0))
        passed = latency_ms <= self.budget_ms
        score = 1.0 if passed else 0.0
        return MetricResult(
            name="latency_budget",
            score=score,
            passed=passed,
            details=f"latency_ms={latency_ms} budget_ms={self.budget_ms}",
        )


class CostBudgetMetric:
    """Pass when ``cost_usd`` in the observation is within budget."""

    def __init__(self, budget_usd: float = 0.05) -> None:
        self.budget_usd = budget_usd

    def evaluate(self, observation: dict[str, Any]) -> MetricResult:
        cost_usd = float(observation.get("cost_usd", 0.0))
        passed = cost_usd <= self.budget_usd
        score = 1.0 if passed else 0.0
        return MetricResult(
            name="cost_budget",
            score=score,
            passed=passed,
            details=f"cost_usd={cost_usd:.6f} budget_usd={self.budget_usd:.6f}",
        )


class MemoryDriftMetric:
    """Pass when ``fact`` appears as a case-insensitive substring in session memory."""

    def __init__(
        self,
        fact: str,
        where: list[str] | None = None,
    ) -> None:
        self.fact = fact
        self.where = list(where or DEFAULT_MEMORY_WHERE)

    def evaluate(self, snapshot: dict[str, Any]) -> MetricResult:
        needle = self.fact.casefold()
        if not needle:
            return MetricResult(
                name=self._metric_name(),
                score=0.0,
                passed=False,
                details="empty fact",
            )

        for location_name, haystack in _memory_locations(snapshot, self.where).items():
            if needle in haystack.casefold():
                return MetricResult(
                    name=self._metric_name(),
                    score=1.0,
                    passed=True,
                    details=f"found in {location_name}",
                )

        searched = ", ".join(self.where) or "(none)"
        return MetricResult(
            name=self._metric_name(),
            score=0.0,
            passed=False,
            details=f"not found in {searched}",
        )

    def _metric_name(self) -> str:
        preview = self.fact[:40]
        if len(self.fact) > 40:
            preview += "..."
        return f"memory_drift:{preview}"


def run_all_metrics(
    observation: dict[str, Any],
    snapshot: dict[str, Any],
    pending_facts: list[str],
    *,
    latency_budget_ms: int = 4000,
    cost_budget_usd: float = 0.05,
) -> list[MetricResult]:
    """Evaluate latency, cost, and memory-drift metrics for one stress turn."""
    results = [
        LatencyBudgetMetric(latency_budget_ms).evaluate(observation),
        CostBudgetMetric(cost_budget_usd).evaluate(observation),
    ]
    for fact in pending_facts:
        results.append(MemoryDriftMetric(fact).evaluate(snapshot))
    return results


def _memory_locations(snapshot: dict[str, Any], where: list[str]) -> dict[str, str]:
    locations: dict[str, str] = {}
    if "summary" in where:
        locations["summary"] = str(snapshot.get("summary") or "")
    if "anchors" in where:
        anchors = snapshot.get("anchors") or []
        locations["anchors"] = "\n".join(str(anchor) for anchor in anchors)
    if "metadata" in where:
        metadata = snapshot.get("project_metadata") or {}
        locations["metadata"] = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
    return locations
