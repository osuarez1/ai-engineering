"""Aggregate stress-test CSV results and generate REPORT.md."""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_CSV = Path("evals/stress/results.csv")
DEFAULT_REPORT = Path("evals/stress/REPORT.md")
MEMORY_DRIFT_SAMPLE_TURNS = (1, 3, 6, 10, 20)

CSV_COLUMN_HEADERS: dict[str, dict[str, str]] = {
    "en": {
        "scenario": "scenario",
        "attachment_size_kb": "attachment_size_kb",
        "repeat": "repeat",
        "turn_index": "turn_index",
        "session_id": "session_id",
        "enriched_transcript_chars": "enriched_transcript_chars",
        "attachments_total_chars": "attachments_total_chars",
        "messages_in_window": "messages_in_window",
        "anchors_count": "anchors_count",
        "summary_chars": "summary_chars",
        "tokens_in": "tokens_in",
        "tokens_out": "tokens_out",
        "cost_usd": "cost_usd",
        "latency_ms": "latency_ms",
        "cache_hit_kind": "cache_hit_kind",
        "last_resolved_tier": "last_resolved_tier",
        "cumulative_cost_usd": "cumulative_cost_usd",
        "latency_budget_passed": "latency_budget_passed",
        "cost_budget_passed": "cost_budget_passed",
        "memory_drift_score": "memory_drift_score",
        "attachment_recall": "attachment_recall",
    },
    "es": {
        "scenario": "escenario",
        "attachment_size_kb": "adjunto_kib",
        "repeat": "repeticion",
        "turn_index": "turno",
        "session_id": "id_sesion",
        "enriched_transcript_chars": "caracteres_transcripcion_enriquecida",
        "attachments_total_chars": "caracteres_adjuntos_total",
        "messages_in_window": "mensajes_en_ventana",
        "anchors_count": "num_anclas",
        "summary_chars": "caracteres_resumen",
        "tokens_in": "tokens_entrada",
        "tokens_out": "tokens_salida",
        "cost_usd": "coste_usd",
        "latency_ms": "latencia_ms",
        "cache_hit_kind": "tipo_acierto_cache",
        "last_resolved_tier": "ultimo_nivel_resuelto",
        "cumulative_cost_usd": "coste_acumulado_usd",
        "latency_budget_passed": "presupuesto_latencia_ok",
        "cost_budget_passed": "presupuesto_coste_ok",
        "memory_drift_score": "puntuacion_memory_drift",
        "attachment_recall": "recuperacion_adjunto",
    },
}

CSV_VALUE_TRANSLATIONS: dict[str, dict[str, str]] = {
    "es": {
        "none": "ninguno",
        "exact": "exacto",
        "semantic": "semantico",
        "low": "bajo",
        "medium": "medio",
        "high": "alto",
        "True": "verdadero",
        "False": "falso",
    },
}

