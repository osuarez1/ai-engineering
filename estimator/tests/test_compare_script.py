import importlib.util
import runpy
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "compare.py"


def test_compare_script_entrypoint() -> None:
    with patch("app.embedding_pipeline.compare_cli.main", return_value=0) as mock_main:
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_path(str(SCRIPT), run_name="__main__")
    assert exc_info.value.code == 0
    mock_main.assert_called_once()


def test_compare_script_inserts_root_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    root = str(ROOT)
    monkeypatch.setattr(sys, "path", ["/tmp"])
    with patch("app.embedding_pipeline.compare_cli.main", return_value=0):
        spec = importlib.util.spec_from_file_location("compare_script_module", SCRIPT)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    assert root in sys.path
