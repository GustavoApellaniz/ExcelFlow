from pathlib import Path

import pytest

from excelflow import __version__
from excelflow.cli import main
from excelflow.sample_data import SampleDataGenerator


def _run(tmp_path: Path, *args: str) -> int:
    return main(["--log-file", str(tmp_path / "logs" / "run.log"), *args])


def test_generate_then_run_writes_report_and_issues_csv(tmp_path, capsys):
    data = tmp_path / "data"
    assert _run(tmp_path, "generate-sample", "--output", str(data), "--rows-per-file", "20") == 0
    out = tmp_path / "out" / "report.xlsx"
    code = _run(tmp_path, "run", "--input", str(data / "raw"), "--output", str(out),
                "--reference", str(data / "reference" / "products.csv"))
    assert code == 0
    assert out.exists() and (tmp_path / "out" / "report_issues.csv").exists()
    assert "Files read       : 5" in capsys.readouterr().out


def test_missing_input_folder_gives_clear_error(tmp_path, capsys):
    code = _run(tmp_path, "run", "--input", str(tmp_path / "nope"), "--no-reference",
                "--output", str(tmp_path / "r.xlsx"))
    assert code == 2
    assert "Input folder not found" in capsys.readouterr().err


def test_missing_reference_file_gives_clear_error(tmp_path, capsys):
    base = SampleDataGenerator(rows_per_file=10).generate(tmp_path / "data")
    code = _run(tmp_path, "run", "--input", str(base / "raw"), "--output", str(tmp_path / "r.xlsx"),
                "--reference", str(tmp_path / "missing.csv"))
    assert code == 2
    assert "Reference file not found" in capsys.readouterr().err


def test_period_start_after_end_is_rejected(tmp_path, capsys):
    base = SampleDataGenerator(rows_per_file=10).generate(tmp_path / "data")
    code = _run(tmp_path, "run", "--input", str(base / "raw"), "--output", str(tmp_path / "r.xlsx"),
                "--no-reference", "--period-start", "2026-10-01", "--period-end", "2026-09-01")
    assert code == 2
    assert "is after" in capsys.readouterr().err


def test_bad_date_argument_is_rejected_by_parser(tmp_path):
    with pytest.raises(SystemExit) as exc:
        _run(tmp_path, "run", "--period-start", "01/09/2026")
    assert exc.value.code == 2


def test_version_flag(capsys):
    with pytest.raises(SystemExit):
        main(["--version"])
    assert __version__ in capsys.readouterr().out