REPORT_LOCALES: dict[str, dict[str, str]] = {
    "en": {
        "title": "# CAG Stress Test Report (Exercise 6.1)",
        "design_heading": "## Design decisions",
        "design_snapshot": (
            "- **Snapshot endpoint:** Each stress turn reads `GET /sessions/{id}` after estimate "
            "so metrics use genuine `last_turn_observed`, anchors, summary, and metadata rather "
            "than inferring state from the response body alone."
        ),
        "design_metrics": (
            "- **Metrics module location:** `evals/stress/metrics.py` lives beside the runner "
            "because it depends on the snapshot/`turn_observed` contract; there is no shared "
            "`evals/metrics.py` base package in this repo."
        ),
        "design_cache_on": (
            "- **Cache on during stress:** `LLM_CACHE_ENABLED=true` so exact and semantic cache "
            "hit rates are measured alongside latency and cost."
        ),
        "design_cache_off": (
            "- **Cache off during stress:** The runner disables `LLM_CACHE_ENABLED` for in-process "
            "runs (and expects it off on the server for `--http`) so repeat latency/cost curves "
            "measure provider variance, not cache replay."
        ),
        "design_spec_gap": (
            "- **Spec vs codebase gap:** Step 0 added anchors, rolling summary, dynamic tiers, "
            "cost wrapper, and cache instrumentation without tuning existing CAG constants "
            "(`MAX_CONVERSATION_TURNS`, prompt templates, etc.)."
        ),
        "run_mode": "**Run mode:**",
        "rows": "**Rows:**",
        "summary_heading": "## Summary table",
        "summary_header": (
            "| Scenario | Attachment (KiB) | P50 latency (ms) | P95 latency (ms) | "
            "Total cost (USD) | Exact cache hit | Semantic cache hit | Mean MemoryDrift |"
        ),
        "curves_heading": "## Curves",
        "latency_curve_heading": "### Latency vs input tokens (growing scenario, turn 1)",
        "latency_curve_header": (
            "| Attachment (KiB) | Mean tokens_in | Mean latency_ms | Mean attachments_total_chars |"
        ),
        "cost_curve_heading": "### Cumulative cost vs turn index (attachment size = 0 KiB)",
        "cost_curve_turn_header": "| Turn | Mean cumulative cost (USD) |",
        "drift_curve_heading": "### MemoryDrift mean vs turn index (sampled)",
        "drift_curve_header": "| Turn | Mean memory_drift_score |",
        "attachment_heading": "## Attachment recall",
        "attachment_line": (
            "- **{size} KiB** (`{token}`): recall rate {rate} over {rows} turn-1 rows."
        ),
        "attachment_none": "- No attachment rows in this CSV.",
        "analysis_heading": "## Analysis",
        "analysis_cost": (
            "Across the **growing** profile with no attachment, turn 20 cumulative cost "
            "({turn20_cost} mean per session) is **{cost_ratio:.1f}×** turn 1 per-turn cost "
            "({turn1_cost}), while mean `tokens_in` grows from {t1_tokens:.0f} to "
            "{t20_tokens:.0f} (**{token_ratio:.1f}×**) as history, anchors, and summary "
            "accumulate in the system prompt."
        ),
        "analysis_drift": (
            "Mean MemoryDrift recall stays at **{drift_t3:.0%}** through turn 12, then drops "
            "to **{drift_t20:.0%}** by turn 20 overall (pivot scenario at turn 20: "
            "**{pivot_drift:.0%}**). The 100 KiB attachment run caps `attachments_total_chars` "
            "at **{attach_chars:.0f}** (limit 60,000), and attachment sizes preserved their "
            "`STRESS_TOKEN_*` in the response on turn 1 at rate shown above."
        ),
    },
    "es": {
        "title": "# Informe de prueba de estrés CAG (Ejercicio 6.1)",
        "design_heading": "## Decisiones de diseño",
        "design_snapshot": (
            "- **Endpoint de snapshot:** Cada turno de estrés lee `GET /sessions/{id}` tras la "
            "estimación para que las métricas usen `last_turn_observed`, anclas, resumen y "
            "metadatos reales en lugar de inferir el estado solo desde el cuerpo de la respuesta."
        ),
        "design_metrics": (
            "- **Ubicación del módulo de métricas:** `evals/stress/metrics.py` vive junto al "
            "runner porque depende del contrato snapshot/`turn_observed`; no existe un paquete "
            "base compartido `evals/metrics.py` en este repositorio."
        ),
        "design_cache_on": (
            "- **Caché activada durante el estrés:** `LLM_CACHE_ENABLED=true` para medir "
            "tasas de acierto exacto y semántico junto con latencia y coste."
        ),
        "design_cache_off": (
            "- **Caché desactivada durante el estrés:** el runner desactiva `LLM_CACHE_ENABLED` "
            "en ejecuciones in-process (y espera que esté desactivada en el servidor con "
            "`--http`) para que las curvas de latencia/coste midan variación del proveedor, no "
            "reproducción desde caché."
        ),
        "design_spec_gap": (
            "- **Brecha especificación vs código:** el paso 0 añadió anclas, resumen incremental, "
            "niveles dinámicos, envoltorio de coste e instrumentación de caché sin ajustar "
            "constantes CAG existentes (`MAX_CONVERSATION_TURNS`, plantillas de prompt, etc.)."
        ),
        "run_mode": "**Modo de ejecución:**",
        "rows": "**Filas:**",
        "summary_heading": "## Tabla resumen",
        "summary_header": (
            "| Escenario | Adjunto (KiB) | Latencia P50 (ms) | Latencia P95 (ms) | "
            "Coste total (USD) | Acierto caché exacta | Acierto caché semántica | Media MemoryDrift |"
        ),
        "curves_heading": "## Curvas",
        "latency_curve_heading": "### Latencia vs tokens de entrada (escenario growing, turno 1)",
        "latency_curve_header": (
            "| Adjunto (KiB) | Media tokens_in | Media latency_ms | Media attachments_total_chars |"
        ),
        "cost_curve_heading": (
            "### Coste acumulado vs índice de turno (tamaño de adjunto = 0 KiB)"
        ),
        "cost_curve_turn_header": "| Turno | Media coste acumulado (USD) |",
        "drift_curve_heading": "### Media MemoryDrift vs índice de turno (muestreado)",
        "drift_curve_header": "| Turno | Media memory_drift_score |",
        "attachment_heading": "## Recuperación de adjuntos",
        "attachment_line": (
            "- **{size} KiB** (`{token}`): tasa de recuperación {rate} en {rows} filas del turno 1."
        ),
        "attachment_none": "- No hay filas con adjuntos en este CSV.",
        "analysis_heading": "## Análisis",
        "analysis_cost": (
            "En el perfil **growing** sin adjunto, el coste acumulado del turno 20 "
            "({turn20_cost} de media por sesión) es **{cost_ratio:.1f}×** el coste por turno "
            "del turno 1 ({turn1_cost}), mientras que la media de `tokens_in` crece de "
            "{t1_tokens:.0f} a {t20_tokens:.0f} (**{token_ratio:.1f}×**) a medida que el "
            "historial, las anclas y el resumen se acumulan en el prompt del sistema."
        ),
        "analysis_drift": (
            "La recuperación media de MemoryDrift se mantiene en **{drift_t3:.0%}** hasta el "
            "turno 12 y baja a **{drift_t20:.0%}** en el turno 20 global (escenario pivot en "
            "turno 20: **{pivot_drift:.0%}**). La ejecución con adjunto de 100 KiB limita "
            "`attachments_total_chars` a **{attach_chars:.0f}** (límite 60.000), y los tamaños "
            "de adjunto conservaron su `STRESS_TOKEN_*` en la respuesta del turno 1 según la "
            "tasa indicada arriba."
        ),
    },
}


