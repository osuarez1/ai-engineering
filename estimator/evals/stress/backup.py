"""Backup helpers for stress-test results and derived reports."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

BACKUP_DIR = Path("evals/stress/backup")
MANIFEST_PATH = BACKUP_DIR / "manifest.jsonl"


def epoch_now() -> int:
    return int(time.time())


def backup_if_exists(source: Path, prefix: str, *, epoch: int | None = None) -> Path | None:
    """Copy *source* to ``backup/{prefix}.{epoch}{suffix}`` when the file exists."""
    if not source.is_file():
        return None
    stamp = epoch_now() if epoch is None else epoch
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    destination = BACKUP_DIR / f"{prefix}.{stamp}{source.suffix}"
    shutil.copy2(source, destination)
    return destination


def backup_results_csv(results_path: Path) -> Path | None:
    """Archive the current results CSV before a new stress run overwrites it."""
    destination = backup_if_exists(results_path, "results")
    if destination is None:
        return None
    append_manifest(
        {
            "kind": "results",
            "epoch": _epoch_from_name(destination),
            "source": str(results_path),
            "backup": str(destination),
        }
    )
    return destination


def backup_reports(
    report_en: Path,
    report_es: Path,
    *,
    epoch: int | None = None,
) -> list[Path]:
    """Archive existing reports before aggregate regenerates them."""
    stamp = epoch_now() if epoch is None else epoch
    backed_up: list[Path] = []
    for source, prefix in ((report_en, "REPORT.en"), (report_es, "REPORT.es")):
        destination = backup_if_exists(source, prefix, epoch=stamp)
        if destination is not None:
            backed_up.append(destination)
    return backed_up


def append_manifest(entry: dict[str, Any]) -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _epoch_from_name(path: Path) -> int:
    stem = path.stem
    return int(stem.rsplit(".", 1)[-1])
