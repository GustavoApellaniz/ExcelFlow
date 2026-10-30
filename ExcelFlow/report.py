"""Step 4: write the consolidated Excel workbook (clean data, issues, mapping, summary formulas)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from harmonize_xl.config import Config
from harmonize_xl.models import ALL_RULES, Issue

FONT = "Arial"
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(name=FONT, bold=True, color="FFFFFF")
BODY_FONT = Font(name=FONT)
BOLD = Font(name=FONT, bold=True)


def _header(ws, row: int, labels: list[str]) -> None:
    for col, label in enumerate(labels, start=1):
        cell = ws.cell(row=row, column=col, value=label)
        cell.font, cell.fill = HEADER_FONT, HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")


def _widths(ws, widths: list[int]) -> None:
    for col, width in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(col)].width = width


def _style_body(ws, first_row: int) -> None:
    for row in ws.iter_rows(min_row=first_row):
        for cell in row:
            cell.font = BODY_FONT


class ReportWriter:
    def __init__(self, config: Config, reference: dict[str, str] | None) -> None:
        self.config = config
        self.reference = reference or {}

    def write(self, path: Path, clean: pd.DataFrame, issues: list[Issue],
              mapping_rows: list[dict], files_read: int, rows_read: int) -> None:
        wb = Workbook()
        summary = wb.active
        summary.title = "Summary"
        data = wb.create_sheet("Data")
        issues_ws = wb.create_sheet("Issues")
        mapping_ws = wb.create_sheet("Mapping")

        clean = clean.sort_values(["delivery_date", "supplier", "product_code"]).reset_index(drop=True)
        self._data_sheet(data, clean)
        self._issues_sheet(issues_ws, issues)
        self._mapping_sheet(mapping_ws, mapping_rows)
        self._summary_sheet(summary, clean, files_read, rows_read)

        path.parent.mkdir(parents=True, exist_ok=True)
        wb.save(path)

    # ---- sheets -----------------------------------------------------------------------------
    def _data_sheet(self, ws, clean: pd.DataFrame) -> None:
        _header(ws, 1, ["Date", "Supplier", "Product code", "Product", "Quantity (kg)",
                        "Unit price (EUR)", "Total (EUR)", "Source file", "Source row"])
        for r, rec in enumerate(clean.to_dict("records"), start=2):
            name = rec["product_name"] or self.reference.get(rec["product_code"], "")
            values = [rec["delivery_date"], rec["supplier"], rec["product_code"], name,
                      rec["quantity_kg"], rec["unit_price_eur"], f"=E{r}*F{r}",
                      rec["source_file"], rec["source_row"]]
            for c, value in enumerate(values, start=1):
                ws.cell(row=r, column=c, value=value)
            ws.cell(row=r, column=1).number_format = "yyyy-mm-dd"
            ws.cell(row=r, column=5).number_format = "#,##0.0"
            ws.cell(row=r, column=6).number_format = "0.000"
            ws.cell(row=r, column=7).number_format = "#,##0.00"
        _style_body(ws, 2)
        _widths(ws, [12, 26, 14, 24, 15, 16, 15, 28, 11])
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:I{max(len(clean) + 1, 2)}"

    def _issues_sheet(self, ws, issues: list[Issue]) -> None:
        _header(ws, 1, ["File", "Row", "Field", "Rule", "Value", "Message"])
        for r, issue in enumerate(sorted(issues, key=lambda i: (i.file, i.row, i.field)), start=2):
            for c, value in enumerate([issue.file, issue.row, issue.field, issue.rule,
                                       issue.value, issue.message], start=1):
                ws.cell(row=r, column=c, value=value)
        _style_body(ws, 2)
        _widths(ws, [28, 8, 18, 22, 18, 60])
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:F{max(len(issues) + 1, 2)}"

    def _mapping_sheet(self, ws, rows: list[dict]) -> None:
        _header(ws, 1, ["File", "Sheet", "Header row", "Original header", "Mapped to",
                        "Method", "Score"])
        for r, row in enumerate(rows, start=2):
            for c, key in enumerate(["file", "sheet", "header_row", "original", "mapped_to",
                                     "method", "score"], start=1):
                ws.cell(row=r, column=c, value=row[key])
        _style_body(ws, 2)
        _widths(ws, [28, 16, 12, 24, 18, 12, 8])
        ws.freeze_panes = "A2"

    def _summary_sheet(self, ws, clean: pd.DataFrame, files_read: int, rows_read: int) -> None:
        ws["A1"] = "Consolidated deliveries report"
        ws["A2"] = f"Period: {self.config.period_start} to {self.config.period_end}"
        ws["A3"] = "Every figure below is an Excel formula over the Data and Issues sheets."
        ws["A3"].font = Font(name=FONT, italic=True, color="595959")

        overview = [
            ("Files processed", files_read, "0"),
            ("Rows read", rows_read, "#,##0"),
            ("Valid rows (in Data sheet)", "=COUNTA(Data!A:A)-1", "#,##0"),
            ("Rows with issues", "=B6-B7", "#,##0"),
            ("Total quantity (kg)", "=SUM(Data!E:E)", "#,##0.0"),
            ("Total value (EUR)", "=SUM(Data!G:G)", "#,##0.00"),
        ]
        _header(ws, 4, ["Overview", "Value"])
        for offset, (label, value, fmt) in enumerate(overview):
            r = 5 + offset
            ws.cell(row=r, column=1, value=label)
            ws.cell(row=r, column=2, value=value).number_format = fmt
        # rows: B5 files, B6 rows read, B7 valid, B8 issues, B9 total kg, B10 total EUR

        row = 13
        suppliers = sorted(s for s in clean["supplier"].dropna().unique())
        _header(ws, row, ["By supplier", "Quantity (kg)", "Value (EUR)", "Share of value"])
        for s in suppliers:
            row += 1
            ws.cell(row=row, column=1, value=s)
            ws.cell(row=row, column=2, value=f"=SUMIFS(Data!$E:$E,Data!$B:$B,$A{row})").number_format = "#,##0.0"
            ws.cell(row=row, column=3, value=f"=SUMIFS(Data!$G:$G,Data!$B:$B,$A{row})").number_format = "#,##0.00"
            ws.cell(row=row, column=4, value=f"=IF($B$10=0,0,C{row}/$B$10)").number_format = "0.0%"

        row += 3
        products = sorted(p for p in clean["product_code"].dropna().unique())
        _header(ws, row, ["By product (code)", "Quantity (kg)", "Value (EUR)", "Product"])
        for p in products:
            row += 1
            ws.cell(row=row, column=1, value=p)
            ws.cell(row=row, column=2, value=f"=SUMIFS(Data!$E:$E,Data!$C:$C,$A{row})").number_format = "#,##0.0"
            ws.cell(row=row, column=3, value=f"=SUMIFS(Data!$G:$G,Data!$C:$C,$A{row})").number_format = "#,##0.00"
            ws.cell(row=row, column=4, value=self.reference.get(p, ""))

        row += 3
        _header(ws, row, ["Issues by rule", "Count"])
        for rule in ALL_RULES:
            row += 1
            ws.cell(row=row, column=1, value=rule)
            ws.cell(row=row, column=2, value=f"=COUNTIF(Issues!$D:$D,$A{row})").number_format = "0"

        _style_body(ws, 4)
        for cells in ws.iter_rows(min_row=4):      # table headers keep the white bold font
            for cell in cells:
                if cell.fill == HEADER_FILL:
                    cell.font = HEADER_FONT
        ws["A1"].font = Font(name=FONT, bold=True, size=14)
        _widths(ws, [30, 18, 18, 24])
