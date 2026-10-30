"""Generates realistic, deliberately messy supplier files plus a ground-truth list of injected errors.

The ground truth is what makes the tool measurable: we know exactly which rows are wrong,
so precision and recall of the validation can be computed (see benchmark.py).
"""

from __future__ import annotations

import csv
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from openpyxl import Workbook

from harmonize_xl.models import (
    DATE_OUT_OF_PERIOD, DUPLICATE_ROW, INVALID_FORMAT, MISSING_VALUE, NON_POSITIVE, UNKNOWN_PRODUCT,
)

PRODUCTS = [  # code, name, typical price EUR/kg (synthetic)
    ("WHT01", "Soft wheat", 0.22), ("BRL02", "Barley", 0.20), ("CRN03", "Corn", 0.21),
    ("POT04", "Potatoes", 0.35), ("SUG05", "Sugar beet", 0.05), ("APL06", "Apples", 0.80),
    ("CAR07", "Carrots", 0.45), ("ONI08", "Onions", 0.40),
]

PERIOD_START, PERIOD_END = date(2026, 9, 1), date(2026, 9, 30)
INJECTED_RULES = [MISSING_VALUE, INVALID_FORMAT, NON_POSITIVE, UNKNOWN_PRODUCT, DATE_OUT_OF_PERIOD]


@dataclass
class FileSpec:
    filename: str
    sheet: str
    suppliers: list[str]
    headers: dict[str, str]                 # canonical field -> header text in this file
    date_style: str                         # "date" | "dmy_text" | "iso_text"
    number_style: str                       # "number" | "comma_text"
    title_rows: list[str] = field(default_factory=list)
    extra_column: str | None = None


SPECS = [
    FileSpec("cooperative_normandie.xlsx", "Livraisons",
             ["Ferme du Val", "Ferme Lenoir", "GAEC des Prés"],
             {"delivery_date": "Date livraison", "supplier": "Fournisseur",
              "product_code": "Code produit", "product_name": "Produit",
              "quantity_kg": "Quantité kg", "unit_price_eur": "Prix unitaire"},
             "date", "number",
             ["Coopérative Normandie - Relevé des livraisons", "Période : septembre 2026", ""]),
    FileSpec("fazenda_sul.xlsx", "Entregas",
             ["Fazenda Boa Vista", "Sítio Água Clara", "Granja Três Irmãos"],
             {"delivery_date": "Data entrega", "supplier": "Fornecedor",
              "product_code": "Código produto", "product_name": "Produto",
              "quantity_kg": "Quantidade kg", "unit_price_eur": "Preço unitário"},
             "dmy_text", "comma_text", ["Relatório mensal de entregas"]),
    FileSpec("green_farms_uk.xlsx", "Deliveries",
             ["Green Acres", "Hillside Farm", "Oakfield Growers"],
             {"delivery_date": "Delivery Date", "supplier": "Supplier",
              "product_code": "Product Code", "product_name": "Product Name",
              "quantity_kg": "Qty kg", "unit_price_eur": "Unit Price EUR"},
             "iso_text", "number", [], "Notes"),
    FileSpec("agro_iberia.xlsx", "Sheet1",
             ["Agro Iberia Norte", "Agro Iberia Sur"],
             {"delivery_date": "Delivry date", "supplier": "Suplier",
              "product_code": "Product code", "product_name": "Produit",
              "quantity_kg": "Quantitiy kg", "unit_price_eur": "Unit prise"},
             "dmy_text", "number", ["Agro Iberia - export ERP"]),
    FileSpec("bio_nord.xlsx", "Export",
             [],  # no supplier column: the file name is used as supplier
             {"delivery_date": "Date", "product_code": "Code",
              "product_name": "Désignation", "quantity_kg": "Quantité (kg)",
              "unit_price_eur": "Prix unitaire (€)"},
             "date", "comma_text", ["Bio Nord", "Export du 30/09/2026", ""]),
]

COLUMN_ORDERS = {
    "cooperative_normandie.xlsx": ["delivery_date", "supplier", "product_code", "product_name",
                                   "quantity_kg", "unit_price_eur"],
    "fazenda_sul.xlsx": ["delivery_date", "supplier", "product_code", "product_name",
                         "quantity_kg", "unit_price_eur"],
    "green_farms_uk.xlsx": ["supplier", "delivery_date", "product_code", "product_name",
                            "quantity_kg", "unit_price_eur"],
    "agro_iberia.xlsx": ["product_code", "product_name", "delivery_date", "supplier",
                         "unit_price_eur", "quantity_kg"],
    "bio_nord.xlsx": ["delivery_date", "product_code", "product_name", "quantity_kg",
                      "unit_price_eur"],
}


def _fmt_date(value: date, style: str):
    if style == "date":
        return datetime(value.year, value.month, value.day)
    if style == "dmy_text":
        return value.strftime("%d/%m/%Y")
    return value.isoformat()


def _fmt_quantity(value: float, style: str):
    if style == "number":
        return value
    return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")   # 1.250,5


def _fmt_price(value: float, style: str):
    return value if style == "number" else f"{value:.3f}".replace(".", ",")          # 0,225


