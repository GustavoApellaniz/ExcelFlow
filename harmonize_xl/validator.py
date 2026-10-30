"""Step 3: business rules. Every failed rule becomes one Issue; rows with issues are excluded."""

from __future__ import annotations

from harmonize_xl.cleaner import is_blank
from harmonize_xl.config import Config
from harmonize_xl.models import (
    DATE_OUT_OF_PERIOD, DUPLICATE_ROW, MISSING_VALUE, NON_POSITIVE, UNKNOWN_PRODUCT, Issue,
)
import pandas as pd

from harmonize_xl.schema import REQUIRED_FIELDS


class Validator:
    def __init__(self, config: Config, reference: dict[str, str] | None = None) -> None:
        self.config = config
        self.reference = reference     # {product_code: product_name}; None disables that rule

    def validate(self, clean: pd.DataFrame, earlier_issues: list[Issue]) -> list[Issue]:
        already_flagged = {(i.file, i.row, i.field) for i in earlier_issues}
        issues: list[Issue] = []
        first_seen: dict[tuple, tuple[str, int]] = {}

        for rec in clean.to_dict("records"):
            file, row = rec["source_file"], int(rec["source_row"])
            found: list[Issue] = []

            for name in REQUIRED_FIELDS:
                if is_blank(rec[name]) and (file, row, name) not in already_flagged:
                    found.append(Issue(file, row, name, MISSING_VALUE, "",
                                       f"Required field '{name}' is empty"))

            for name in ("quantity_kg", "unit_price_eur"):
                value = rec[name]
                if not is_blank(value) and value <= 0:
                    found.append(Issue(file, row, name, NON_POSITIVE, str(value),
                                       f"'{name}' must be greater than zero"))

            code = rec["product_code"]
            if self.reference is not None and not is_blank(code) and code not in self.reference:
                found.append(Issue(file, row, "product_code", UNKNOWN_PRODUCT, code,
                                   "Product code is not in the reference list"))

            day = rec["delivery_date"]
            if not is_blank(day) and not (self.config.period_start <= day <= self.config.period_end):
                found.append(Issue(file, row, "delivery_date", DATE_OUT_OF_PERIOD, day.isoformat(),
                                   f"Date outside {self.config.period_start} to {self.config.period_end}"))

            has_earlier = any(i.file == file and i.row == row for i in earlier_issues)
            if not found and not has_earlier:
                key = (rec["supplier"], day, code, round(rec["quantity_kg"], 3),
                       round(rec["unit_price_eur"], 4))
                if key in first_seen:
                    origin_file, origin_row = first_seen[key]
                    found.append(Issue(file, row, "all", DUPLICATE_ROW, "",
                                       f"Duplicate of {origin_file} row {origin_row}"))
                else:
                    first_seen[key] = (file, row)
            issues.extend(found)
        return issues
