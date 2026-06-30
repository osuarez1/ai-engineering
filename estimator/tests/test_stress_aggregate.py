import csv
from pathlib import Path

from evals.stress.aggregate import (
    attachment_recall_by_size,
    generate_report_md,
    load_csv_rows,
    localize_csv_row,
    localized_csv_path,
    percentile,
    summarize_groups,
    write_localized_csv,
)


def test_percentile_interpolates_between_values() -> None:
    assert percentile([10.0, 20.0, 30.0, 40.0], 50) == 25.0
    assert percentile([10.0, 20.0, 30.0, 40.0], 95) == 38.5


def test_summarize_groups_computes_latency_and_cache_rates() -> None:
    rows = [
        {
            "scenario": "growing",
            "attachment_size_kb": "0",
            "latency_ms": "100",
            "cost_usd": "0.01",
            "cache_hit_kind": "none",
            "memory_drift_score": "1.0",
        },
        {
            "scenario": "growing",
            "attachment_size_kb": "0",
            "latency_ms": "300",
            "cost_usd": "0.02",
            "cache_hit_kind": "exact",
            "memory_drift_score": "0.5",
        },
    ]
    summaries = summarize_groups(rows)
    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.p50_latency_ms == 200.0
    assert summary.total_cost_usd == 0.03
    assert summary.exact_cache_hit_rate == 0.5
    assert summary.mean_memory_drift == 0.75


def test_generate_report_md_includes_required_sections(tmp_path: Path) -> None:
    csv_path = tmp_path / "results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "scenario",
                "attachment_size_kb",
                "repeat",
                "turn_index",
                "latency_ms",
                "tokens_in",
                "cost_usd",
                "cumulative_cost_usd",
                "cache_hit_kind",
                "memory_drift_score",
                "attachment_recall",
                "attachments_total_chars",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "scenario": "growing",
                "attachment_size_kb": "5",
                "repeat": "0",
                "turn_index": "1",
                "latency_ms": "120",
                "tokens_in": "500",
                "cost_usd": "0.01",
                "cumulative_cost_usd": "0.01",
                "cache_hit_kind": "none",
                "memory_drift_score": "1.0",
                "attachment_recall": "True",
                "attachments_total_chars": "1000",
            }
        )

    report = generate_report_md(load_csv_rows(csv_path), run_mode="test", row_count=1)
    assert "## Design decisions" in report
    assert "## Summary table" in report
    assert "## Attachment recall" in report
    assert "## Analysis" in report
    assert attachment_recall_by_size(load_csv_rows(csv_path))[0]["recall_rate"] == 1.0


def test_write_localized_csv_uses_spanish_headers(tmp_path: Path) -> None:
    csv_path = tmp_path / "results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "scenario",
                "attachment_size_kb",
                "repeat",
                "turn_index",
                "session_id",
                "cache_hit_kind",
                "last_resolved_tier",
                "latency_budget_passed",
                "attachment_recall",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "scenario": "growing",
                "attachment_size_kb": "5",
                "repeat": "0",
                "turn_index": "1",
                "session_id": "abc",
                "cache_hit_kind": "exact",
                "last_resolved_tier": "medium",
                "latency_budget_passed": "True",
                "attachment_recall": "False",
            }
        )

    output = tmp_path / "results.es.csv"
    write_localized_csv(csv_path, output, locale="es")

    rows = list(csv.DictReader(output.open(encoding="utf-8")))
    assert list(rows[0].keys()) == [
        "escenario",
        "adjunto_kib",
        "repeticion",
        "turno",
        "id_sesion",
        "tipo_acierto_cache",
        "ultimo_nivel_resuelto",
        "presupuesto_latencia_ok",
        "recuperacion_adjunto",
    ]
    assert rows[0]["escenario"] == "growing"
    assert rows[0]["tipo_acierto_cache"] == "exacto"
    assert rows[0]["ultimo_nivel_resuelto"] == "medio"
    assert rows[0]["presupuesto_latencia_ok"] == "verdadero"
    assert rows[0]["recuperacion_adjunto"] == "falso"
    assert localize_csv_row({"cache_hit_kind": "semantic"}, "es") == {
        "tipo_acierto_cache": "semantico"
    }


def test_localized_csv_path_strips_en_suffix_before_adding_locale() -> None:
    english = Path("evals/stress/results.csv")
    assert localized_csv_path(english, "en") is None
    assert localized_csv_path(english, "es") == Path("evals/stress/results.es.csv")
    localized_en = Path("evals/stress/results.en.csv")
    assert localized_csv_path(localized_en, "es") == Path("evals/stress/results.es.csv")
