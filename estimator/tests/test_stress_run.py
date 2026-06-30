import csv
from pathlib import Path

from evals.stress.run import CSV_COLUMNS, main


def test_stress_run_inprocess_writes_expected_csv_rows(tmp_path: Path) -> None:
    output = tmp_path / "results.csv"
    row_count = main(
        [
            "--scenarios",
            "growing",
            "--attachment-sizes",
            "0,5",
            "--repeats",
            "1",
            "--max-turns",
            "2",
            "--output",
            str(output),
        ],
    )

    assert row_count == 4
    assert output.exists()

    rows = list(csv.DictReader(output.open(encoding="utf-8")))
    assert len(rows) == 4
    assert set(rows[0].keys()) == set(CSV_COLUMNS)
    assert all(row["scenario"] == "growing" for row in rows)
    assert {row["attachment_size_kb"] for row in rows} == {"0", "5"}
    assert all(row["turn_index"] in {"1", "2"} for row in rows)
    assert rows[0]["latency_budget_passed"] == "True"
    assert rows[0]["cost_budget_passed"] == "True"


def test_stress_run_attachment_recall_on_turn_one_with_pdf(tmp_path: Path) -> None:
    output = tmp_path / "results.csv"
    main(
        [
            "--scenarios",
            "growing",
            "--attachment-sizes",
            "5",
            "--repeats",
            "1",
            "--max-turns",
            "1",
            "--output",
            str(output),
        ],
    )

    rows = list(csv.DictReader(output.open(encoding="utf-8")))
    assert len(rows) == 1
    assert rows[0]["turn_index"] == "1"
    assert rows[0]["attachment_recall"] == "True"
    assert rows[0]["attachment_size_kb"] == "5"
