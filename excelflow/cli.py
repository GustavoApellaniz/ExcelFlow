"""Command-line interface: generate-sample | run | benchmark."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from excelflow import __version__
from excelflow.benchmark import run_benchmark
from excelflow.config import Config
from excelflow.pipeline import Pipeline, issues_csv_path
from excelflow.sample_data import SampleDataGenerator

DEFAULT_SAMPLE = Path("sample_data")
DEFAULT_INPUT = DEFAULT_SAMPLE / "raw"
DEFAULT_REFERENCE = DEFAULT_SAMPLE / "reference" / "products.csv"

logger = logging.getLogger("excelflow")


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


def _reference_for(args: argparse.Namespace) -> Path | None:
    """Explicit --reference must exist; with the bundled sample input the sample list is used."""
    if args.no_reference:
        return None
    if args.reference is not None:
        if not args.reference.exists():
            raise FileNotFoundError(f"Reference file not found: {args.reference}")
        return args.reference
    if args.input == DEFAULT_INPUT and DEFAULT_REFERENCE.exists():
        return DEFAULT_REFERENCE
    return None


def cmd_run(args: argparse.Namespace) -> int:
    config = Config(period_start=args.period_start, period_end=args.period_end)
    result = Pipeline(config).run(args.input, args.output, _reference_for(args))
    print(f"\nFiles read       : {result.files_read}")
    print(f"Rows read        : {result.rows_read}")
    print(f"Valid rows       : {result.valid_rows}")
    print(f"Rows with issues : {result.rows_with_issues} ({len(result.issues)} issues)")
    print(f"Time             : {result.elapsed_seconds:.2f} s")
    print(f"Report           : {result.output_path}")
    print(f"Issues CSV       : {issues_csv_path(result.output_path)}")
    if result.failed_files:
        print(f"Failed files     : {', '.join(name for name, _ in result.failed_files)}")
        return 1
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    print(run_benchmark(args.sizes, repeats=args.repeats))
    return 0


COMMANDS = {"generate-sample": cmd_generate_sample, "run": cmd_run, "benchmark": cmd_benchmark}


def _iso_date(text: str) -> date:
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{text}' is not a date in YYYY-MM-DD format") from None


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        value = 0
    if value < 1:
        raise argparse.ArgumentTypeError(f"'{text}' must be a whole number greater than zero")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="excelflow",
                                     description="Consolidate and validate messy Excel files.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--log-file", type=Path, default=Path("logs/excelflow.log"),
                        help="where to write the processing log (default: logs/excelflow.log)")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate-sample", help="create messy example files with known errors")
    gen.add_argument("--output", type=Path, default=DEFAULT_SAMPLE,
                     help="folder to create (default: sample_data)")
    gen.add_argument("--rows-per-file", type=_positive_int, default=130)
    gen.add_argument("--seed", type=int, default=42)

    run = sub.add_parser("run", help="consolidate a folder of .xlsx files")
    run.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                     help="folder with the .xlsx files (default: sample_data/raw)")
    run.add_argument("--output", type=Path, default=Path("output/consolidated_report.xlsx"),
                     help="workbook to write; the issues CSV is written next to it")
    ref = run.add_mutually_exclusive_group()
    ref.add_argument("--reference", type=Path, default=None,
                     help="CSV with product_code,product_name columns (enables 'unknown_product')")
    ref.add_argument("--no-reference", action="store_true",
                     help="skip the product reference check")
    run.add_argument("--period-start", type=_iso_date, default=Config().period_start,
                     help="first valid delivery date, YYYY-MM-DD")
    run.add_argument("--period-end", type=_iso_date, default=Config().period_end,
                     help="last valid delivery date, YYYY-MM-DD")

    bench = sub.add_parser("benchmark", help="measure speed and error-detection quality")
    bench.add_argument("--sizes", type=_positive_int, nargs="+", default=[130, 2000],
                       help="rows per generated file, one benchmark line per size")
    bench.add_argument("--repeats", type=_positive_int, default=3)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    setup_logging(args.log_file)
    try:
        return COMMANDS[args.command](args)
    except (FileNotFoundError, ValueError, PermissionError) as exc:
        # Expected user errors: one clear line instead of a traceback (details go to the log).
        logger.debug("Run failed", exc_info=True)
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