class SampleDataGenerator:
    def __init__(self, seed: int = 42, rows_per_file: int = 130) -> None:
        self.rng = random.Random(seed)
        self.rows_per_file = rows_per_file
        self.used_keys: set[tuple] = set()

    # ---- public ----------------------------------------------------------------------------
    def generate(self, base_dir: Path) -> Path:
        base_dir = Path(base_dir)
        raw_dir = base_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / "reference").mkdir(parents=True, exist_ok=True)

        with open(base_dir / "reference" / "products.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["product_code", "product_name"])
            writer.writerows([[code, name] for code, name, _ in PRODUCTS])

        truth: list[tuple[str, int, str]] = []
        for spec in SPECS:
            truth.extend(self._write_file(spec, raw_dir))

        with open(base_dir / "ground_truth.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["file", "row", "rule"])
            writer.writerows(sorted(truth))
        return base_dir

    # ---- internals ------------------------------------------------------------------------
    def _new_record(self, spec: FileSpec, fallback_supplier: str) -> dict:
        while True:
            code, name, base = self.rng.choice(PRODUCTS)
            record = {
                "delivery_date": PERIOD_START + timedelta(days=self.rng.randint(0, 29)),
                "supplier": self.rng.choice(spec.suppliers) if spec.suppliers else fallback_supplier,
                "product_code": code, "product_name": name,
                "quantity_kg": round(self.rng.uniform(300, 18000), 1),
                "unit_price_eur": round(base * self.rng.uniform(0.9, 1.1), 3),
            }
            key = (record["supplier"], record["delivery_date"], code,
                   record["quantity_kg"], record["unit_price_eur"])
            if key not in self.used_keys:
                self.used_keys.add(key)
                return record

    def _write_file(self, spec: FileSpec, raw_dir: Path) -> list[tuple[str, int, str]]:
        fallback = Path(spec.filename).stem.replace("_", " ").title()
        records = [self._new_record(spec, fallback) for _ in range(self.rows_per_file)]
        overrides: dict[int, dict] = {i: {} for i in range(len(records))}
        injected: dict[int, str] = {}

        n_errors = max(6, round(self.rows_per_file * 0.06))
        n_dups = max(1, n_errors // 5)
        picks = self.rng.sample(range(len(records)), n_errors + n_dups)
        error_idx, dup_source_idx = picks[:n_errors], picks[n_errors:]
        order = COLUMN_ORDERS[spec.filename]

        for n, i in enumerate(error_idx):
            rule = INJECTED_RULES[n % len(INJECTED_RULES)]
            injected[i] = rule
            rec = records[i]
            if rule == MISSING_VALUE:
                field_name = self.rng.choice([f for f in order if f in
                                              ("delivery_date", "supplier", "product_code",
                                               "quantity_kg", "unit_price_eur")])
                overrides[i][field_name] = None
            elif rule == INVALID_FORMAT:
                field_name = self.rng.choice(["delivery_date", "quantity_kg", "unit_price_eur"])
                bad = {"delivery_date": "31/02/2026" if spec.date_style == "dmy_text" else "TBD",
                       "quantity_kg": self.rng.choice(["n/a", "abc", "--"]),
                       "unit_price_eur": "?"}
                overrides[i][field_name] = bad[field_name]
            elif rule == NON_POSITIVE:
                if self.rng.random() < 0.5:
                    rec["quantity_kg"] = self.rng.choice([0.0, -round(rec["quantity_kg"], 1)])
                else:
                    rec["unit_price_eur"] = self.rng.choice([0.0, -rec["unit_price_eur"]])
            elif rule == UNKNOWN_PRODUCT:
                rec["product_code"], rec["product_name"] = "ZZZ99", "Unlisted product"
            else:  # DATE_OUT_OF_PERIOD
                rec["delivery_date"] = (date(2026, 8, self.rng.randint(1, 31)) if self.rng.random() < 0.5
                                        else date(2026, 10, self.rng.randint(1, 31)))

        # rows to write: the originals, then exact copies of some clean rows (duplicates)
        rows = [(rec, overrides[i]) for i, rec in enumerate(records)]
        dup_rows = [(dict(records[i]), {}) for i in dup_source_idx]
        rows += dup_rows

        wb = Workbook()
        ws = wb.active
        ws.title = spec.sheet
        for text in spec.title_rows:
            ws.append([text])
        header = [spec.headers[f] for f in order] + ([spec.extra_column] if spec.extra_column else [])
        ws.append(header)
        header_row = ws.max_row

        truth: list[tuple[str, int, str]] = []
        for position, (rec, over) in enumerate(rows):
            values = []
            for f in order:
                if f in over:
                    values.append(over[f])
                elif f == "delivery_date":
                    values.append(_fmt_date(rec[f], spec.date_style))
                elif f == "quantity_kg":
                    values.append(_fmt_quantity(rec[f], spec.number_style))
                elif f == "unit_price_eur":
                    values.append(_fmt_price(rec[f], spec.number_style))
                elif f == "product_code":
                    code = rec[f]
                    # harmless noise the cleaner must normalise (not an error)
                    values.append(code.lower() + " " if self.rng.random() < 0.1 else code)
                elif f == "supplier":
                    values.append(rec[f].upper() if self.rng.random() < 0.1 else rec[f])
                else:
                    values.append(rec[f])
            if spec.extra_column:
                values.append(self.rng.choice(["", "", "", "organic", "late delivery", "checked"]))
            ws.append(values)

            excel_row = header_row + 1 + position
            if position < len(records) and position in injected:
                truth.append((spec.filename, excel_row, injected[position]))
            if position >= len(records):
                truth.append((spec.filename, excel_row, DUPLICATE_ROW))

        for index in range(1, len(header) + 1):
            ws.column_dimensions[ws.cell(row=header_row, column=index).column_letter].width = 18
        wb.save(raw_dir / spec.filename)
        return truth
