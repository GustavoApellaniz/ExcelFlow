"""Command-line interface: generate-sample | run | benchmark."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from harmonize_xl.benchmark import run_benchmark
from harmonize_xl.config import Config
from harmonize_xl.pipeline import Pipeline
from harmonize_xl.sample_data import SampleDataGenerator

DEFAULT_SAMPLE = Path("sample_data")


def setup_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
        force=True,
    )


def cmd_generate_sample(args: argparse.Namespace) -> int:
    base = SampleDataGenerator(seed=args.seed, rows_per_file=args.rows_per_file).generate(args.output)
    print(f"Sample data written to {base}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    config = Config(period_start=args.period_start, period_end=args.period_end)
    result = Pipeline(config).run(args.input, args.output, args.reference)
    print(f"\nFiles read       : {result.files_read}")
    print(f"Rows read        : {result.rows_read}")
    print(f"Valid rows       : {result.valid_rows}")
    print(f"Rows with issues : {result.rows_with_issues} ({len(result.issues)} issues)")
    print(f"Time             : {result.elapsed_seconds:.2f} s")
    print(f"Report           : {result.output_path}")
    if result.failed_files:
        print(f"Failed files     : {', '.join(name for name, _ in result.failed_files)}")
        return 1
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    print(run_benchmark(args.sizes, repeats=args.repeats))
    return 0


COMMANDS = {"generate-sample": cmd_generate_sample, "run": cmd_run, "benchmark": cmd_benchmark}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harmonize_xl",
                                     description="Consolidate and validate messy Excel files.")
    parser.add_argument("--log-file", type=Path, default=Path("logs/harmonize.log"))
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate-sample", help="create messy example files with known errors")
    gen.add_argument("--output", type=Path, default=DEFAULT_SAMPLE)
    gen.add_argument("--rows-per-file", type=int, default=130)
    gen.add_argument("--seed", type=int, default=42)

    run = sub.add_parser("run", help="consolidate a folder of .xlsx files")
    run.add_argument("--input", type=Path, default=DEFAULT_SAMPLE / "raw")
    run.add_argument("--output", type=Path, default=Path("output/consolidated_report.xlsx"))
    run.add_argument("--reference", type=Path, default=DEFAULT_SAMPLE / "reference" / "products.csv")
    run.add_argument("--period-start", type=date.fromisoformat, default=Config().period_start)
    run.add_argument("--period-end", type=date.fromisoformat, default=Config().period_end)

    bench = sub.add_parser("benchmark", help="measure speed and error-detection quality")
    bench.add_argument("--sizes", type=int, nargs="+", default=[130, 2000])
    bench.add_argument("--repeats", type=int, default=3)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.log_file)
    return COMMANDS[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
