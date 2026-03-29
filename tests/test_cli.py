from __future__ import annotations

from llll_chart2sus.cli import build_parser


def test_cli_subcommands_exist():
    parser = build_parser()
    namespace = parser.parse_args(["convert", "--input", "a.json", "--output", "a.sus"])

    assert namespace.command == "convert"
    assert namespace.input == "a.json"
    assert namespace.output == "a.sus"

