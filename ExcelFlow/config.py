from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Config:
    """Settings shared by every step of the pipeline."""

    period_start: date = date(2026, 9, 1)
    period_end: date = date(2026, 9, 30)
    fuzzy_cutoff: float = 0.8      # minimum similarity (0-1) to accept a misspelled header
    header_scan_rows: int = 15     # how many rows to search for the header row
    min_header_matches: int = 4    # fields that must be recognised to accept a header row
