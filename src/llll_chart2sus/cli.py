"""Command-line interface for llll_chart2sus."""

from __future__ import annotations

import argparse
import sys

from .errors import Chart2SusError
from .pipeline import convert_chart_file, run_doctor, validate_sus_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llll_chart2sus")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Check Python/Rust toolchains and validator availability.")
    doctor.set_defaults(handler=handle_doctor)

    convert = sub.add_parser("convert", help="Convert LinkLike chart JSON to SUS.")
    convert.add_argument("--input", required=True, metavar="<chart.json>")
    convert.add_argument("--output", required=True, metavar="<chart.sus>")
    convert.add_argument("--strict", action="store_true", help="Enable stricter mapping checks.")
    convert.set_defaults(handler=handle_convert)

    validate = sub.add_parser("validate", help="Validate SUS with Python and Rust parser stacks.")
    validate.add_argument("--sus", required=True, metavar="<file.sus>")
    validate.add_argument("--svg-out", required=True, metavar="<file.svg>")
    validate.set_defaults(handler=handle_validate)

    return parser


def handle_doctor(args: argparse.Namespace) -> int:
    summary = run_doctor()
    for key in ("python", "pip", "uv", "cargo", "rustc", "scores", "pjsekai-scores-rs"):
        value = summary.get(key, "n/a")
        print(f"{key}: {value}")
    return 0


def handle_convert(args: argparse.Namespace) -> int:
    output = convert_chart_file(args.input, args.output, strict=args.strict)
    print(f"Converted chart written to: {output}")
    return 0


def handle_validate(args: argparse.Namespace) -> int:
    ok, message = validate_sus_file(args.sus, args.svg_out)
    print(message)
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except Chart2SusError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

