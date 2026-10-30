from datetime import date, datetime

import pandas as pd

from harmonize_xl.cleaner import Cleaner, ParseError, is_blank, parse_date, parse_number
from harmonize_xl.models import INVALID_FORMAT


def _fails(func, value) -> bool:
    try:
        func(value)
    except ParseError:
        return True
    return False


def test_parse_date_accepts_common_formats():
    assert parse_date(datetime(2026, 9, 3, 0, 0)) == date(2026, 9, 3)
    assert parse_date("2026-09-03") == date(2026, 9, 3)
    assert parse_date("03/09/2026") == date(2026, 9, 3)      # day first
    assert parse_date(" 03.09.2026 ") == date(2026, 9, 3)
    assert parse_date(46268) == date(2026, 9, 3)             # Excel serial number


def test_parse_date_rejects_impossible_dates():
    assert _fails(parse_date, "31/02/2026")
    assert _fails(parse_date, "TBD")


def test_parse_number_handles_european_and_us_formats():
    assert parse_number(12) == 12.0
    assert parse_number("1.250,5") == 1250.5
    assert parse_number("1,250.5") == 1250.5
    assert parse_number("0,225") == 0.225
    assert parse_number("€ 3,5 kg") == 3.5
    assert parse_number("-120,5") == -120.5


def test_parse_number_rejects_text():
    assert _fails(parse_number, "abc")
    assert _fails(parse_number, "n/a")
    assert _fails(parse_number, "--")
    assert _fails(parse_number, True)


def test_is_blank():
    assert is_blank(None) and is_blank("") and is_blank("   ") and is_blank(float("nan"))
    assert not is_blank(0) and not is_blank("0")


def _raw(**overrides) -> pd.DataFrame:
    row = {"delivery_date": "2026-09-03", "supplier": "Ferme Lenoir", "product_code": "wht01 ",
           "product_name": "Soft  wheat", "quantity_kg": "1.250,5", "unit_price_eur": "0,225",
           "source_file": "a.xlsx", "source_row": 5}
    row.update(overrides)
    return pd.DataFrame([row], dtype=object)


def test_cleaner_normalises_values():
    clean, issues = Cleaner().clean(_raw())
    rec = clean.iloc[0]
    assert issues == []
    assert rec["product_code"] == "WHT01"
    assert rec["product_name"] == "Soft wheat"
    assert rec["quantity_kg"] == 1250.5 and rec["unit_price_eur"] == 0.225
    assert rec["delivery_date"] == date(2026, 9, 3)


def test_cleaner_reports_unreadable_cell_and_keeps_row_number():
    clean, issues = Cleaner().clean(_raw(quantity_kg="abc"))
    assert len(issues) == 1
    assert (issues[0].file, issues[0].row, issues[0].field, issues[0].rule) == \
           ("a.xlsx", 5, "quantity_kg", INVALID_FORMAT)
    assert clean.iloc[0]["quantity_kg"] is None


def test_cleaner_unifies_supplier_spelling():
    frame = pd.concat([_raw(supplier="FERME LENOIR", source_row=1),
                       _raw(supplier="Ferme Lenoir", source_row=2)], ignore_index=True)
    clean, _ = Cleaner().clean(frame)
    assert set(clean["supplier"]) == {"Ferme Lenoir"}
