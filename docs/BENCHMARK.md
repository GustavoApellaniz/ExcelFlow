# Benchmark: manual vs automated consolidation

The goal is a **measurable** comparison, not a claim. Two things are measured on the same
data (`sample_data/raw/`, 5 files, 655 rows, **45 injected errors** listed in
`sample_data/ground_truth.csv`):

1. **Time** to produce one consolidated, validated workbook.
2. **Errors found**: how many of the 45 known errors were detected, and how many false alarms.

## Automated result (measured)

```bash
python -m harmonize_xl benchmark --sizes 130 2000 10000 --repeats 3
```

| Rows per file | Total rows read | Injected errors | Median time (s) | Rows/s | Precision | Recall |
|---|---|---|---|---|---|---|
| 130 | 655 | 45 | 0.31 | 2,129 | 100.0% | 100.0% |
| 2000 | 10120 | 720 | 2.59 | 3,906 | 100.0% | 100.0% |
| 10000 | 50600 | 3600 | 15.51 | 3,262 | 100.0% | 100.0% |

Median of 3 runs, single thread, generated in a Linux sandbox. Absolute times depend on your
machine; run the command above to reproduce on yours. Precision/recall are 100% because the
sample errors are the kinds the rules are designed to catch; real files will contain error
types that no rule covers yet (see "Limitations" in the README).

## Manual baseline (to be measured by the author)

No manual figure is published here because none has been measured yet. Protocol:

1. Copy `sample_data/raw/` to a new folder. Do **not** open `ground_truth.csv`.
2. Start a stopwatch. In Excel, build one workbook with all rows in the same columns
   (same order, ISO dates, decimal point), then look for and mark the problems you find
   (missing values, text in number cells, zero or negative quantities, unknown product codes,
   dates outside September 2026, duplicate rows).
3. Stop the stopwatch. Save the list of rows you flagged as `manual_issues.csv`
   (`file,row,rule`).
4. Compare with the ground truth:

```python
from harmonize_xl.benchmark import read_ground_truth
import csv
truth = read_ground_truth("sample_data/ground_truth.csv")
found = {(r["file"], int(r["row"]), r["rule"]) for r in csv.DictReader(open("manual_issues.csv"))}
print("recall", len(truth & found) / len(truth), "false alarms", len(found - truth))
```

5. Fill in the table (repeat the manual attempt twice if you can; report the best and the first):

| Process | Time | Errors found (of 45) | False alarms | Reproducible? |
|---|---|---|---|---|
| Manual in Excel | _measure_ | _measure_ | _measure_ | No |
| `python -m harmonize_xl run` | 0.3 s | 45 | 0 | Yes |
