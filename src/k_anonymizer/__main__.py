"""Command-line interface for k_anonymizer."""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
from collections.abc import Sequence

from . import KAnonError, anonymize, check_k, numeric_range, prefix_mask

MAX_CLI_FILE_SIZE = 50_000_000


def _parse_hierarchy_spec(spec: str) -> tuple[str, str, str]:
    """Parse hierarchy spec in form col=range:10,20 or col=mask:5."""
    if "=" not in spec:
        raise KAnonError(
            f"Invalid hierarchy specification: '{spec}', expected col=kind:params",
            code="invalid_option",
        )
    col, right = spec.split("=", 1)
    col = col.strip()
    if not col:
        raise KAnonError("Quasi-identifier column name cannot be empty", code="invalid_option")
    if ":" not in right:
        raise KAnonError(
            f"Invalid hierarchy type in '{spec}', expected kind:params", code="invalid_option"
        )
    kind, params = right.split(":", 1)
    return col, kind.strip(), params.strip()


def _read_csv(filepath: str) -> list[dict[str, str]]:
    try:
        size = os.path.getsize(filepath)
    except OSError as err:
        raise KAnonError(f"Cannot access file: {filepath}", code="invalid_option") from err

    if size > MAX_CLI_FILE_SIZE:
        raise KAnonError(
            f"File size {size} exceeds limit of {MAX_CLI_FILE_SIZE} bytes",
            code="input_too_large",
        )

    try:
        with open(filepath, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return []
            return [dict(row) for row in reader]
    except UnicodeDecodeError as err:
        raise KAnonError("Failed to decode CSV file as UTF-8", code="invalid_value") from err
    except csv.Error as err:
        raise KAnonError(f"CSV parsing error: {err}", code="invalid_value") from err


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="k-anonymizer",
        description="Check and enforce k-anonymity on CSV tabular datasets.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    # check subcommand
    check_parser = subparsers.add_parser("check", help="Check k-anonymity of a dataset")
    check_parser.add_argument("file", help="Input CSV file path")
    check_parser.add_argument(
        "--qi",
        required=True,
        help="Comma-separated quasi-identifiers (e.g. age,zip)",
    )
    check_parser.add_argument(
        "--k",
        type=int,
        default=2,
        help="Target k value for pass/fail (default: 2)",
    )

    # anonymize subcommand
    anon_parser = subparsers.add_parser("anonymize", help="Anonymize a dataset")
    anon_parser.add_argument("file", help="Input CSV file path")
    anon_parser.add_argument(
        "--qi",
        action="append",
        required=True,
        help="Quasi-identifier hierarchy (e.g. --qi age=range:10,20 --qi zip=mask:5)",
    )
    anon_parser.add_argument(
        "--k",
        type=int,
        required=True,
        help="Desired k value (k >= 2)",
    )
    anon_parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output CSV file path (defaults to stdout)",
    )
    anon_parser.add_argument(
        "--max-suppression",
        type=float,
        default=0.0,
        help="Maximum allowed row suppression fraction [0.0, 1.0) (default: 0.0)",
    )

    if not argv:
        parser.print_help()
        return 2

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code != 0 else 0

    try:
        if args.command == "check":
            rows = _read_csv(args.file)
            qi_cols = [c.strip() for c in args.qi.split(",") if c.strip()]
            report = check_k(rows, qi_cols)
            print(f"k={report.k_actual}")
            return 0 if report.k_actual >= args.k else 1

        elif args.command == "anonymize":
            rows = _read_csv(args.file)
            hierarchies = {}
            for spec in args.qi:
                col, kind, params = _parse_hierarchy_spec(spec)
                if kind == "range":
                    widths = [int(w.strip()) for w in params.split(",") if w.strip()]
                    hierarchies[col] = numeric_range(widths)
                elif kind == "mask":
                    hierarchies[col] = prefix_mask(int(params))
                else:
                    raise KAnonError(
                        f"Unknown hierarchy kind '{kind}', expected 'range' or 'mask'",
                        code="invalid_option",
                    )

            result = anonymize(
                rows,
                hierarchies,
                k=args.k,
                max_suppression=args.max_suppression,
            )

            # Output rows
            if rows:
                fieldnames = list(rows[0].keys())
            elif result.rows:
                fieldnames = list(result.rows[0].keys())
            else:
                fieldnames = list(hierarchies.keys())

            out_buffer = io.StringIO()
            writer = csv.DictWriter(out_buffer, fieldnames=fieldnames, lineterminator="\n")
            writer.writeheader()
            for r in result.rows:
                writer.writerow(r)
            csv_text = out_buffer.getvalue()

            if args.output:
                with open(args.output, "w", encoding="utf-8", newline="") as f:
                    f.write(csv_text)
            else:
                sys.stdout.write(csv_text)
            return 0
        else:
            parser.print_help()
            return 2
    except KAnonError as err:
        sys.stderr.write(f"Error ({err.code}): {err}\n")
        return 2
    except Exception as err:
        sys.stderr.write(f"Unexpected error: {err}\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
