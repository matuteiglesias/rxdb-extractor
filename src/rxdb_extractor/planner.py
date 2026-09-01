from dataclasses import dataclass

from .errors import PlanningError


@dataclass(frozen=True)
class GeneratedId:
    entity: str
    field: str
    scope: str
    parent_field: str | None = None


@dataclass(frozen=True)
class RecordQueryPlan:
    entity: str
    selection_entity: str
    selection_code: str
    identity_scope: str
    own_id: str
    prelude_definitions: tuple[tuple[str, str, str], ...]
    parent_ids: tuple[str, ...]
    geography_fields: tuple[str, ...]
    variables: tuple[str, ...]
    spc: str


def _qualified(entity: str, field: str) -> str:
    return f"{entity}.{field}"


def build_record_query(
    *,
    entity: str,
    selection_entity: str,
    selection_code: str,
    identity_scope: str,
    own_id: str,
    prelude_definitions: tuple[tuple[str, str, str], ...] = (),
    parent_inheritance: tuple[tuple[str, str], ...] = (),
    geography_entities: tuple[str, ...] = (),
    variables: tuple[str, ...] = (),
    use_cmpcode: bool = True,
) -> RecordQueryPlan:
    """Build deterministic SPC for one record batch.

    ``prelude_definitions`` contains ordered ``(entity, field, expression)`` triples
    needed before the target entity is defined. This is how a PERSONA query can first
    define the VIVIENDA/HOGAR sequence variables that it later inherits.

    ``parent_inheritance`` contains ``(output_field, ancestor_expression)`` pairs,
    e.g. ``("XHID", "HOGAR.XHID")`` for PERSONA.
    """
    if not entity or not selection_entity or not identity_scope or not own_id:
        raise PlanningError("entity, selection, identity scope and own ID are required")
    if not selection_code:
        raise PlanningError("selection code is required")

    lines = [
        "RUNDEF RXDB_ROWS",
        f'SELECTION {selection_entity} == "{selection_code}"',
    ]

    seen_definitions: set[tuple[str, str]] = set()
    for target_entity, field, expression in prelude_definitions:
        if not target_entity or not field or not expression:
            raise PlanningError("prelude definitions require entity, field and expression")
        target = (target_entity, field)
        if target in seen_definitions:
            raise PlanningError(
                f"duplicate generated definition: {target_entity}.{field}"
            )
        seen_definitions.add(target)
        lines.append(f"DEFINE {target_entity}.{field} AS {expression}")

    own_target = (entity, own_id)
    if own_target in seen_definitions:
        raise PlanningError(f"prelude already defines own ID {entity}.{own_id}")
    lines.append(f"DEFINE {entity}.{own_id} AS NUMBER {identity_scope}")

    parent_fields: list[str] = []
    for output_field, source_expression in parent_inheritance:
        if not output_field or not source_expression:
            raise PlanningError("parent inheritance requires output field and expression")
        lines.append(f"DEFINE {entity}.{output_field} AS {source_expression}")
        parent_fields.append(output_field)

    geography_fields: list[str] = []
    if use_cmpcode:
        for geo in geography_entities:
            field = f"X{geo}"
            lines.append(
                f"DEFINE {entity}.{field} AS {geo}@cmpcode TYPE STRING SIZE 32"
            )
            geography_fields.append(field)

    dimensions = [
        _qualified(entity, own_id),
        *(_qualified(entity, f) for f in parent_fields),
        *(_qualified(entity, f) for f in geography_fields),
        *variables,
    ]
    if not dimensions:
        raise PlanningError("at least one FREQ dimension is required")

    lines.append("FREQ " + " BY ".join(dimensions))
    spc = "\n".join(lines)
    return RecordQueryPlan(
        entity=entity,
        selection_entity=selection_entity,
        selection_code=selection_code,
        identity_scope=identity_scope,
        own_id=own_id,
        prelude_definitions=prelude_definitions,
        parent_ids=tuple(parent_fields),
        geography_fields=tuple(geography_fields),
        variables=variables,
        spc=spc,
    )
