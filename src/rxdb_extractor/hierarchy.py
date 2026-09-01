from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .errors import PlanningError
from .schema import DatabaseSchema


@dataclass(frozen=True)
class HierarchyProjection:
    prelude_definitions: tuple[tuple[str, str, str], ...]
    parent_inheritance: tuple[tuple[str, str], ...]


def build_hierarchy_projection(
    schema: DatabaseSchema,
    *,
    target_entity: str,
    identity_scope: str,
    id_fields: Mapping[str, str],
) -> HierarchyProjection:
    """Derive generated-ID propagation for a target entity from the entity graph.

    ``id_fields`` identifies the record entities that should receive source-native
    sequence IDs. For a VIVIENDA > HOGAR > PERSONA chain this can be
    ``{"VIVIENDA": "XVID", "HOGAR": "XHID", "PERSONA": "XPID"}``.

    Ancestor record entities are defined in order. Each one carries forward the IDs
    of earlier record ancestors, so the target can inherit all parent keys from its
    nearest record parent. This mirrors the experimentally validated REDATAM hierarchy.
    """
    if target_entity not in schema.entities:
        raise PlanningError(f"unknown target entity: {target_entity}")
    if target_entity not in id_fields:
        raise PlanningError(f"missing generated ID field for target {target_entity}")
    if not identity_scope:
        raise PlanningError("identity scope is required")

    ancestors = schema.ancestors(target_entity)
    record_ancestors = [entity for entity in ancestors if entity.name in id_fields]

    prelude: list[tuple[str, str, str]] = []
    carried: list[tuple[str, str]] = []
    for ancestor in record_ancestors:
        own_field = id_fields[ancestor.name]
        prelude.append((ancestor.name, own_field, f"NUMBER {identity_scope}"))
        for earlier_entity, earlier_field in carried:
            prelude.append(
                (ancestor.name, earlier_field, f"{earlier_entity}.{earlier_field}")
            )
        carried.append((ancestor.name, own_field))

    inheritance: list[tuple[str, str]] = []
    if record_ancestors:
        nearest = record_ancestors[-1].name
        for _, field in carried:
            inheritance.append((field, f"{nearest}.{field}"))

    return HierarchyProjection(tuple(prelude), tuple(inheritance))
