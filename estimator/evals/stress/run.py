"""Stress-test runner for CAG exercise 6.1."""

from __future__ import annotations

import argparse
import asyncio
import csv
import os
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from unittest.mock import patch

import httpx

from evals.stress.fixtures.build_pdfs import (
    ATTACHMENT_SIZES_KB,
    attachment_pdf_path,
    build_pdfs,
    recall_token,
)
from evals.stress.metrics import run_all_metrics
from evals.stress.scenarios import SCENARIO_NAMES, get_scenario

TURN_OBSERVED_FIELDS: tuple[str, ...] = (
    "turn_index",
    "session_id",
    "enriched_transcript_chars",
    "attachments_total_chars",
    "messages_in_window",
    "anchors_count",
    "summary_chars",
    "tokens_in",
    "tokens_out",
    "cost_usd",
    "latency_ms",
    "cache_hit_kind",
    "last_resolved_tier",
)

CSV_COLUMNS: tuple[str, ...] = (
    "scenario",
    "attachment_size_kb",
    "repeat",
    *TURN_OBSERVED_FIELDS,
    "cumulative_cost_usd",
    "latency_budget_passed",
    "cost_budget_passed",
    "memory_drift_score",
    "attachment_recall",
)

DEFAULT_OUTPUT = Path("evals/stress/results.csv")
DEFAULT_SCENARIOS = ",".join(SCENARIO_NAMES)
DEFAULT_ATTACHMENT_SIZES = "0,5,20,50,100"
ESTIMATION_TEXT = "## Project estimate\n\nTotal: 120 hours · 7,500 EUR"


@dataclass(frozen=True)
class RunConfig:
    scenarios: tuple[str, ...]
    attachment_sizes_kb: tuple[int, ...]
    repeats: int
    max_turns: int
    latency_budget_ms: int
    cost_budget_usd: float
    output: Path
    http_base_url: str | None
    cache_on: bool
    real_llm: bool
    request_delay_ms: int


class StressTransport(Protocol):
    async def create_session(self) -> str: ...

    async def estimate(
        self,
        session_id: str,
        transcript: str,
        attachments: Sequence[tuple[str, bytes]],
    ) -> dict[str, Any]: ...

    async def get_snapshot(self, session_id: str) -> dict[str, Any]: ...


