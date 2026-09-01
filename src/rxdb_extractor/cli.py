import argparse
import json
from pathlib import Path

from . import __version__
from .reports import read_validation_report


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

    validate = sub.add_parser("validate", help="read a persisted validation report")
    validate.add_argument("path")
    return parser


def _validation_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_dir():
        candidate = candidate / "validation.json"
    return candidate


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "validate":
        payload = read_validation_report(_validation_path(args.path))
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload.get("status") == "pass" else 1

    # Live runtime execution deliberately lands after the stable pure contracts.
    print(json.dumps({"command": args.command, "status": "runtime-not-configured"}))
    return 2
