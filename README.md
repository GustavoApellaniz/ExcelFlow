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

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run ExcelFlow

```bash
python -m harmonize_xl run
```

The default execution uses the bundled sample files.

Generated files:

```text
output/
├── consolidated_report.xlsx
└── consolidated_report_issues.csv
```

### 5. Process custom spreadsheets

```bash
python -m harmonize_xl run \
    --input my_files/ \
    --output output/report.xlsx \
    --reference my_products.csv \
    --period-start 2026-10-01 \
    --period-end 2026-10-31
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
pip install -r requirements-dev.txt
```

Run the test suite:

```bash
python -m pytest -q
```

GitHub Actions is configured to run tests on Python 3.10 and 3.12.

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
