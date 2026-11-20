"""Glue: load -> clean -> validate -> report."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd

from excelflow.cleaner import Cleaner
from excelflow.config import Config
from excelflow.loader import Loader
from excelflow.models import Issue, RunResult
from excelflow.report import ReportWriter
from excelflow.validator import Validator

logger = logging.getLogger(__name__)


def load_reference(path: Path | None) -> dict[str, str] | None:
    """Read the product reference list (columns: product_code, product_name)."""
    if path is None or not Path(path).exists():
        logger.warning("No reference file: the 'unknown_product' rule is disabled")
        return None
    # utf-8-sig: CSV files saved by Excel often start with a byte-order mark.
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    missing = {"product_code", "product_name"} - set(frame.columns)
    if missing:
        raise ValueError(f"Reference file {Path(path).name} is missing column(s): "
                         f"{', '.join(sorted(missing))}")
    codes = frame["product_code"].str.replace(" ", "").str.upper()
    return {code: name for code, name in zip(codes, frame["product_name"]) if code}


def issues_to_frame(issues: list[Issue]) -> pd.DataFrame:
    return pd.DataFrame(
        [[i.file, i.row, i.field, i.rule, i.value, i.message] for i in issues],
        columns=["file", "row", "field", "rule", "value", "message"],
    )


def issues_csv_path(report_path: Path) -> Path:
    """report.xlsx -> report_issues.csv (next to the workbook)."""
    return report_path.with_name(report_path.stem + "_issues.csv")


class Pipeline:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()

    def run(self, input_dir: Path, output_path: Path, reference_path: Path | None = None) -> RunResult:
        if self.config.period_start > self.config.period_end:
            raise ValueError(f"Period start {self.config.period_start} is after "
                             f"period end {self.config.period_end}")
        started = time.perf_counter()
        reference = load_reference(reference_path)

        loader = Loader(self.config)
        tables = loader.load_folder(input_dir)
        if not tables:
            details = "; ".join(f"{name}: {err}" for name, err in loader.failed_files)
            raise ValueError(f"No readable table found in {input_dir}"
                             + (f" ({details})" if details else ""))
        raw = pd.concat([t.frame for t in tables], ignore_index=True)
        logger.info("Loaded %d rows from %d sheets", len(raw), len(tables))

        clean_all, parse_issues = Cleaner().clean(raw)
        rule_issues = Validator(self.config, reference).validate(clean_all, parse_issues)
        issues = parse_issues + rule_issues

        bad_rows = {(i.file, i.row) for i in issues}
        keep = [(f, r) not in bad_rows for f, r in zip(clean_all["source_file"], clean_all["source_row"])]
        clean = clean_all[keep].reset_index(drop=True)

        mapping_rows = [row for t in tables for row in t.mapping_rows()]
        ReportWriter(self.config, reference).write(
            Path(output_path), clean, issues, mapping_rows,
            files_read=len({t.file for t in tables}), rows_read=len(raw))
        issues_to_frame(issues).to_csv(issues_csv_path(Path(output_path)), index=False)

        elapsed = time.perf_counter() - started
        logger.info("Done: %d valid rows, %d issues in %d rows, %.2fs",
                    len(clean), len(issues), len(bad_rows), elapsed)
        return RunResult(files_read=len({t.file for t in tables}), rows_read=len(raw), clean=clean,
                         issues=issues, elapsed_seconds=elapsed, output_path=Path(output_path),
                         failed_files=loader.failed_files)