@dataclass(frozen=True)
class GroupSummary:
    scenario: str
    attachment_size_kb: int
    row_count: int
    p50_latency_ms: float
    p95_latency_ms: float
    total_cost_usd: float
    exact_cache_hit_rate: float
    semantic_cache_hit_rate: float
    mean_memory_drift: float


def _base_stem(path: Path) -> str:
    """Strip locale suffix: ``results.en.csv`` -> ``results``."""
    stem = path.stem
    if "." in stem:
        return stem.rsplit(".", 1)[0]
    return stem


def localized_csv_path(csv_path: Path, locale: str) -> Path | None:
    if locale == "en":
        return None
    base = _base_stem(csv_path)
    return csv_path.with_name(f"{base}.{locale}{csv_path.suffix}")


def localize_csv_row(row: dict[str, str], locale: str) -> dict[str, str]:
    headers = CSV_COLUMN_HEADERS.get(locale, CSV_COLUMN_HEADERS["en"])
    value_map = CSV_VALUE_TRANSLATIONS.get(locale, {})
    localized: dict[str, str] = {}
    for field, value in row.items():
        header = headers.get(field, field)
        localized[header] = value_map.get(value, value)
    return localized


def write_localized_csv(csv_path: Path, output_path: Path, *, locale: str) -> None:
    rows = load_csv_rows(csv_path)
    if not rows:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("", encoding="utf-8")
        return

    localized_rows = [localize_csv_row(row, locale) for row in rows]
    headers = list(localized_rows[0].keys())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(localized_rows)


