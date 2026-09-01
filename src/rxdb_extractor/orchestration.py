from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
import re
from typing import Mapping, Sequence

from . import __version__
from .artifacts import hash_file
from .checkpoint import CheckpointStore, SliceCheckpoint
from .dataset import PlanExecutor, SliceSpec, run_slice
from .errors import CheckpointError, ValidationError
from .manifest import semantic_hash


@dataclass(frozen=True)
class RunProvenance:
    source_hash: str
    schema_hash: str
    profile_hash: str
    runtime_hash: str
    extractor_version: str = __version__

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PartitionRequest:
    selection_code: str
    expected_counts: Mapping[str, int] | None = None


@dataclass(frozen=True)
class PartitionOutcome:
    selection_code: str
    status: str
    output_dir: str
    checkpoint: str


def _safe_component(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    if not cleaned:
        cleaned = semantic_hash({"value": value})[:16]
    return cleaned[:120]


def partition_output_dir(root: str | Path, selection_entity: str, selection_code: str) -> Path:
    return Path(root) / f"{selection_entity.lower()}={_safe_component(selection_code)}"


def checkpoint_name(selection_entity: str, selection_code: str) -> str:
    human = _safe_component(selection_code)[:48]
    suffix = semantic_hash({"code": selection_code})[:12]
    return f"{selection_entity.lower()}-{human}-{suffix}"


def _spec_contract(spec: SliceSpec) -> dict[str, object]:
    return {
        "selection_entity": spec.selection_entity,
        "identity_scope": spec.identity_scope,
        "scope_field": spec.scope_field,
        "batch_width": spec.batch_width,
        "use_cmpcode": spec.use_cmpcode,
        "entities": [
            {
                "entity": job.entity,
                "own_id": job.own_id,
                "variables": list(job.variables),
                "prelude_definitions": [list(item) for item in job.prelude_definitions],
                "parent_inheritance": [list(item) for item in job.parent_inheritance],
                "geography_entities": list(job.geography_entities),
                "blocked_variables": sorted(job.blocked_variables),
                "keys": [asdict(key) for key in job.keys],
                "primary_key": job.primary_key,
            }
            for job in spec.entities
        ],
        "foreign_keys": [asdict(item) for item in spec.foreign_keys],
    }


def partition_identity(
    spec: SliceSpec,
    request: PartitionRequest,
    provenance: RunProvenance,
) -> str:
    return semantic_hash(
        {
            "provenance": provenance.to_dict(),
            "contract": _spec_contract(spec),
            "selection_code": request.selection_code,
            "expected_counts": dict(sorted((request.expected_counts or {}).items())),
        }
    )


def _checkpoint_artifacts_valid(output_dir: Path, checkpoint: SliceCheckpoint) -> bool:
    try:
        for entity, expected_hash in checkpoint.output_hashes.items():
            artifact = output_dir / f"{entity.lower()}.parquet"
            if not artifact.is_file() or hash_file(artifact) != expected_hash:
                return False
        manifest_path = output_dir / "dataset-manifest.json"
        if not manifest_path.is_file():
            return False
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return manifest.get("semantic_hash") == checkpoint.dataset_manifest_hash
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def _load_valid_checkpoint(
    store: CheckpointStore,
    *,
    name: str,
    identity: str,
    output_dir: Path,
) -> SliceCheckpoint | None:
    if not store.matches_slice(name, identity):
        return None
    try:
        checkpoint = store.read_slice(name)
    except CheckpointError:
        return None
    return checkpoint if _checkpoint_artifacts_valid(output_dir, checkpoint) else None


def run_partitions(
    *,
    execute: PlanExecutor,
    output_root: str | Path,
    base_spec: SliceSpec,
    requests: Sequence[PartitionRequest],
    provenance: RunProvenance,
    resume: bool = True,
) -> tuple[PartitionOutcome, ...]:
    """Run selected-area slices with provenance-aware, artifact-verified resume."""

    root = Path(output_root)
    checkpoint_store = CheckpointStore(root / ".checkpoints")
    outcomes: list[PartitionOutcome] = []

    for request in requests:
        if not request.selection_code:
            raise ValueError("partition selection code must not be empty")
        spec = replace(base_spec, selection_code=request.selection_code)
        identity = partition_identity(spec, request, provenance)
        name = checkpoint_name(spec.selection_entity, request.selection_code)
        output_dir = partition_output_dir(root, spec.selection_entity, request.selection_code)

        checkpoint = (
            _load_valid_checkpoint(
                checkpoint_store,
                name=name,
                identity=identity,
                output_dir=output_dir,
            )
            if resume
            else None
        )
        if checkpoint is not None:
            outcomes.append(
                PartitionOutcome(
                    request.selection_code,
                    "skipped",
                    str(output_dir),
                    str(checkpoint_store.path_for(name)),
                )
            )
            continue

        # A stale success marker must never survive an attempted recomputation.
        checkpoint_store.invalidate(name)
        result = run_slice(
            execute=execute,
            output_dir=output_dir,
            spec=spec,
            provenance={
                **provenance.to_dict(),
                "checkpoint_identity": identity,
            },
            expected_counts=request.expected_counts,
        )
        if not result.validation.passed:
            failures = [check.name for check in result.validation.checks if not check.passed]
            raise ValidationError(
                f"partition {request.selection_code} failed validation: {', '.join(failures)}"
            )

        row_counts = {
            entity: len(entity_result.rows)
            for entity, entity_result in result.entities.items()
        }
        output_hashes = {
            entity: entity_result.artifact.sha256
            for entity, entity_result in result.entities.items()
        }
        checkpoint = SliceCheckpoint(
            checkpoint_identity=identity,
            selection_entity=spec.selection_entity,
            selection_code=request.selection_code,
            row_counts=row_counts,
            output_hashes=output_hashes,
            dataset_manifest_hash=str(result.manifest["semantic_hash"]),
            validation_status="pass",
        )
        checkpoint_path = checkpoint_store.write_slice(name, checkpoint)
        outcomes.append(
            PartitionOutcome(
                request.selection_code,
                "completed",
                str(output_dir),
                str(checkpoint_path),
            )
        )

    return tuple(outcomes)
