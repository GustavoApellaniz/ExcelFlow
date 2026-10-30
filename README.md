# harmonize-xl

[![tests](https://github.com/GustavoApellaniz/harmonize-xl/actions/workflows/tests.yml/badge.svg)](https://github.com/GustavoApellaniz/harmonize-xl/actions/workflows/tests.yml)

A Python command-line tool that **consolidates Excel files from different sources into one
validated workbook**: it finds each file's header row, maps columns written in different
languages (even misspelled), converts dates and numbers, flags every inconsistent row with its
exact location, and writes a report with live Excel formulas.

> Built for a common situation: every supplier, branch or department sends a monthly `.xlsx`
> with its own layout, and someone spends hours copying and fixing them by hand.

## What it does

| Step | What happens |
|---|---|
| **Load** | Finds the header row even below title rows; matches headers by exact alias or fuzzy similarity (`Delivry date` → `delivery_date`); falls back to the file name when a file has no supplier column |
| **Clean** | Reads `1.250,5`, `0,225`, `€ 3,5 kg`, `03/09/2026`, Excel dates; trims text, upper-cases product codes, unifies supplier spelling (`FERME LENOIR` = `Ferme Lenoir`) |
| **Validate** | Six rules (table below). Each problem becomes one entry with file, **Excel row number**, field and reason |
| **Report** | `Summary` (formulas), `Data` (valid rows, total = formula), `Issues`, `Mapping` (audit trail of every column match) + an `_issues.csv` |
| **Log** | Everything is written to `logs/harmonize.log`; an unreadable file is logged and skipped, it does not stop the run |

### Validation rules

| Rule | Triggers when |
|---|---|
| `missing_value` | a required field is empty (date, supplier, product code, quantity, price) |
| `invalid_format` | a cell has content that is not a valid date or number (`abc`, `31/02/2026`, `n/a`) |
| `non_positive_value` | quantity or unit price is zero or negative |
| `unknown_product` | product code is not in `products.csv` |
| `date_out_of_period` | date is outside the configured period (default: September 2026) |
| `duplicate_row` | same supplier, date, product, quantity and price as an earlier row (the first one is kept) |

Rows with any issue are excluded from `Data` and listed in `Issues`, so totals never include
suspicious rows silently.

## Quick start

```bash
git clone https://github.com/GustavoApellaniz/harmonize-xl.git
cd harmonize-xl
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python -m harmonize_xl run          # uses the bundled sample files
```

Output: `output/consolidated_report.xlsx` and `output/consolidated_report_issues.csv`.
A ready-made result is in [`examples/`](examples/).

Use it on your own files:

```bash
python -m harmonize_xl run --input my_files/ --output out/report.xlsx \
    --reference my_products.csv --period-start 2026-10-01 --period-end 2026-10-31
```

Other commands:

```bash
python -m harmonize_xl generate-sample --rows-per-file 500   # new messy files + ground truth
python -m harmonize_xl benchmark --sizes 130 2000            # speed and detection quality
```

## The sample data

`sample_data/raw/` holds five files with different problems on purpose:

| File | Mess |
|---|---|
| `cooperative_normandie.xlsx` | French headers, 3 title rows above the table |
| `fazenda_sul.xlsx` | Portuguese headers, dates and numbers stored as text (`1.250,5`) |
| `green_farms_uk.xlsx` | ISO text dates, extra `Notes` column, supplier names in upper case |
| `agro_iberia.xlsx` | misspelled headers, different column order |
| `bio_nord.xlsx` | no supplier column |

The data is **synthetic**. 45 errors were injected at known positions and listed in
`sample_data/ground_truth.csv`, which allows precision and recall to be measured.

## Results

Measured with `python -m harmonize_xl benchmark` (details and reproduction in
[`docs/BENCHMARK.md`](docs/BENCHMARK.md)):

| Rows read | Median time | Precision | Recall |
|---|---|---|---|
| 655 | 0.31 s | 100% | 100% |
| 10,120 | 2.59 s | 100% | 100% |
| 50,600 | 15.51 s | 100% | 100% |

The comparison with the manual process is **not filled in yet**: the protocol is in
[`docs/BENCHMARK.md`](docs/BENCHMARK.md). The 100% figures only mean the rules catch the error
types they were designed for; they are not a claim about arbitrary real-world files.

## Design decisions

- **Row numbers are Excel row numbers**, so every issue can be found by looking at that row in
  the source file.
- **Formulas, not pasted values.** The report's totals are `SUMIFS`/`SUM`/`COUNTIF` over the data
  sheets, so they update if someone edits the data. Values appear when the file is opened in Excel.
- **`keep_default_na=False` when reading.** By default pandas turns text like `n/a` or a product
  code `NA` into empty values without telling you. Here the Cleaner decides what is missing and what
  is invalid.
- **Fuzzy header matching with a cutoff (0.8)** and an audit sheet, so a wrong match is visible.
- **One failing file is logged and skipped**; the exit code is non-zero so scripts notice.
- **Schema in one place** (`schema.py`): to adapt the tool to other columns, edit the field list
  and aliases there and the rules in `validator.py`.

## Project structure

```
harmonize_xl/
├── cli.py          # generate-sample | run | benchmark
├── pipeline.py     # load -> clean -> validate -> report
├── loader.py       # header detection and column mapping
├── schema.py       # canonical fields, aliases, fuzzy matching
├── cleaner.py      # date/number parsing, text normalisation
├── validator.py    # business rules
├── report.py       # output workbook (openpyxl)
├── sample_data.py  # messy file generator + ground truth
└── benchmark.py    # timing, precision, recall
tests/              # 26 automated tests
sample_data/        # raw files, product reference, ground truth
examples/           # report produced from the sample files
docs/BENCHMARK.md   # measured results and manual-baseline protocol
```

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

The end-to-end test generates new messy files with a different seed and asserts that every
injected error is found and nothing else is flagged. GitHub Actions runs the suite on Python 3.10
and 3.12.

## Limitations

- Reads `.xlsx` only (not `.xls` or `.csv`) and expects one table per sheet.
- Dates are read day-first (`03/09/2026` = 3 September). If only one separator appears in a number
  it is treated as the decimal one, so `1.250` is read as `1.25`.
- Supplier names are unified when they differ only by case or spacing, not by spelling.
- Rules are written for the delivery schema; other domains need their own aliases and rules.
- The `Summary` sheet shows values after Excel (or LibreOffice) recalculates the file; a program that
  reads the file without calculating (such as pandas) sees empty formula cells. The example in
  `examples/` was recalculated.

## Ideas for next versions

- Read `.csv` and `.xls`; configurable schema in a YAML file
- Outlier rule (price far from the product's median)
- Export clean data to SQLite for the SQL project of this portfolio

## Author

**Gustavo Fraga Apellaniz**: [GitHub](https://github.com/GustavoApellaniz) ·
[LinkedIn](https://linkedin.com/in/gustavoapellaniz)

Released under the MIT License.
