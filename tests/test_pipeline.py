from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook

from harmonize_xl.benchmark import evaluate, read_ground_truth
from harmonize_xl.config import Config
from harmonize_xl.loader import Loader
from harmonize_xl.pipeline import Pipeline
from harmonize_xl.sample_data import SampleDataGenerator


def test_end_to_end_detects_every_injected_error_and_nothing_else(tmp_path):
    base = SampleDataGenerator(seed=7, rows_per_file=60).generate(tmp_path / "data")
    result = Pipeline().run(base / "raw", tmp_path / "out" / "report.xlsx",
                            base / "reference" / "products.csv")
    evaluation = evaluate(result.issues, read_ground_truth(base / "ground_truth.csv"))
    assert evaluation.recall == 1.0
    assert evaluation.precision == 1.0
    assert result.files_read == 5
    assert result.valid_rows + result.rows_with_issues == result.rows_read


def test_report_has_expected_sheets_and_live_formulas(tmp_path):
    base = SampleDataGenerator(seed=1, rows_per_file=30).generate(tmp_path / "data")
    out = tmp_path / "report.xlsx"
    Pipeline().run(base / "raw", out, base / "reference" / "products.csv")
    wb = load_workbook(out)
    assert wb.sheetnames == ["Summary", "Data", "Issues", "Mapping"]
    assert wb["Data"]["G2"].value == "=E2*F2"                   # total is a formula, not a number
    assert str(wb["Summary"]["B10"].value).startswith("=SUM(")
    assert (tmp_path / "report_issues.csv").exists()


def test_header_is_found_below_title_rows_and_row_numbers_are_excel_rows(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws["A3"] = "Report title"                                    # rows 1-2 empty, title in row 3
    ws.append(["Date", "Supplier", "Code", "Quantity", "Price"])  # header lands in row 4
    ws.append([date(2026, 9, 2), "Farm A", "WHT01", 100, 0.2])   # Excel row 5
    wb.save(tmp_path / "x.xlsx")

    table = Loader(Config()).load_file(tmp_path / "x.xlsx")[0]
    assert table.header_row == 4
    assert table.frame["source_row"].tolist() == [5]


def test_one_unreadable_file_does_not_stop_the_run(tmp_path):
    base = SampleDataGenerator(seed=3, rows_per_file=20).generate(tmp_path / "data")
    (base / "raw" / "broken.xlsx").write_text("this is not an excel file")
    result = Pipeline().run(base / "raw", tmp_path / "report.xlsx", base / "reference" / "products.csv")
    assert [name for name, _ in result.failed_files] == ["broken.xlsx"]
    assert result.files_read == 5


def test_empty_folder_raises_clear_error(tmp_path):
    (tmp_path / "empty").mkdir()
    try:
        Pipeline().run(tmp_path / "empty", tmp_path / "r.xlsx")
    except FileNotFoundError as exc:
        assert "No .xlsx files" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")