class HttpTransport:
    """Remote stress transport via FastAPI HTTP endpoints."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def create_session(self) -> str:
        response = await self._client.post("/sessions")
        response.raise_for_status()
        return response.json()["session_id"]

    async def estimate(
        self,
        session_id: str,
        transcript: str,
        attachments: Sequence[tuple[str, bytes]],
    ) -> dict[str, Any]:
        files = [
            ("attachments", (filename, content, "application/pdf"))
            for filename, content in attachments
        ]
        response = await self._client.post(
            f"/sessions/{session_id}/estimate",
            data={"transcript": transcript},
            files=files,
        )
        response.raise_for_status()
        return response.json()

    async def get_snapshot(self, session_id: str) -> dict[str, Any]:
        response = await self._client.get(f"/sessions/{session_id}")
        response.raise_for_status()
        return response.json()


class InProcessTransport:
    """In-process stress transport using FastAPI TestClient."""

    def __init__(self, client: Any) -> None:
        self._client = client

    async def create_session(self) -> str:
        return await asyncio.to_thread(self._create_session_sync)

    async def estimate(
        self,
        session_id: str,
        transcript: str,
        attachments: Sequence[tuple[str, bytes]],
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._estimate_sync,
            session_id,
            transcript,
            list(attachments),
        )

    async def get_snapshot(self, session_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._get_snapshot_sync, session_id)

    def _create_session_sync(self) -> str:
        response = self._client.post("/sessions")
        response.raise_for_status()
        return response.json()["session_id"]

    def _estimate_sync(
        self,
        session_id: str,
        transcript: str,
        attachments: list[tuple[str, bytes]],
    ) -> dict[str, Any]:
        files = [
            ("attachments", (filename, content, "application/pdf"))
            for filename, content in attachments
        ]
        response = self._client.post(
            f"/sessions/{session_id}/estimate",
            data={"transcript": transcript},
            files=files,
        )
        response.raise_for_status()
        return response.json()

    def _get_snapshot_sync(self, session_id: str) -> dict[str, Any]:
        response = self._client.get(f"/sessions/{session_id}")
        response.raise_for_status()
        return response.json()


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CAG stress scenarios and write CSV results.")
    parser.add_argument(
        "--http",
        metavar="URL",
        help="Base URL for a running estimator API (default: in-process TestClient).",
    )
    parser.add_argument(
        "--scenarios",
        default=DEFAULT_SCENARIOS,
        help=f"Comma-separated scenario names (default: {DEFAULT_SCENARIOS}).",
    )
    parser.add_argument(
        "--attachment-sizes",
        default=DEFAULT_ATTACHMENT_SIZES,
        help=f"Comma-separated attachment sizes in KiB (default: {DEFAULT_ATTACHMENT_SIZES}).",
    )
    parser.add_argument("--repeats", type=int, default=3, help="Runs per scenario × size.")
    parser.add_argument(
        "--max-turns",
        type=int,
        default=20,
        help="Maximum turns per session (default: 20).",
    )
    parser.add_argument(
        "--latency-budget-ms",
        type=int,
        default=4000,
        help="Latency budget per turn in milliseconds.",
    )
    parser.add_argument(
        "--cost-budget-usd",
        type=float,
        default=0.05,
        help="Cost budget per turn in USD.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"CSV output path (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--cache-on",
        action="store_true",
        help="Leave LLM cache enabled for in-process runs (default: disabled).",
    )
    parser.add_argument(
        "--real-llm",
        action="store_true",
        help="Use the real LLM provider (no mock) for in-process runs; reads .env.",
    )
    parser.add_argument(
        "--request-delay-ms",
        type=int,
        default=None,
        help="Pause between estimate calls to avoid provider rate limits (default: 1500 with --real-llm, else 0).",
    )
    return parser.parse_args(argv)


def config_from_args(args: argparse.Namespace) -> RunConfig:
    scenarios = _parse_csv_tokens(args.scenarios)
    attachment_sizes = _parse_int_list(args.attachment_sizes)
    real_llm = bool(args.real_llm or args.http)
    request_delay_ms = args.request_delay_ms
    if request_delay_ms is None:
        request_delay_ms = 1500 if real_llm else 0
    return RunConfig(
        scenarios=tuple(scenarios),
        attachment_sizes_kb=tuple(attachment_sizes),
        repeats=args.repeats,
        max_turns=args.max_turns,
        latency_budget_ms=args.latency_budget_ms,
        cost_budget_usd=args.cost_budget_usd,
        output=args.output,
        http_base_url=args.http,
        cache_on=args.cache_on,
        real_llm=real_llm,
        request_delay_ms=request_delay_ms,
    )


def _parse_csv_tokens(value: str) -> list[str]:
    return [token.strip() for token in value.split(",") if token.strip()]


def _parse_int_list(value: str) -> list[int]:
    return [int(token.strip()) for token in value.split(",") if token.strip()]


def _configure_inprocess_env(*, cache_on: bool, real_llm: bool) -> None:
    if not real_llm:
        os.environ.setdefault("LLM_PROVIDER", "openai")
        os.environ.setdefault("OPENAI_API_KEY", "sk-test")
        os.environ.setdefault("LLM_MODEL", "gpt-4o-mini")
        os.environ.setdefault("APP_ENV", "development")
    os.environ["LLM_CACHE_ENABLED"] = "true" if cache_on else "false"


def _fake_llm_result(messages: list[dict[str, str]], *, version: str = "v2", opts=None) -> dict:
    user_content = messages[-1]["content"] if messages else ""
    text = ESTIMATION_TEXT
    for size_kb in ATTACHMENT_SIZES_KB:
        token = recall_token(size_kb)
        if token in user_content:
            text = f"{text}\n\nAttachment recall: {token}"
            break
    return {
        "text": text,
        "prompt_version": version,
        "model": "gpt-4o-mini",
        "provider": "openai",
        "usage": {
            "input_tokens": 100 + len(user_content) // 4,
            "output_tokens": 50,
            "total_tokens": 150 + len(user_content) // 4,
        },
        "finish_reason": "stop",
        "latency_ms": 42,
        "cost_usd": 0.0001,
        "cache_hit_kind": "none",
    }


def _load_attachment_bytes(size_kb: int) -> bytes:
    if size_kb <= 0:
        return b""
    path = attachment_pdf_path(size_kb)
    if not path.exists():
        build_pdfs()
    return path.read_bytes()


def _pending_facts(scenario_turns: Sequence[Any], current_turn_index: int) -> list[str]:
    return [
        turn.fact_to_remember for turn in scenario_turns if turn.turn_index < current_turn_index
    ]


def _memory_drift_score(metric_results: Sequence[Any]) -> float:
    drift_scores = [
        result.score for result in metric_results if result.name.startswith("memory_drift")
    ]
    if not drift_scores:
        return 1.0
    return statistics.mean(drift_scores)


def _attachment_recall(
    *,
    turn_index: int,
    attachment_size_kb: int,
    response_text: str,
) -> str:
    if turn_index != 1 or attachment_size_kb <= 0:
        return ""
    token = recall_token(attachment_size_kb)
    return str(token.casefold() in response_text.casefold())


def _build_row(
    *,
    scenario_name: str,
    attachment_size_kb: int,
    repeat: int,
    observation: dict[str, Any],
    cumulative_cost_usd: float,
    latency_budget_passed: bool,
    cost_budget_passed: bool,
    memory_drift_score: float,
    attachment_recall: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "scenario": scenario_name,
        "attachment_size_kb": attachment_size_kb,
        "repeat": repeat,
        "cumulative_cost_usd": cumulative_cost_usd,
        "latency_budget_passed": latency_budget_passed,
        "cost_budget_passed": cost_budget_passed,
        "memory_drift_score": memory_drift_score,
        "attachment_recall": attachment_recall,
    }
    for field in TURN_OBSERVED_FIELDS:
        row[field] = observation.get(field, "")
    return row


async def run_stress(config: RunConfig, transport: StressTransport) -> list[dict[str, Any]]:
    """Execute all configured stress runs and return CSV rows."""
    rows: list[dict[str, Any]] = []
    delay_seconds = config.request_delay_ms / 1000.0

    for scenario_name in config.scenarios:
        scenario = get_scenario(scenario_name, config.max_turns)
        for attachment_size_kb in config.attachment_sizes_kb:
            attachment_bytes = _load_attachment_bytes(attachment_size_kb)
            for repeat in range(config.repeats):
                session_id = await transport.create_session()
                cumulative_cost_usd = 0.0

                for turn in scenario.turns:
                    attachments: list[tuple[str, bytes]] = []
                    if turn.turn_index == 1 and attachment_size_kb > 0:
                        filename = f"attach_{attachment_size_kb}kb.pdf"
                        attachments = [(filename, attachment_bytes)]

                    estimate_response = await transport.estimate(
                        session_id,
                        turn.transcript,
                        attachments,
                    )
                    if delay_seconds > 0:
                        await asyncio.sleep(delay_seconds)
                    snapshot = await transport.get_snapshot(session_id)
                    observation = snapshot.get("last_turn_observed") or {}
                    cumulative_cost_usd += float(observation.get("cost_usd", 0.0))

                    pending = _pending_facts(scenario.turns, turn.turn_index)
                    metric_results = run_all_metrics(
                        observation,
                        snapshot,
                        pending,
                        latency_budget_ms=config.latency_budget_ms,
                        cost_budget_usd=config.cost_budget_usd,
                    )
                    latency_budget_passed = next(
                        result.passed
                        for result in metric_results
                        if result.name == "latency_budget"
                    )
                    cost_budget_passed = next(
                        result.passed for result in metric_results if result.name == "cost_budget"
                    )
                    memory_drift_score = _memory_drift_score(metric_results)
                    attachment_recall = _attachment_recall(
                        turn_index=turn.turn_index,
                        attachment_size_kb=attachment_size_kb,
                        response_text=str(estimate_response.get("text", "")),
                    )

                    rows.append(
                        _build_row(
                            scenario_name=scenario_name,
                            attachment_size_kb=attachment_size_kb,
                            repeat=repeat,
                            observation=observation,
                            cumulative_cost_usd=cumulative_cost_usd,
                            latency_budget_passed=latency_budget_passed,
                            cost_budget_passed=cost_budget_passed,
                            memory_drift_score=memory_drift_score,
                            attachment_recall=attachment_recall,
                        )
                    )

    return rows


def write_csv(output_path: Path, rows: Sequence[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(CSV_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)


async def _ensure_http_server_reachable(client: httpx.AsyncClient, base_url: str) -> None:
    """Fail fast with a clear message when --http is used without a running API."""
    try:
        response = await client.get("/health")
        response.raise_for_status()
    except httpx.ConnectError as exc:
        raise SystemExit(
            f"Cannot connect to {base_url.rstrip('/')}.\n"
            "Start the estimator API in another terminal, then re-run:\n"
            "  cd estimator\n"
            "  LLM_CACHE_ENABLED=false uv run uvicorn app.main:app --reload\n"
            "  uv run python -m evals.stress.run --http http://localhost:8000"
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise SystemExit(
            f"Health check failed at {base_url.rstrip('/')}/health: "
            f"HTTP {exc.response.status_code}"
        ) from exc


async def _async_main(config: RunConfig) -> int:
    build_pdfs()
    if config.http_base_url:
        async with httpx.AsyncClient(
            base_url=config.http_base_url.rstrip("/"),
            timeout=120.0,
        ) as client:
            await _ensure_http_server_reachable(client, config.http_base_url)
            rows = await run_stress(config, HttpTransport(client))
    else:
        _configure_inprocess_env(cache_on=config.cache_on, real_llm=config.real_llm)
        from app.config import get_settings
        from app.main import app
        from app.services.llm_cache import clear_cache
        from fastapi.testclient import TestClient

        clear_cache()
        get_settings.cache_clear()

        transport = InProcessTransport(TestClient(app))
        if config.real_llm:
            rows = await run_stress(config, transport)
        else:
            with patch(
                "app.services.session_estimation.generate_estimation_from_messages",
                _fake_llm_result,
            ):
                rows = await run_stress(config, transport)

    write_csv(config.output, rows)
    print(f"wrote {len(rows)} rows to {config.output}")
    return len(rows)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = config_from_args(args)
    return asyncio.run(_async_main(config))


if __name__ == "__main__":
    raise SystemExit(main())
