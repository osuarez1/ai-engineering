import csv
from pathlib import Path

import pytest

from evals.stress.aggregate import load_csv_rows, write_all_outputs
from evals.stress.backup import (
    backup_if_exists,
    backup_results_csv,
    backup_reports,
)
from evals.stress.run import write_csv


def test_backup_if_exists_skips_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("evals.stress.backup.BACKUP_DIR", tmp_path / "backup")
    missing = tmp_path / "results.csv"
    assert backup_if_exists(missing, "results") is None


def test_backup_if_exists_copies_existing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backup"
    monkeypatch.setattr("evals.stress.backup.BACKUP_DIR", backup_dir)
    source = tmp_path / "results.csv"
    source.write_text("scenario,turn_index\ngrowing,1\n", encoding="utf-8")

    destination = backup_if_exists(source, "results", epoch=1_700_000_000)

    assert destination == backup_dir / "results.1700000000.csv"
    assert destination is not None
    assert destination.read_text(encoding="utf-8") == source.read_text(encoding="utf-8")


def test_backup_results_csv_appends_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backup"
    monkeypatch.setattr("evals.stress.backup.BACKUP_DIR", backup_dir)
    monkeypatch.setattr("evals.stress.backup.MANIFEST_PATH", backup_dir / "manifest.jsonl")
    monkeypatch.setattr("evals.stress.backup.epoch_now", lambda: 1_700_000_001)
    source = tmp_path / "results.csv"
    source.write_text("scenario,turn_index\ngrowing,1\n", encoding="utf-8")

    destination = backup_results_csv(source)

    assert destination == backup_dir / "results.1700000001.csv"
    manifest = (backup_dir / "manifest.jsonl").read_text(encoding="utf-8")
    assert '"kind": "results"' in manifest
    assert str(source) in manifest


def test_backup_reports_archives_existing_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backup"
    monkeypatch.setattr("evals.stress.backup.BACKUP_DIR", backup_dir)
    report_en = tmp_path / "REPORT.md"
    report_es = tmp_path / "REPORT.es.md"
    report_en.write_text("# EN", encoding="utf-8")
    report_es.write_text("# ES", encoding="utf-8")

    backed_up = backup_reports(report_en, report_es, epoch=1_700_000_002)

    assert backed_up == [
        backup_dir / "REPORT.1700000002.md",
        backup_dir / "REPORT.es.1700000002.md",
    ]


def test_write_csv_backs_up_existing_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backup_dir = tmp_path / "backup"
    monkeypatch.setattr("evals.stress.backup.BACKUP_DIR", backup_dir)
    monkeypatch.setattr("evals.stress.backup.MANIFEST_PATH", backup_dir / "manifest.jsonl")
    monkeypatch.setattr("evals.stress.backup.epoch_now", lambda: 1_700_000_003)
    output = tmp_path / "results.csv"
    output.write_text("old,data\n", encoding="utf-8")

    write_csv(
        output, [{"scenario": "growing", "attachment_size_kb": 0, "repeat": 0, "turn_index": 1}]
    )

    assert (backup_dir / "results.1700000003.csv").read_text(encoding="utf-8") == "old,data\n"
    rows = list(csv.DictReader(output.open(encoding="utf-8")))
    assert rows[0]["scenario"] == "growing"


def test_load_csv_rows_raises_when_missing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Run the stress test first"):
        load_csv_rows(tmp_path / "missing.csv")


def test_write_all_outputs_generates_en_es_reports_and_csv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backup_dir = tmp_path / "backup"
    monkeypatch.setattr("evals.stress.backup.BACKUP_DIR", backup_dir)
    monkeypatch.setattr("evals.stress.backup.MANIFEST_PATH", backup_dir / "manifest.jsonl")
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
                "attachment_size_kb": "0",
                "repeat": "0",
                "turn_index": "1",
                "latency_ms": "120",
                "tokens_in": "500",
                "cost_usd": "0.01",
                "cumulative_cost_usd": "0.01",
                "cache_hit_kind": "none",
                "memory_drift_score": "1.0",
                "attachment_recall": "",
                "attachments_total_chars": "0",
            }
        )

    report_en = tmp_path / "REPORT.md"
    report_es = tmp_path / "localized" / "REPORT.es.md"
    write_all_outputs(
        csv_path,
        run_mode="test",
        backup=False,
        report_en_path=report_en,
        report_es_path=report_es,
        localized_dir=tmp_path / "localized",
    )

    assert "## Design decisions" in report_en.read_text(encoding="utf-8")
    assert "## Decisiones de diseño" in report_es.read_text(encoding="utf-8")
