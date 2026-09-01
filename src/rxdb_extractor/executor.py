from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from .artifacts import ParquetArtifact, write_parquet_atomic
from .batching import VariableBatch, batch_variables
from .merge import merge_record_batches
from .planner import RecordQueryPlan, build_record_query


PlanExecutor = Callable[[RecordQueryPlan], list[dict[str, object]]]


@dataclass(frozen=True)
class EntityExtraction:
    entity: str
    plans: tuple[RecordQueryPlan, ...]
    rows: tuple[dict[str, object], ...]
    blocked_variables: tuple[str, ...] = ()


@dataclass(frozen=True)
class PersistedEntityExtraction:
    extraction: EntityExtraction
    artifact: ParquetArtifact


def _variable_batches(
    variables: tuple[str, ...],
    *,
    width: int,
    blocked: frozenset[str],
) -> tuple[VariableBatch, ...]:
    batches = batch_variables(variables, width=width, blocked=blocked)
    # ID-only extraction is still meaningful and provides a count/identity proof.
    return batches or (VariableBatch(0, ()),)


def extract_entity_batches(
    *,
    execute: PlanExecutor,
    entity: str,
    selection_entity: str,
    selection_code: str,
    identity_scope: str,
    own_id: str,
    parent_inheritance: tuple[tuple[str, str], ...] = (),
    geography_entities: tuple[str, ...] = (),
    variables: tuple[str, ...] = (),
    batch_width: int = 5,
    blocked_variables: frozenset[str] = frozenset(),
    use_cmpcode: bool = True,
) -> EntityExtraction:
    plans: list[RecordQueryPlan] = []
    normalized_batches: list[list[dict[str, object]]] = []

    for batch in _variable_batches(
        variables, width=batch_width, blocked=blocked_variables
    ):
        plan = build_record_query(
            entity=entity,
            selection_entity=selection_entity,
            selection_code=selection_code,
            identity_scope=identity_scope,
            own_id=own_id,
            parent_inheritance=parent_inheritance,
            geography_entities=geography_entities,
            variables=batch.variables,
            use_cmpcode=use_cmpcode,
        )
        plans.append(plan)
        normalized_batches.append(execute(plan))

    rows = merge_record_batches(normalized_batches, key_field=own_id)
    blocked = tuple(variable for variable in variables if variable in blocked_variables)
    return EntityExtraction(
        entity=entity,
        plans=tuple(plans),
        rows=tuple(rows),
        blocked_variables=blocked,
    )


def extract_entity_to_parquet(
    output: str | Path,
    **kwargs: object,
) -> PersistedEntityExtraction:
    extraction = extract_entity_batches(**kwargs)  # type: ignore[arg-type]
    artifact = write_parquet_atomic(output, extraction.rows)
    return PersistedEntityExtraction(extraction=extraction, artifact=artifact)
