from __future__ import annotations

from collections.abc import Callable
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
    return batch_variables(variables, width=width, blocked=blocked)


def extract_entity_batches(
    *,
    execute: PlanExecutor,
    entity: str,
    selection_entity: str,
    selection_code: str,
    identity_scope: str,
    own_id: str,
    prelude_definitions: tuple[tuple[str, str, str], ...] = (),
    parent_inheritance: tuple[tuple[str, str], ...] = (),
    geography_entities: tuple[str, ...] = (),
    variables: tuple[str, ...] = (),
    batch_width: int = 5,
    blocked_variables: frozenset[str] = frozenset(),
    use_cmpcode: bool = True,
) -> EntityExtraction:
    """Extract one entity using an identity backbone plus narrow payload batches.

    Parent IDs and geography are recovered exactly once in a low-dimensional identity
    query. Stored variables are then extracted in separate batches keyed only by the
    entity's own deterministic NUMBER sequence. This keeps arbitrary payload variables
    from perturbing hierarchy recovery and reduces FREQ dimensionality. All pieces are
    joined by the explicit own ID; positional assembly is never used.
    """

    plans: list[RecordQueryPlan] = []
    normalized_batches: list[list[dict[str, object]]] = []

    # Stable identity/hierarchy backbone. This is deliberately independent of stored
    # Census variables and therefore remains small and easy to validate.
    identity_plan = build_record_query(
        entity=entity,
        selection_entity=selection_entity,
        selection_code=selection_code,
        identity_scope=identity_scope,
        own_id=own_id,
        prelude_definitions=prelude_definitions,
        parent_inheritance=parent_inheritance,
        geography_entities=geography_entities,
        variables=(),
        use_cmpcode=use_cmpcode,
    )
    plans.append(identity_plan)
    normalized_batches.append(execute(identity_plan))

    # Payload batches need only the entity's own deterministic ID. Parent IDs and
    # geography come from the backbone above and are merged by that explicit key.
    for batch in _variable_batches(
        variables, width=batch_width, blocked=blocked_variables
    ):
        plan = build_record_query(
            entity=entity,
            selection_entity=selection_entity,
            selection_code=selection_code,
            identity_scope=identity_scope,
            own_id=own_id,
            prelude_definitions=(),
            parent_inheritance=(),
            geography_entities=(),
            variables=batch.variables,
            use_cmpcode=False,
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
