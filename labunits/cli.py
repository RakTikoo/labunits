"""Command-line interface for labunits.

Subcommands:
  labunits convert FILE --columns glucose,creatinine
                   --from conventional --to si [--out FILE]
  labunits convert FILE --spec spec.csv --from si --to conventional
  labunits convert-one --analyte glucose --value 100
                       --from conventional --to si
  labunits list        -- the verified analyte table, with sources
  labunits check       -- verify against built-in published worked pairs

The system of the input (--from) must be stated, never guessed, and
the analyte of every converted column must be named explicitly --
in --columns (column name = analyte key) or in a --spec CSV with
`analyte,column` rows for columns whose names differ from the keys.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from pathlib import Path

from . import core
from .analytes import ANALYTES, REFUSED
from .core import LabunitsError


def build_parser():
    parser = argparse.ArgumentParser(
        prog="labunits",
        description="Batch-convert lab-result CSV columns between "
                    "conventional (US) and SI units -- only with "
                    "factors verified against two authorities.")
    sub = parser.add_subparsers(dest="command")

    conv = sub.add_parser(
        "convert", help="convert whole columns of a CSV file")
    conv.add_argument("file", help="input CSV")
    conv.add_argument("--columns", default=None,
                      help="comma-separated analyte keys; each key "
                           "must also be a column name in the file")
    conv.add_argument("--spec", default=None,
                      help="CSV with header analyte,column mapping "
                           "analyte keys to column names")
    conv.add_argument("--from", dest="from_system", default=None,
                      choices=core.SYSTEMS,
                      help="unit system of the input: conventional "
                           "or si (required -- never guessed)")
    conv.add_argument("--to", dest="to_system", default=None,
                      choices=core.SYSTEMS,
                      help="unit system to write: conventional or si "
                           "(required)")
    conv.add_argument("--out", default=None,
                      help="output CSV (default: <input>_converted.csv)")

    one = sub.add_parser("convert-one", help="convert a single value")
    one.add_argument("--analyte", required=True)
    one.add_argument("--value", required=True, type=float)
    one.add_argument("--from", dest="from_system", default=None,
                     choices=core.SYSTEMS, required=False,
                     help="unit system of the value (required)")
    one.add_argument("--to", dest="to_system", default=None,
                     choices=core.SYSTEMS,
                     help="unit system to convert to (required)")

    sub.add_parser("list", help="print the verified analyte table")
    sub.add_parser("check", help="verify against published worked pairs")
    return parser


# A CSV cell counts as a number only if it is plain decimal or
# scientific notation. float() alone would also accept 'nan', 'inf',
# 'infinity' and Python-literal forms like '1_000' -- none of which
# is a laboratory value, and all of which must fail loudly instead
# of being silently converted.
_NUMBER_RE = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")


def _parse_cell(raw, row_num, col):
    if not _NUMBER_RE.match(raw):
        raise LabunitsError(
            f"row {row_num}, column {col!r}: value {raw!r} is not "
            "a number. labunits converts numbers only and "
            "will not silently skip or guess one.")
    value = float(raw)
    if not math.isfinite(value):  # e.g. 1e999 overflows to inf
        raise LabunitsError(
            f"row {row_num}, column {col!r}: value {raw!r} is not "
            "a finite number. labunits converts measured values only.")
    if value < 0:
        raise LabunitsError(
            f"row {row_num}, column {col!r}: value {raw!r} is "
            "negative -- a laboratory result cannot be negative, "
            "so labunits will not convert it.")
    return value


def _systems(args):
    if args.from_system is None or args.to_system is None:
        raise LabunitsError(
            "--from and --to are both required, and labunits refuses "
            "to guess them. State them explicitly, e.g. "
            "--from conventional --to si.")
    if args.from_system == args.to_system:
        raise LabunitsError(
            f"--from and --to are both {args.from_system!r} -- nothing "
            "to convert. Pick two different systems.")
    return args.from_system, args.to_system


def _read_spec(path):
    p = Path(path)
    if not p.is_file():
        raise LabunitsError(f"spec file not found: {path}")
    pairs = []
    with p.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or \
                "analyte" not in reader.fieldnames or \
                "column" not in reader.fieldnames:
            raise LabunitsError(
                f"spec file {path} must have header 'analyte,column'.")
        for i, row in enumerate(reader, start=2):
            analyte = (row.get("analyte") or "").strip()
            column = (row.get("column") or "").strip()
            if not analyte and not column:
                continue
            if not analyte or not column:
                raise LabunitsError(
                    f"spec file {path} line {i}: both analyte and "
                    "column are required.")
            pairs.append((analyte, column))
    if not pairs:
        raise LabunitsError(f"spec file {path} names no conversions.")
    return pairs


def cmd_convert(args):
    from_system, to_system = _systems(args)
    if bool(args.columns) == bool(args.spec):
        raise LabunitsError(
            "state exactly one of --columns or --spec: labunits must "
            "be told explicitly which analyte each column is.")
    in_path = Path(args.file)
    if not in_path.is_file():
        raise LabunitsError(f"input file not found: {args.file}")
    if in_path.stat().st_size == 0:
        raise LabunitsError(f"input file is empty: {args.file}")

    if args.columns:
        pairs = [(name.strip(), name.strip())
                 for name in args.columns.split(",") if name.strip()]
        if not pairs:
            raise LabunitsError("--columns named no analytes.")
    else:
        pairs = _read_spec(args.spec)

    # Resolve every analyte BEFORE touching data: a refused or
    # unknown analyte aborts the whole run, with its reason.
    resolved = [(core.resolve_analyte(a), col) for a, col in pairs]
    seen_cols = set()
    for _, col in resolved:
        if col in seen_cols:
            raise LabunitsError(f"column {col!r} is named twice.")
        seen_cols.add(col)

    with in_path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise LabunitsError(f"{args.file} has no header row.")
        fieldnames = list(reader.fieldnames)
        rows = list(reader)
    if not rows:
        raise LabunitsError(f"{args.file} contains no data rows.")
    for _, col in resolved:
        if col not in fieldnames:
            raise LabunitsError(
                f"column {col!r} not found in {args.file}. "
                f"Available columns: {', '.join(fieldnames)}")

    new_fields = list(fieldnames)
    additions = []  # (key, column, converted_name, factor_name)
    for key, col in resolved:
        unit = core.target_unit(key, to_system)
        safe_unit = (unit.replace(" ", "_").replace("/", "_")
                     .replace("(", "").replace(")", "")
                     .replace("%", "pct"))
        conv_name = f"{col}__{safe_unit}"
        factor_name = f"{col}__factor"
        for name in (conv_name, factor_name):
            if name in new_fields:
                raise LabunitsError(
                    f"the input already has a {name!r} column; "
                    "refusing to overwrite it. Rename or remove it first.")
            new_fields.append(name)
        additions.append((key, col, conv_name, factor_name))

    converted_cells = 0
    for r, row in enumerate(rows, start=2):
        for key, col, conv_name, factor_name in additions:
            raw = (row.get(col) or "").strip()
            if raw == "":
                row[conv_name] = ""
                row[factor_name] = ""
                continue
            value = _parse_cell(raw, r, col)
            row[conv_name] = core.format_value(
                core.convert_value(key, value, from_system, to_system))
            row[factor_name] = core.factor_label(key, from_system)
            converted_cells += 1

    if args.out:
        out_path = Path(args.out)
    else:
        out_path = in_path.with_name(
            in_path.stem + "_converted" + (in_path.suffix or ".csv"))
    if out_path.resolve() == in_path.resolve():
        raise LabunitsError(
            f"output file {out_path} is the input file -- refusing "
            "to overwrite the original data. Pick a different --out.")
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=new_fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"converted {converted_cells} values in {len(rows)} rows "
          f"from {args.file}")
    print(f"  direction : {from_system} -> {to_system}")
    for key, col, conv_name, _ in additions:
        info = core.analyte_info(key)
        print(f"  {col} ({info['name']}): "
              f"{core.factor_label(key, from_system)} -> {conv_name}")
    print(f"  output    : {out_path}")
    print("  note      : conversion only -- no reference ranges, "
          "no flags, no interpretation.")
    return 0


def cmd_convert_one(args):
    from_system, to_system = _systems(args)
    key = core.resolve_analyte(args.analyte)
    result = core.convert_value(key, args.value, from_system, to_system)
    info = core.analyte_info(key)
    src_unit = (info["conv_unit"] if from_system == "conventional"
                else info["si_unit"])
    dst_unit = core.target_unit(key, to_system)
    print(f"{args.value:g} {src_unit} = {core.format_value(result)} "
          f"{dst_unit}")
    print(f"  {core.factor_label(key, from_system)}")
    print(f"  source: {info['source']}")
    return 0


def cmd_list(_args):
    print(f"{'key':26} {'conventional':16} {'SI':16} factor (conv -> SI)")
    print("-" * 100)
    for key in ("hba1c", "bun"):
        info = core.analyte_info(key)
        print(f"{key:26} {info['conv_unit']:16} {info['si_unit']:16} "
              f"{info['formula_conv_to_si']}")
    for key in sorted(ANALYTES):
        info = core.analyte_info(key)
        print(f"{key:26} {info['conv_unit']:16} {info['si_unit']:16} "
              f"x {info['factor']:g}")
    print()
    print(f"{len(ANALYTES) + 2} analytes shipped "
          f"({len(ANALYTES)} linear, plus hba1c by master equation "
          "and bun -> urea).")
    print(f"{len(REFUSED)} names refused (no fixed factor): "
          + ", ".join(sorted(REFUSED)))
    return 0


def cmd_check(_args):
    failures, lines = core.run_check()
    print("labunits check -- built-in published worked pairs")
    for line in lines:
        print(line)
    if failures:
        print(f"result  : FAIL ({len(failures)} pair(s) off: "
              + ", ".join(failures) + ")")
        return 1
    print(f"result  : PASS ({len(lines)}/{len(lines)} worked pairs "
          "match published values)")
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 2
    try:
        if args.command == "convert":
            return cmd_convert(args)
        if args.command == "convert-one":
            return cmd_convert_one(args)
        if args.command == "list":
            return cmd_list(args)
        if args.command == "check":
            return cmd_check(args)
    except LabunitsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
