"""Glue: load -> clean -> validate -> report."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd

from harmonize_xl.cleaner import Cleaner
from harmonize_xl.config import Config
from harmonize_xl.loader import Loader
from harmonize_xl.models import Issue, RunResult
from harmonize_xl.report import ReportWriter
from harmonize_xl.validator import Validator

logger = logging.getLogger(__name__)


def load_reference(path: Path | None) -> dict[str, str] | None:
    """Read the product reference list (columns: product_code, product_name)."""
    if path is None or not Path(path).exists():
        logger.warning("No reference file: the 'unknown_product' rule is disabled")
        return None
    frame = pd.read_csv(path, dtype=str)
    return dict(zip(frame["product_code"].str.strip().str.upper(), frame["product_name"]))


def issues_to_frame(issues: list[Issue]) -> pd.DataFrame:
    return pd.DataFrame(
        [[i.file, i.row, i.field, i.rule, i.value, i.message] for i in issues],
        columns=["file", "row", "field", "rule", "value", "message"],
    )


class Pipeline:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()

    def run(self, input_dir: Path, output_path: Path, reference_path: Path | None = None) -> RunResult:
        started = time.perf_counter()
        reference = load_reference(reference_path)

        loader = Loader(self.config)
        tables = loader.load_folder(input_dir)
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
        issues_to_frame(issues).to_csv(Path(output_path).with_name(Path(output_path).stem + "_issues.csv"),
                                       index=False)

        elapsed = time.perf_counter() - started
        logger.info("Done: %d valid rows, %d issues in %d rows, %.2fs",
                    len(clean), len(issues), len(bad_rows), elapsed)
        return RunResult(files_read=len({t.file for t in tables}), rows_read=len(raw), clean=clean,
                         issues=issues, elapsed_seconds=elapsed, output_path=Path(output_path),
                         failed_files=loader.failed_files)
