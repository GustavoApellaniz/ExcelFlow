"""Step 2: convert raw cell values into proper types and normalise text."""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from datetime import date, datetime

import pandas as pd
from openpyxl.utils.datetime import from_excel

from harmonize_xl.models import INVALID_FORMAT, Issue
from harmonize_xl.schema import FIELDS

logger = logging.getLogger(__name__)

# Day-first formats are tried before anything else (European convention).
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d")


class ParseError(ValueError):
    """The cell has content, but it cannot be read as the expected type."""


def is_blank(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if value is pd.NaT:
        return True
    return isinstance(value, str) and not value.strip()


def parse_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool) and 20000 < value < 80000:
        return from_excel(value).date()           # Excel serial number
    if isinstance(value, str):
        text = value.strip()
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
    raise ParseError(f"cannot read '{value}' as a date")


def parse_number(value: object) -> float:
    """Read 1250.5, '1.250,5', '1,250.5', '0,225' or '€ 3,5 kg'.

    Rule: if only one kind of separator appears, it is the decimal separator.
    """
    if isinstance(value, bool):
        raise ParseError(f"cannot read '{value}' as a number")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = re.sub(r"[^\d,.\-+]", "", value)
        if "," in text and "." in text:
            decimal = "," if text.rfind(",") > text.rfind(".") else "."
            thousands = "." if decimal == "," else ","
            text = text.replace(thousands, "").replace(decimal, ".")
        elif "," in text:
            text = text.replace(",", ".")
        try:
            return float(text)
        except ValueError:
            pass
    raise ParseError(f"cannot read '{value}' as a number")


def _text(value: object) -> str | None:
    return None if is_blank(value) else " ".join(str(value).split())


def supplier_spellings(series: pd.Series) -> dict[str, str]:
    """Map 'FERME LENOIR' and 'Ferme Lenoir' to one spelling (mixed case preferred, then most common)."""
    groups: dict[str, Counter] = {}
    for value in series:
        text = _text(value)
        if text:
            groups.setdefault(text.casefold(), Counter())[text] += 1
    return {key: max(counts, key=lambda t: (not t.isupper(), counts[t]))
            for key, counts in groups.items()}


class Cleaner:
    """Blank cells become None (the Validator reports them); unreadable cells become Issues."""

    def clean(self, raw: pd.DataFrame) -> tuple[pd.DataFrame, list[Issue]]:
        spellings = supplier_spellings(raw["supplier"])
        records: list[dict] = []
        issues: list[Issue] = []
        for rec in raw.to_dict("records"):
            file, row = rec["source_file"], int(rec["source_row"])
            out: dict = {"source_file": file, "source_row": row}

            for name, parser in (("delivery_date", parse_date),
                                 ("quantity_kg", parse_number),
                                 ("unit_price_eur", parse_number)):
                value = rec[name]
                if is_blank(value):
                    out[name] = None
                    continue
                try:
                    out[name] = parser(value)
                except ParseError as exc:
                    out[name] = None
                    issues.append(Issue(file, row, name, INVALID_FORMAT, str(value), str(exc)))

            supplier = _text(rec["supplier"])
            code = _text(rec["product_code"])
            out["supplier"] = spellings[supplier.casefold()] if supplier else None
            out["product_code"] = code.replace(" ", "").upper() if code else None
            out["product_name"] = _text(rec["product_name"])
            records.append(out)

        columns = list(FIELDS) + ["source_file", "source_row"]
        return pd.DataFrame(records, columns=columns, dtype=object), issues
