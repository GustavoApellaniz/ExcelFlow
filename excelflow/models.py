from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

# Validation rule names (also used as ground-truth labels in the sample data).
MISSING_VALUE = "missing_value"
INVALID_FORMAT = "invalid_format"
NON_POSITIVE = "non_positive_value"
UNKNOWN_PRODUCT = "unknown_product"
DATE_OUT_OF_PERIOD = "date_out_of_period"
DUPLICATE_ROW = "duplicate_row"

ALL_RULES = (
    MISSING_VALUE,
    INVALID_FORMAT,
    NON_POSITIVE,
    UNKNOWN_PRODUCT,
    DATE_OUT_OF_PERIOD,
    DUPLICATE_ROW,
)


@dataclass(frozen=True)
class Issue:
    """One problem found in one cell (or one row) of a source file."""

    file: str
    row: int          # Excel row number in the source file (1-based)
    field: str
    rule: str
    value: str
    message: str


@dataclass
class RunResult:
    """Everything produced by one pipeline run."""

    files_read: int
    rows_read: int
    clean: pd.DataFrame           # rows that passed every rule
    issues: list[Issue]
    elapsed_seconds: float
    output_path: Path
    failed_files: list[tuple[str, str]] = field(default_factory=list)

    @property
    def valid_rows(self) -> int:
        return len(self.clean)

    @property
    def rows_with_issues(self) -> int:
        return len({(i.file, i.row) for i in self.issues})