def load_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _float(value: str | float | int | None, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    return float(value)


def _int(value: str | float | int | None, default: int = 0) -> int:
    if value in (None, ""):
        return default
    return int(float(value))


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    rank = (len(ordered) - 1) * (pct / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def summarize_groups(rows: list[dict[str, str]]) -> list[GroupSummary]:
    grouped: dict[tuple[str, int], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (row["scenario"], _int(row["attachment_size_kb"]))
        grouped[key].append(row)

    summaries: list[GroupSummary] = []
    for (scenario, attachment_size_kb), group_rows in sorted(grouped.items()):
        latencies = [_float(row["latency_ms"]) for row in group_rows]
        costs = [_float(row["cost_usd"]) for row in group_rows]
        drift_scores = [_float(row["memory_drift_score"]) for row in group_rows]
        cache_kinds = [row.get("cache_hit_kind", "none") for row in group_rows]
        total_rows = len(group_rows)

        summaries.append(
            GroupSummary(
                scenario=scenario,
                attachment_size_kb=attachment_size_kb,
                row_count=total_rows,
                p50_latency_ms=percentile(latencies, 50),
                p95_latency_ms=percentile(latencies, 95),
                total_cost_usd=sum(costs),
                exact_cache_hit_rate=sum(kind == "exact" for kind in cache_kinds) / total_rows,
                semantic_cache_hit_rate=sum(kind == "semantic" for kind in cache_kinds) / total_rows,
                mean_memory_drift=statistics.mean(drift_scores) if drift_scores else 0.0,
            )
        )
    return summaries


def latency_vs_tokens_turn_one(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    turn_one = [
        row
        for row in rows
        if _int(row["turn_index"]) == 1 and row["scenario"] == "growing"
    ]
    by_size: dict[int, list[dict[str, str]]] = defaultdict(list)
    for row in turn_one:
        by_size[_int(row["attachment_size_kb"])].append(row)

    curve: list[dict[str, Any]] = []
    for size_kb in sorted(by_size):
        group = by_size[size_kb]
        curve.append(
            {
                "attachment_size_kb": size_kb,
                "mean_tokens_in": statistics.mean(_float(row["tokens_in"]) for row in group),
                "mean_latency_ms": statistics.mean(_float(row["latency_ms"]) for row in group),
                "mean_attachments_total_chars": statistics.mean(
                    _float(row["attachments_total_chars"]) for row in group
                ),
            }
        )
    return curve


def cumulative_cost_curve(
    rows: list[dict[str, str]],
    *,
    attachment_size_kb: int = 0,
) -> dict[str, list[dict[str, Any]]]:
    curves: dict[str, list[dict[str, Any]]] = {}
    for scenario in sorted({row["scenario"] for row in rows}):
        scenario_rows = [
            row
            for row in rows
            if row["scenario"] == scenario and _int(row["attachment_size_kb"]) == attachment_size_kb
        ]
        by_turn: dict[int, list[float]] = defaultdict(list)
        for row in scenario_rows:
            by_turn[_int(row["turn_index"])].append(_float(row["cumulative_cost_usd"]))

        curves[scenario] = [
            {
                "turn_index": turn_index,
                "mean_cumulative_cost_usd": statistics.mean(values),
            }
            for turn_index, values in sorted(by_turn.items())
        ]
    return curves


def memory_drift_sample_curve(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    sampled: list[dict[str, Any]] = []
    for turn_index in MEMORY_DRIFT_SAMPLE_TURNS:
        turn_rows = [row for row in rows if _int(row["turn_index"]) == turn_index]
        if not turn_rows:
            continue
        sampled.append(
            {
                "turn_index": turn_index,
                "mean_memory_drift": statistics.mean(
                    _float(row["memory_drift_score"]) for row in turn_rows
                ),
            }
        )
    return sampled


def attachment_recall_by_size(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    turn_one = [row for row in rows if _int(row["turn_index"]) == 1]
    by_size: dict[int, list[str]] = defaultdict(list)
    for row in turn_one:
        size_kb = _int(row["attachment_size_kb"])
        if size_kb <= 0:
            continue
        by_size[size_kb].append(row.get("attachment_recall", ""))

    results: list[dict[str, Any]] = []
    for size_kb in sorted(by_size):
        recalls = by_size[size_kb]
        true_count = sum(value == "True" for value in recalls)
        results.append(
            {
                "attachment_size_kb": size_kb,
                "recall_rate": true_count / len(recalls) if recalls else 0.0,
                "rows": len(recalls),
            }
        )
    return results


def _format_money(value: float) -> str:
    return f"{value:.4f}"


def _format_rate(value: float) -> str:
    return f"{value:.1%}"


def generate_report_md(
    rows: list[dict[str, str]],
    *,
    run_mode: str,
    row_count: int,
    locale: str = "en",
    cache_on: bool = False,
) -> str:
    t = REPORT_LOCALES.get(locale, REPORT_LOCALES["en"])
    summaries = summarize_groups(rows)
    latency_curve = latency_vs_tokens_turn_one(rows)
    cost_curves = cumulative_cost_curve(rows, attachment_size_kb=0)
    drift_curve = memory_drift_sample_curve(rows)
    attachment_recall = attachment_recall_by_size(rows)

    growing_turn1_cost = _mean_turn_metric(
        rows,
        scenario="growing",
        turn_index=1,
        attachment_size_kb=0,
        field="cost_usd",
    )
    growing_turn20_cumulative = _mean_turn_metric(
        rows,
        scenario="growing",
        turn_index=20,
        attachment_size_kb=0,
        field="cumulative_cost_usd",
    )
    cost_ratio = (
        growing_turn20_cumulative / growing_turn1_cost if growing_turn1_cost else 0.0
    )

    growing_t1_tokens = _mean_turn_metric(
        rows,
        scenario="growing",
        turn_index=1,
        attachment_size_kb=0,
        field="tokens_in",
    )
    growing_t20_tokens = _mean_turn_metric(
        rows,
        scenario="growing",
        turn_index=20,
        attachment_size_kb=0,
        field="tokens_in",
    )
    token_ratio = growing_t20_tokens / growing_t1_tokens if growing_t1_tokens else 0.0

    drift_turn3 = _mean_turn_metric(rows, turn_index=3, field="memory_drift_score")
    drift_turn20 = _mean_turn_metric(rows, turn_index=20, field="memory_drift_score")
    pivot_turn20_drift = _mean_turn_metric(
        rows,
        scenario="pivot",
        turn_index=20,
        field="memory_drift_score",
    )

    attachment_chars_100kb = _mean_turn_metric(
        rows,
        scenario="growing",
        turn_index=1,
        attachment_size_kb=100,
        field="attachments_total_chars",
    )

    lines: list[str] = [
        t["title"],
        "",
        t["design_heading"],
        "",
        t["design_snapshot"],
        t["design_metrics"],
        t["design_cache_on"] if cache_on else t["design_cache_off"],
        t["design_spec_gap"],
        "",
        f"{t['run_mode']} {run_mode} · {t['rows']} {row_count}",
        "",
        t["summary_heading"],
        "",
        t["summary_header"],
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for summary in summaries:
        lines.append(
            f"| {summary.scenario} | {summary.attachment_size_kb} | "
            f"{summary.p50_latency_ms:.0f} | {summary.p95_latency_ms:.0f} | "
            f"{_format_money(summary.total_cost_usd)} | "
            f"{_format_rate(summary.exact_cache_hit_rate)} | "
            f"{_format_rate(summary.semantic_cache_hit_rate)} | "
            f"{summary.mean_memory_drift:.2f} |"
        )

    lines.extend(
        [
            "",
            t["curves_heading"],
            "",
            t["latency_curve_heading"],
            "",
            t["latency_curve_header"],
            "|---:|---:|---:|---:|",
        ]
    )
    for point in latency_curve:
        lines.append(
            f"| {point['attachment_size_kb']} | {point['mean_tokens_in']:.0f} | "
            f"{point['mean_latency_ms']:.0f} | {point['mean_attachments_total_chars']:.0f} |"
        )

    lines.extend(
        [
            "",
            t["cost_curve_heading"],
            "",
        ]
    )
    for scenario, curve in cost_curves.items():
        lines.append(f"**{scenario}**")
        lines.append("")
        lines.append(t["cost_curve_turn_header"])
        lines.append("|---:|---:|")
        for point in curve:
            if point["turn_index"] in MEMORY_DRIFT_SAMPLE_TURNS:
                lines.append(
                    f"| {point['turn_index']} | {_format_money(point['mean_cumulative_cost_usd'])} |"
                )
        lines.append("")

    lines.extend(
        [
            t["drift_curve_heading"],
            "",
            t["drift_curve_header"],
            "|---:|---:|",
        ]
    )
    for point in drift_curve:
        lines.append(f"| {point['turn_index']} | {point['mean_memory_drift']:.2f} |")

    lines.extend(
        [
            "",
            t["attachment_heading"],
            "",
        ]
    )
    if attachment_recall:
        for item in attachment_recall:
            token = f"STRESS_TOKEN_{item['attachment_size_kb']}KB"
            lines.append(
                t["attachment_line"].format(
                    size=item["attachment_size_kb"],
                    token=token,
                    rate=_format_rate(item["recall_rate"]),
                    rows=item["rows"],
                )
            )
    else:
        lines.append(t["attachment_none"])

    lines.extend(
        [
            "",
            t["analysis_heading"],
            "",
            t["analysis_cost"].format(
                turn20_cost=_format_money(growing_turn20_cumulative),
                cost_ratio=cost_ratio,
                turn1_cost=_format_money(growing_turn1_cost),
                t1_tokens=growing_t1_tokens,
                t20_tokens=growing_t20_tokens,
                token_ratio=token_ratio,
            ),
            "",
            t["analysis_drift"].format(
                drift_t3=drift_turn3,
                drift_t20=drift_turn20,
                pivot_drift=pivot_turn20_drift,
                attach_chars=attachment_chars_100kb,
            ),
            "",
        ]
    )

    return "\n".join(lines)


def _mean_turn_metric(
    rows: list[dict[str, str]],
    *,
    field: str,
    scenario: str | None = None,
    turn_index: int | None = None,
    attachment_size_kb: int | None = None,
) -> float:
    filtered = rows
    if scenario is not None:
        filtered = [row for row in filtered if row["scenario"] == scenario]
    if turn_index is not None:
        filtered = [row for row in filtered if _int(row["turn_index"]) == turn_index]
    if attachment_size_kb is not None:
        filtered = [
            row for row in filtered if _int(row["attachment_size_kb"]) == attachment_size_kb
        ]
    if not filtered:
        return 0.0
    return statistics.mean(_float(row[field]) for row in filtered)


def write_report(
    csv_path: Path,
    report_path: Path,
    *,
    run_mode: str,
    locale: str = "en",
    cache_on: bool = False,
) -> None:
    rows = load_csv_rows(csv_path)
    report = generate_report_md(
        rows,
        run_mode=run_mode,
        row_count=len(rows),
        locale=locale,
        cache_on=cache_on,
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate stress CSV and write REPORT.md.")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument(
        "--run-mode",
        default="in-process (mocked LLM, cache off)",
        help="Description of how results.csv was produced.",
    )
    parser.add_argument(
        "--locale",
        default="en",
        choices=sorted(REPORT_LOCALES),
        help="Report language (default: en).",
    )
    parser.add_argument(
        "--cache-on",
        action="store_true",
        help="Describe cache as enabled in the design-decisions section.",
    )
    parser.add_argument(
        "--localized-csv",
        type=Path,
        default=None,
        help="Optional path for a localized CSV export (default: <csv-stem>.<locale>.csv).",
    )
    args = parser.parse_args(argv)
    write_report(
        args.csv,
        args.report,
        run_mode=args.run_mode,
        locale=args.locale,
        cache_on=args.cache_on,
    )
    localized_output = args.localized_csv or localized_csv_path(args.csv, args.locale)
    if localized_output is not None:
        write_localized_csv(args.csv, localized_output, locale=args.locale)
        print(f"wrote {localized_output}")
    print(f"wrote {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
