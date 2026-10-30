"""Measures speed and detection quality of the automated process against the ground truth."""

from __future__ import annotations

import csv
import statistics
import tempfile
from dataclasses import dataclass
from pathlib import Path

from harmonize_xl.config import Config
from harmonize_xl.models import Issue
from harmonize_xl.pipeline import Pipeline
from harmonize_xl.sample_data import SampleDataGenerator


@dataclass
class Evaluation:
    true_positives: int
    false_positives: int
    false_negatives: int

    @property
    def precision(self) -> float:
        total = self.true_positives + self.false_positives
        return self.true_positives / total if total else 1.0

    @property
    def recall(self) -> float:
        total = self.true_positives + self.false_negatives
        return self.true_positives / total if total else 1.0


def read_ground_truth(path: Path) -> set[tuple[str, int, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return {(r["file"], int(r["row"]), r["rule"]) for r in csv.DictReader(f)}


def evaluate(issues: list[Issue], truth: set[tuple[str, int, str]]) -> Evaluation:
    detected = {(i.file, i.row, i.rule) for i in issues}
    return Evaluation(len(detected & truth), len(detected - truth), len(truth - detected))


def run_benchmark(sizes: list[int], repeats: int = 3, config: Config | None = None) -> str:
    """Return a Markdown table: one line per dataset size."""
    lines = ["| Rows per file | Total rows read | Injected errors | Median time (s) | Rows/s "
             "| Precision | Recall |", "|---|---|---|---|---|---|---|"]
    for size in sizes:
        with tempfile.TemporaryDirectory() as tmp:
            base = SampleDataGenerator(rows_per_file=size).generate(Path(tmp) / "data")
            truth = read_ground_truth(base / "ground_truth.csv")
            times, result = [], None
            for _ in range(repeats):
                result = Pipeline(config).run(base / "raw", Path(tmp) / "out" / "report.xlsx",
                                              base / "reference" / "products.csv")
                times.append(result.elapsed_seconds)
            ev = evaluate(result.issues, truth)
            median = statistics.median(times)
            lines.append(f"| {size} | {result.rows_read} | {len(truth)} | {median:.2f} | "
                         f"{result.rows_read / median:,.0f} | {ev.precision:.1%} | {ev.recall:.1%} |")
    return "\n".join(lines)
