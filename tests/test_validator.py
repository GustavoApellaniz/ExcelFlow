from datetime import date

import pandas as pd

from harmonize_xl.config import Config
from harmonize_xl.models import (
    DATE_OUT_OF_PERIOD, DUPLICATE_ROW, MISSING_VALUE, NON_POSITIVE, UNKNOWN_PRODUCT, Issue,
)
from harmonize_xl.validator import Validator

REFERENCE = {"WHT01": "Soft wheat"}


def _frame(*rows: dict) -> pd.DataFrame:
    base = {"delivery_date": date(2026, 9, 3), "supplier": "Ferme Lenoir", "product_code": "WHT01",
            "product_name": None, "quantity_kg": 1000.0, "unit_price_eur": 0.22,
            "source_file": "a.xlsx", "source_row": 2}
    records = []
    for i, override in enumerate(rows):
        rec = dict(base, source_row=2 + i)
        rec.update(override)
        records.append(rec)
    return pd.DataFrame(records, dtype=object)


def _rules(*rows: dict, earlier=None) -> list[str]:
    issues = Validator(Config(), REFERENCE).validate(_frame(*rows), earlier or [])
    return [i.rule for i in issues]


def test_clean_row_has_no_issues():
    assert _rules({}) == []


def test_missing_required_value():
    assert _rules({"supplier": None}) == [MISSING_VALUE]


def test_missing_value_already_reported_by_cleaner_is_not_repeated():
    earlier = [Issue("a.xlsx", 2, "quantity_kg", "invalid_format", "abc", "x")]
    assert _rules({"quantity_kg": None}, earlier=earlier) == []


def test_non_positive_quantity_and_price():
    assert _rules({"quantity_kg": 0.0}) == [NON_POSITIVE]
    assert _rules({"unit_price_eur": -1.0}) == [NON_POSITIVE]


def test_unknown_product():
    assert _rules({"product_code": "ZZZ99"}) == [UNKNOWN_PRODUCT]


def test_without_reference_the_product_rule_is_off():
    issues = Validator(Config(), None).validate(_frame({"product_code": "ZZZ99"}), [])
    assert issues == []


def test_date_outside_period():
    assert _rules({"delivery_date": date(2026, 8, 31)}) == [DATE_OUT_OF_PERIOD]
    assert _rules({"delivery_date": date(2026, 10, 1)}) == [DATE_OUT_OF_PERIOD]
    assert _rules({"delivery_date": date(2026, 9, 30)}) == []        # boundary is inclusive


def test_duplicate_is_flagged_on_second_occurrence_only():
    issues = Validator(Config(), REFERENCE).validate(_frame({}, {}), [])
    assert [(i.row, i.rule) for i in issues] == [(3, DUPLICATE_ROW)]
    assert "row 2" in issues[0].message
