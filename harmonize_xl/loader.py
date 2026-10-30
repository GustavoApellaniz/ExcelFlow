"""Step 1: find the header row of every sheet and map its columns to the canonical schema."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from harmonize_xl.cleaner import is_blank
from harmonize_xl.config import Config
from harmonize_xl.schema import FIELDS, HeaderMatch, match_row

logger = logging.getLogger(__name__)


@dataclass
class LoadedTable:
    file: str
    sheet: str
    header_row: int                      # Excel row number of the header (1-based)
    frame: pd.DataFrame                  # canonical columns + source_file + source_row
    matches: list[HeaderMatch]
    ignored_headers: list[str] = field(default_factory=list)
    supplier_from_filename: bool = False

    def mapping_rows(self) -> list[dict]:
        """Rows for the 'Mapping' sheet of the report (audit trail of the column matching)."""
        rows = [
            {"file": self.file, "sheet": self.sheet, "header_row": self.header_row,
             "original": m.original, "mapped_to": m.field, "method": m.method, "score": m.score}
            for m in self.matches
        ]
        rows += [
            {"file": self.file, "sheet": self.sheet, "header_row": self.header_row,
             "original": name, "mapped_to": "(ignored)", "method": "-", "score": None}
            for name in self.ignored_headers
        ]
        if self.supplier_from_filename:
            rows.append({"file": self.file, "sheet": self.sheet, "header_row": self.header_row,
                         "original": "(no supplier column)", "mapped_to": "supplier",
                         "method": "file name", "score": None})
        return rows


class Loader:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.failed_files: list[tuple[str, str]] = []

    def load_folder(self, folder: Path) -> list[LoadedTable]:
        files = sorted(p for p in Path(folder).glob("*.xlsx") if not p.name.startswith("~$"))
        if not files:
            raise FileNotFoundError(f"No .xlsx files found in {folder}")
        tables: list[LoadedTable] = []
        for path in files:
            try:
                tables.extend(self.load_file(path))
            except Exception as exc:  # one bad file must not stop the whole run
                logger.error("Could not read %s: %s", path.name, exc)
                self.failed_files.append((path.name, str(exc)))
        return tables

    def load_file(self, path: Path) -> list[LoadedTable]:
        # keep_default_na=False: pandas would silently turn text such as 'n/a' or a product code 'NA'
        # into NaN; here the Cleaner decides what is missing and what is invalid.
        sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=object,
                               keep_default_na=False)
        tables = []
        for sheet_name, raw in sheets.items():
            found = self._find_header(raw)
            if found is None:
                logger.warning("%s / %s: no recognisable header row, sheet skipped",
                               path.name, sheet_name)
                continue
            header_index, mapping = found
            table = self._build_table(path, str(sheet_name), raw, header_index, mapping)
            logger.info("%s / %s: header at row %d, %d columns mapped, %d data rows",
                        path.name, sheet_name, table.header_row, len(mapping), len(table.frame))
            tables.append(table)
        return tables

    def _find_header(self, raw: pd.DataFrame):
        best_index, best_map = None, {}
        for i in range(min(self.config.header_scan_rows, len(raw))):
            mapping = match_row(raw.iloc[i].tolist(), self.config.fuzzy_cutoff)
            if len(mapping) > len(best_map):
                best_index, best_map = i, mapping
        if best_index is None or len(best_map) < self.config.min_header_matches:
            return None
        return best_index, best_map

    def _build_table(self, path: Path, sheet: str, raw: pd.DataFrame,
                     header_index: int, mapping: dict[int, HeaderMatch]) -> LoadedTable:
        header_cells = raw.iloc[header_index].tolist()
        body = raw.iloc[header_index + 1:]
        body = body[~body.apply(lambda row: all(is_blank(v) for v in row), axis=1)]

        frame = pd.DataFrame(index=body.index, columns=list(FIELDS), dtype=object)
        for column_index, match in mapping.items():
            frame[match.field] = body.iloc[:, column_index]

        supplier_from_filename = "supplier" not in {m.field for m in mapping.values()}
        if supplier_from_filename:
            fallback = path.stem.replace("_", " ").replace("-", " ").title()
            frame["supplier"] = fallback
            logger.info("%s: no supplier column, using file name '%s'", path.name, fallback)

        frame["source_file"] = path.name
        frame["source_row"] = body.index + 1      # raw index 0 == Excel row 1
        ignored = [str(c) for i, c in enumerate(header_cells)
                   if i not in mapping and isinstance(c, str) and c.strip()]
        return LoadedTable(path.name, sheet, header_index + 1, frame,
                           list(m for m in mapping.values()), ignored, supplier_from_filename)
