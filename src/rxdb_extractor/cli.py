import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shlex

from . import __version__
from .artifacts import hash_file
from .bridge import JsonSubprocessRuntime
from .dataset import run_slice
from .errors import RxdbError
from .manifest import semantic_hash
from .orchestration import PartitionOutcome, RunProvenance, run_partitions
from .partitions import load_partition_requests
from .persistent_bridge import JsonPersistentSubprocessRuntime
from .profile import compile_profile, load_profile
from .reports import read_validation_report
from .runtime import normalized_plan_executor
from .source_identity import rxdb_source_family_hash


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rxdb")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--bridge",
        help="JSON runtime bridge command, e.g. 'Rscript redengine_bridge.R'",
    )
    parser.add_argument(
        "--persistent-bridge",
        action="store_true",
        help="keep one bridge process/database open across requests (bridge must support --serve)",
    )
    parser.add_argument(
        "--bridge-timeout",
        type=float,
        default=120.0,
        help="seconds allowed for each bridge request",
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

    many = sub.add_parser(
        "extract-many",
        help="run a resumable profile extraction across an explicit partition inventory",
    )
    many.add_argument("database")
    many.add_argument("--profile", required=True, help="portable extraction profile JSON")
    many.add_argument(
        "--partitions",
        required=True,
        help="JSON/CSV/TSV/text partition inventory with selection_code values",
    )
    many.add_argument("--output-root", required=True)
    many.add_argument("--batch-width", type=int)
    many.add_argument(
        "--source-hash",
        help="precomputed exact source-family identity; otherwise RXDB/RBFX files are hashed",
    )
    many.add_argument(
        "--no-resume",
        action="store_true",
        help="ignore valid checkpoints and recompute requested partitions",
    )
    many.add_argument(
        "--limit",
        type=int,
        help="run only the first N partition requests (qualification/debugging)",
    )
    many.add_argument(
        "--workers",
        type=int,
        default=1,
        help="independent bridge/RedEngine workers; default 1, choose explicitly based on RAM",
    )

    validate = sub.add_parser("validate", help="read a persisted validation report")
    validate.add_argument("path")
    return parser


def _validation_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_dir():
        candidate = candidate / "validation.json"
    return candidate


def _bridge_runtime(command: str | None, *, persistent: bool, timeout: float):
    if command is None:
        return None
    parts = shlex.split(command)
    if persistent:
        return JsonPersistentSubprocessRuntime(parts, timeout_seconds=timeout)
    return JsonSubprocessRuntime(parts, timeout_seconds=timeout)


def _run_extract(args, runtime) -> int:
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
        "bridge_transport": (
            "persistent-json-lines" if args.persistent_bridge else "one-shot-json"
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
        "bridge_transport": provenance["bridge_transport"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.validation.passed else 1


def _run_partition_chunk(
    args,
    *,
    requests,
    output_root: Path,
    base_spec,
    provenance: RunProvenance,
) -> tuple[PartitionOutcome, ...]:
    worker_runtime = _bridge_runtime(
        args.bridge,
        persistent=args.persistent_bridge,
        timeout=args.bridge_timeout,
    )
    if worker_runtime is None:  # pragma: no cover - guarded by main
        raise ValueError("bridge runtime is required")
    try:
        execute = normalized_plan_executor(worker_runtime, args.database)
        return run_partitions(
            execute=execute,
            output_root=output_root,
            base_spec=base_spec,
            requests=requests,
            provenance=provenance,
            resume=not args.no_resume,
        )
    finally:
        close = getattr(worker_runtime, "close", None)
        if callable(close):
            close()


def _run_extract_many(args, runtime) -> int:
    requests = load_partition_requests(args.partitions)
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("--limit must be >= 1")
        requests = requests[: args.limit]
    if not requests:
        raise ValueError("no partitions selected")
    if args.workers < 1 or args.workers > 32:
        raise ValueError("--workers must be between 1 and 32")

    capabilities = runtime.capabilities()
    capabilities.require_record_extraction()
    inspection = runtime.inspect(args.database)
    profile = load_profile(args.profile)
    base_spec = compile_profile(
        inspection.schema,
        profile,
        selection_code=requests[0].selection_code,
        batch_width=args.batch_width,
        use_cmpcode=capabilities.cmpcode,
    )

    source_hash = args.source_hash or rxdb_source_family_hash(args.database)
    provenance = RunProvenance(
        source_hash=source_hash,
        schema_hash=semantic_hash(inspection.schema.to_dict()),
        profile_hash=semantic_hash(profile),
        runtime_hash=semantic_hash(capabilities.to_dict()),
    )
    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    worker_count = min(args.workers, len(requests))

    if worker_count == 1:
        execute = normalized_plan_executor(runtime, args.database)
        outcomes = run_partitions(
            execute=execute,
            output_root=output_root,
            base_spec=base_spec,
            requests=requests,
            provenance=provenance,
            resume=not args.no_resume,
        )
    else:
        # The inspection runtime is no longer needed. Closing it prevents an extra
        # persistent RedEngine process from consuming memory beside the N workers.
        close = getattr(runtime, "close", None)
        if callable(close):
            close()
        chunks = tuple(
            tuple(requests[index::worker_count]) for index in range(worker_count)
        )
        outcome_by_code: dict[str, PartitionOutcome] = {}
        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            futures = [
                pool.submit(
                    _run_partition_chunk,
                    args,
                    requests=chunk,
                    output_root=output_root,
                    base_spec=base_spec,
                    provenance=provenance,
                )
                for chunk in chunks
                if chunk
            ]
            for future in futures:
                for outcome in future.result():
                    outcome_by_code[outcome.selection_code] = outcome
        outcomes = tuple(outcome_by_code[request.selection_code] for request in requests)

    summary = {
        "status": "pass",
        "database": str(Path(args.database).expanduser().resolve()),
        "output_root": str(output_root),
        "partition_file": str(Path(args.partitions).expanduser().resolve()),
        "partition_file_sha256": hash_file(Path(args.partitions).expanduser().resolve()),
        "partition_count": len(outcomes),
        "completed": sum(item.status == "completed" for item in outcomes),
        "skipped": sum(item.status == "skipped" for item in outcomes),
        "workers": worker_count,
        "source_hash": source_hash,
        "profile_hash": provenance.profile_hash,
        "schema_hash": provenance.schema_hash,
        "runtime_hash": provenance.runtime_hash,
        "geography_key_mode": (
            "cmpcode" if capabilities.cmpcode else "selection-code-fallback"
        ),
        "bridge_transport": (
            "persistent-json-lines" if args.persistent_bridge else "one-shot-json"
        ),
        "partitions": [
            {
                "selection_code": item.selection_code,
                "status": item.status,
                "output_dir": item.output_dir,
                "checkpoint": item.checkpoint,
            }
            for item in outcomes
        ],
    }
    (output_root / "run-manifest.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    runtime = None
    try:
        if args.command == "validate":
            payload = read_validation_report(_validation_path(args.path))
            print(json.dumps(payload, indent=2, sort_keys=True))
            return 0 if payload.get("status") == "pass" else 1

        runtime = _bridge_runtime(
            args.bridge,
            persistent=args.persistent_bridge,
            timeout=args.bridge_timeout,
        )
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
        if args.command == "extract-many":
            return _run_extract_many(args, runtime)
    except (RxdbError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}))
        return 2
    finally:
        close = getattr(runtime, "close", None)
        if callable(close):
            close()

    return 2
