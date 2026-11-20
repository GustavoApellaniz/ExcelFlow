# ExcelFlow

[![Tests](https://github.com/GustavoApellaniz/ExcelFlow/actions/workflows/tests.yml/badge.svg)](https://github.com/GustavoApellaniz/ExcelFlow/actions/workflows/tests.yml)

**ExcelFlow** is a Python-based tool for automating the consolidation, cleaning, and validation of Excel spreadsheets from multiple sources.

It addresses a common business problem: receiving spreadsheets with inconsistent formats, column names, date conventions, and data quality issues, then having to manually standardize and consolidate them.

ExcelFlow automates this process through a structured data-processing pipeline, producing a consolidated Excel report and a detailed record of detected inconsistencies.

## Key Features

- **Automatic header detection:** Identifies table headers even when spreadsheets contain introductory rows.
- **Flexible column mapping:** Matches column names across different languages and handles minor spelling mistakes.
- **Data cleaning:** Standardizes dates, numeric values, text fields, and product codes.
- **Data validation:** Detects missing values, invalid formats, non-positive values, unknown products, dates outside the reporting period, and duplicate records.
- **Error traceability:** Records the source file, original Excel row, field, and reason for each detected issue.
- **Automated reporting:** Generates a consolidated Excel workbook with summary, data, issues, and column-mapping sheets.
- **CSV export:** Produces an additional CSV file containing detected issues.
- **Logging:** Records processing events and errors for easier troubleshooting.

## Processing Pipeline

```text
Excel Files
     |
     v
Header Detection
     |
     v
Column Mapping
     |
     v
Data Cleaning
     |
     v
Data Validation
     |
     v
Report Generation
     |
     v
Consolidated Excel + Issues CSV
```

## Validation Rules

| Rule | Description |
|---|---|
| `missing_value` | Detects missing required fields. |
| `invalid_format` | Identifies invalid date and numeric formats. |
| `non_positive_value` | Flags zero or negative quantities and prices. |
| `unknown_product` | Detects product codes absent from the reference dataset. |
| `date_out_of_period` | Identifies records outside the configured reporting period. |
| `duplicate_row` | Detects duplicate records based on supplier, date, product, quantity, and price. |

Records containing validation issues are excluded from the valid data sheet and documented separately in the issues report.

## Technologies

- **Python**
- **Pandas** — Data manipulation and processing.
- **OpenPyXL** — Excel file reading and report generation.
- **Pytest** — Automated testing.
- **GitHub Actions** — Continuous integration.

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/GustavoApellaniz/ExcelFlow.git
cd ExcelFlow
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
```

Activate it:

```bash
# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install

```bash
pip install -e .
```

This installs the dependencies (Pandas, OpenPyXL) and the `excelflow` command.
`python -m excelflow` works too, and `pip install -r requirements.txt` is enough if you
prefer to run it without installing the package.

### 4. Run ExcelFlow on the sample files

```bash
excelflow run
```

The default run uses the bundled sample files in `sample_data/raw/` and the product list in
`sample_data/reference/products.csv`. Generated files:

```text
output/
├── consolidated_report.xlsx        # Summary, Data, Issues and Mapping sheets
└── consolidated_report_issues.csv  # one line per detected issue
logs/
└── excelflow.log                   # processing log
```

Pre-generated copies are in [`examples/`](examples/).

### 5. Process your own spreadsheets

```bash
excelflow run     --input my_files/     --output output/report.xlsx     --reference my_products.csv     --period-start 2026-10-01     --period-end 2026-10-31
```

The reference file is a CSV with the columns `product_code,product_name`. Without
`--reference`, the `unknown_product` rule is skipped for custom folders (a warning is logged).

## Command Reference

| Command | What it does |
|---|---|
| `excelflow run` | Consolidates every `.xlsx` in `--input` into one validated workbook. |
| `excelflow generate-sample` | Recreates the synthetic messy files and their ground truth (`--rows-per-file`, `--seed`, `--output`). |
| `excelflow benchmark` | Measures speed, precision and recall on generated data (`--sizes`, `--repeats`). |
| `excelflow --version` | Prints the installed version. |

Options of `run`:

| Option | Default | Meaning |
|---|---|---|
| `--input` | `sample_data/raw` | Folder with the `.xlsx` files. |
| `--output` | `output/consolidated_report.xlsx` | Workbook to write; the issues CSV goes next to it. |
| `--reference` | sample list (only for the sample input) | Product reference CSV. |
| `--no-reference` | off | Skip the product reference check. |
| `--period-start` / `--period-end` | `2026-09-01` / `2026-09-30` | Valid delivery period (inclusive, `YYYY-MM-DD`). |
| `--log-file` (before the command) | `logs/excelflow.log` | Where the log is written. |

Exit codes: `0` success, `1` finished but some files could not be read, `2` invalid input
(missing folder or reference file, bad dates, no readable table).

## Output Workbook

| Sheet | Content |
|---|---|
| **Summary** | Totals by supplier, by product and issues by rule. Every figure is a live Excel formula (`SUMIFS`, `COUNTIF`) over the other sheets, so it updates if you edit the data. |
| **Data** | Valid rows only, in one standard layout. `Total (EUR)` is a formula (`=Quantity*Price`). Each row keeps its source file and Excel row. |
| **Issues** | One line per problem: file, row, field, rule, original value and message. |
| **Mapping** | How each original header was mapped (exact or fuzzy match, with score), which columns were ignored and when the supplier came from the file name. |

## Project Structure

```text
excelflow/
├── cli.py          # command-line interface
├── pipeline.py     # load -> clean -> validate -> report
├── loader.py       # header detection and column mapping
├── schema.py       # canonical fields and multilingual/fuzzy header aliases
├── cleaner.py      # date, number and text normalisation
├── validator.py    # business rules
├── report.py       # Excel workbook with live formulas
├── sample_data.py  # synthetic messy files + ground truth
└── benchmark.py    # speed and precision/recall measurement
tests/              # pytest suite (unit + end-to-end)
sample_data/        # bundled example input
examples/           # example output
docs/BENCHMARK.md   # benchmark method and manual baseline protocol
```

## Sample Dataset

The project includes synthetic Excel files designed to simulate real-world data inconsistencies.

| File | Scenario |
|---|---|
| `cooperative_normandie.xlsx` | French headers and introductory rows. |
| `fazenda_sul.xlsx` | Portuguese headers and localized numeric formats. |
| `green_farms_uk.xlsx` | ISO dates, additional columns, and inconsistent capitalization. |
| `agro_iberia.xlsx` | Misspelled headers and different column ordering. |
| `bio_nord.xlsx` | Missing supplier column. |

The dataset includes injected errors and a ground-truth reference file, allowing the validation process to be evaluated objectively.

## Benchmark Results

Measured performance using the project's benchmark command:

| Total Rows | Median Processing Time | Precision | Recall |
|---:|---:|---:|---:|
| 655 | 0.31 s | 100% | 100% |
| 10,120 | 2.59 s | 100% | 100% |
| 50,600 | 15.51 s | 100% | 100% |

Results were obtained using synthetic datasets with predefined validation errors. They demonstrate detection performance for the implemented rules, not a guarantee of detecting every possible real-world data issue.

For benchmark methodology and reproduction instructions, see [`docs/BENCHMARK.md`](docs/BENCHMARK.md).

## Running Tests

Install development dependencies:

```bash
pip install -e ".[dev]"
```

Run the test suite:

```bash
python -m pytest -q
```

GitHub Actions runs the tests and a CLI smoke test on Python 3.10, 3.12 and 3.13.

## Current Limitations

- Supports `.xlsx` files.
- Expects one data table per worksheet.
- Date parsing follows a day-first convention.
- Supplier normalization handles capitalization and spacing differences, but not arbitrary spelling variations.
- Validation rules are currently designed around the project's delivery-data schema.

## Project Goals

ExcelFlow was developed to demonstrate practical skills in:

- Data cleaning and preprocessing.
- Spreadsheet automation.
- Data validation and quality control.
- Error handling and traceability.
- Python application architecture.
- Automated testing and benchmarking.

## Author

**Gustavo Fraga Apellaniz**

- GitHub: [@GustavoApellaniz](https://github.com/GustavoApellaniz)
- LinkedIn: [gustavoapellaniz](https://linkedin.com/in/gustavoapellaniz)

---

Released under the MIT License.
