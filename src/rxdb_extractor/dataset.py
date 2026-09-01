from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from .artifacts import ParquetArtifact, write_parquet_atomic
from .executor import EntityExtraction, PlanExecutor, extract_entity_batches
from .identity import add_canonical_keys
from .manifest import semantic_hash, write_json_atomic
from .reports import ValidationReport, build_validation_report, write_validation_report
from .validation import CheckResult, validate_foreign_key, validate_unique_key


@dataclass(frozen=True)
class KeyProjection:
    sequence_field: str
    output_field: str


@dataclass(frozen=True)
class EntityJob:
    entity: str
    own_id: str
    variables: tuple[str, ...] = ()
    parent_inheritance: tuple[tuple[str, str], ...] = ()
    geography_entities: tuple[str, ...] = ()
    blocked_variables: frozenset[str] = frozenset()
    keys: tuple[KeyProjection, ...] = ()
    primary_key: str | None = None


@dataclass(frozen=True)
class ForeignKeyJob:
    child_entity: str
    child_field: str
    parent_entity: str
    parent_field: str


@dataclass(frozen=True)
class SliceSpec:
    selection_entity: str
    selection_code: str
    identity_scope: str
    scope_field: str
    entities: tuple[EntityJob, ...]
    foreign_keys: tuple[ForeignKeyJob, ...] = ()
    batch_width: int = 5
    use_cmpcode: bool = True


@dataclass(frozen=True)
class EntityResult:
    extraction: EntityExtraction
    artifact: ParquetArtifact
    rows: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class SliceResult:
    entities: Mapping[str, EntityResult]
    validation: ValidationReport
    manifest: Mapping[str, object]


def _project_keys(
    rows: tuple[dict[str, object], ...],
    *,
    scope_field: str,
    keys: tuple[KeyProjection, ...],
) -> tuple[dict[str, object], ...]:
    current = list(rows)
    for key in keys:
        current = add_canonical_keys(
            current,
            scope_field=scope_field,
            sequence_field=key.sequence_field,
            output_field=key.output_field,
        )
    return tuple(current)


def run_slice(
    *,
    execute: PlanExecutor,
    output_dir: str | Path,
    spec: SliceSpec,
    provenance: Mapping[str, object] | None = None,
) -> SliceResult:
    """Run a fully configured multi-entity extraction slice.

    The executor callback is the only live-runtime boundary. Everything else—batching,
    key projection, Parquet persistence, PK/FK validation and manifests—is runtime
    independent and can be exercised with deterministic fixtures.
    """

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    results: dict[str, EntityResult] = {}
    checks: list[CheckResult] = []

    for job in spec.entities:
        extraction = extract_entity_batches(
            execute=execute,
            entity=job.entity,
            selection_entity=spec.selection_entity,
            selection_code=spec.selection_code,
            identity_scope=spec.identity_scope,
            own_id=job.own_id,
            parent_inheritance=job.parent_inheritance,
            geography_entities=job.geography_entities,
            variables=job.variables,
            batch_width=spec.batch_width,
            blocked_variables=job.blocked_variables,
            use_cmpcode=spec.use_cmpcode,
        )
        rows = _project_keys(
            extraction.rows,
            scope_field=spec.scope_field,
            keys=job.keys,
        )
        artifact = write_parquet_atomic(
            destination / f"{job.entity.lower()}.parquet",
            rows,
        )
        results[job.entity] = EntityResult(extraction, artifact, rows)
        if job.primary_key is not None:
            checks.append(validate_unique_key(rows, job.primary_key))

    for relation in spec.foreign_keys:
        child = results[relation.child_entity].rows
        parent = results[relation.parent_entity].rows
        checks.append(
            validate_foreign_key(
                child,
                child_field=relation.child_field,
                parent_rows=parent,
                parent_key=relation.parent_field,
            )
        )

    validation = build_validation_report(checks)
    write_validation_report(destination / "validation.json", validation)

    entity_manifest: dict[str, object] = {}
    for name, result in results.items():
        artifact = result.artifact.to_dict()
        artifact["path"] = Path(result.artifact.path).relative_to(destination).as_posix()
        entity_manifest[name] = {
            "artifact": artifact,
            "blocked_variables": list(result.extraction.blocked_variables),
            "query_hashes": [
                semantic_hash({"spc": plan.spc}) for plan in result.extraction.plans
            ],
        }

    manifest: dict[str, object] = {
        "manifest_version": "1",
        "selection": {
            "entity": spec.selection_entity,
            "code": spec.selection_code,
        },
        "identity_scope": spec.identity_scope,
        "scope_field": spec.scope_field,
        "batch_width": spec.batch_width,
        "entities": entity_manifest,
        "validation_status": "pass" if validation.passed else "fail",
        "provenance": dict(provenance or {}),
    }
    manifest["semantic_hash"] = semantic_hash(manifest)
    write_json_atomic(destination / "dataset-manifest.json", manifest)
    return SliceResult(results, validation, manifest)
