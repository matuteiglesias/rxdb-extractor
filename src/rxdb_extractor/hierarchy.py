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

    Every record ancestor receives its own ``NUMBER <scope>`` definition in the
    prelude. The target then inherits each ancestor ID *directly from the ancestor
    that owns it*. We deliberately do not relay an older ancestor ID through the
    nearest record parent. The direct form is the experimentally qualified RedEngine
    primitive and avoids missing-value propagation on older runtimes, e.g. PERSONA
    must use ``VIVIENDA.XVID`` rather than ``HOGAR.XVID`` for its dwelling identity.
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
    for ancestor in record_ancestors:
        own_field = id_fields[ancestor.name]
        prelude.append((ancestor.name, own_field, f"NUMBER {identity_scope}"))

    inheritance = [
        (id_fields[ancestor.name], f"{ancestor.name}.{id_fields[ancestor.name]}")
        for ancestor in record_ancestors
    ]

    return HierarchyProjection(tuple(prelude), tuple(inheritance))
