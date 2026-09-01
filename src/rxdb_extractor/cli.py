import argparse
import json

from . import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rxdb")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")

    inspect = sub.add_parser("inspect", help="inspect an RXDB schema")
    inspect.add_argument("database")

    extract = sub.add_parser("extract", help="extract relational records")
    extract.add_argument("database")
    extract.add_argument("--entity", required=True)
    extract.add_argument("--output", required=True)

    validate = sub.add_parser("validate", help="validate an existing extraction")
    validate.add_argument("path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command is None:
        build_parser().print_help()
        return 0
    # Runtime execution deliberately lands after the stable pure contracts.
    print(json.dumps({"command": args.command, "status": "not-implemented"}))
    return 2
