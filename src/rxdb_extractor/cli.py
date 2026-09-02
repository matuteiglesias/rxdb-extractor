import argparse
import json
from pathlib import Path
import shlex

from . import __version__
from .bridge import JsonSubprocessRuntime
from .dataset import run_slice
from .errors import RxdbError
from .manifest import semantic_hash
from .profile import compile_profile, load_profile
from .reports import read_validation_report
from .runtime import normalized_plan_executor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rxdb")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--bridge",
        help="JSON runtime bridge command, e.g. 'Rscript redengine_bridge.R'",
    )
    sub = parser.add_subparsers(dest="command")

    inspect = sub.add_parser("inspect", help="inspect an RXDB schema through a runtime bridge")
    inspect.add_argument("database")

    extract = sub.add_parser("extract", help="extract a profile-defined relational slice")
    extract.add_argument("database")
    extract.add_argument("--profile", required=True, help="portable extraction profile JSON")
    extract.add_argument("--selection-code", required=True)
    extract.add_argument("--output", required=True)
    extract.add_argument("--batch-width", type=int)

    validate = sub.add_parser("validate", help="read a persisted validation report")
    validate.add_argument("path")
    return parser


def _validation_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_dir():
        candidate = candidate / "validation.json"
    return candidate


def _bridge_runtime(command: str | None) -> JsonSubprocessRuntime | None:
    if command is None:
        return None
    parts = shlex.split(command)
    return JsonSubprocessRuntime(parts)


def _run_extract(args, runtime: JsonSubprocessRuntime) -> int:
    capabilities = runtime.capabilities()
    capabilities.require_record_extraction()

    inspection = runtime.inspect(args.database)
    profile = load_profile(args.profile)
    spec = compile_profile(
        inspection.schema,
        profile,
        selection_code=args.selection_code,
        batch_width=args.batch_width,
        use_cmpcode=capabilities.cmpcode,
    )
    execute = normalized_plan_executor(runtime, args.database)
    provenance = {
        "runtime": capabilities.to_dict(),
        "database_metadata": dict(inspection.metadata),
        "profile_hash": semantic_hash(profile),
        "geography_key_mode": (
            "cmpcode" if capabilities.cmpcode else "selection-code-fallback"
        ),
    }
    result = run_slice(
        execute=execute,
        output_dir=args.output,
        spec=spec,
        provenance=provenance,
    )
    payload = {
        "status": "pass" if result.validation.passed else "fail",
        "output": str(Path(args.output)),
        "manifest": str(Path(args.output) / "dataset-manifest.json"),
        "validation": str(Path(args.output) / "validation.json"),
        "geography_key_mode": provenance["geography_key_mode"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.validation.passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    try:
        if args.command == "validate":
            payload = read_validation_report(_validation_path(args.path))
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload.get("status") == "pass" else 1

        runtime = _bridge_runtime(args.bridge)
        if runtime is None:
            print(json.dumps({"command": args.command, "status": "runtime-not-configured"}))
            return 2

        if args.command == "inspect":
            payload = {
                "capabilities": runtime.capabilities().to_dict(),
                "database": runtime.inspect(args.database).to_dict(),
            }
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0

        if args.command == "extract":
            return _run_extract(args, runtime)
    except (RxdbError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2

    return 2
