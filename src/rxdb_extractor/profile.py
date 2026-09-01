from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from .dataset import EntityJob, ForeignKeyJob, KeyProjection, SliceSpec
from .errors import PlanningError, SchemaError
from .hierarchy import build_hierarchy_projection
from .schema import DatabaseSchema


def load_profile(path: str | Path) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PlanningError("profile must be a JSON object")
    return payload


def _string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise PlanningError(f"profile field {key!r} must be a non-empty string")
    return value


def _strings(payload: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = payload.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise PlanningError(f"profile field {key!r} must be a list of strings")
    return tuple(value)


def _id_fields(payload: Mapping[str, object]) -> dict[str, str]:
    raw = payload.get("id_fields")
    if not isinstance(raw, dict) or not raw:
        raise PlanningError("profile id_fields must be a non-empty object")
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in raw.items()):
        raise PlanningError("profile id_fields must map strings to strings")
    return dict(raw)


def _parent_map(payload: Mapping[str, object]) -> dict[str, str | None]:
    raw = payload.get("parent_map")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise PlanningError("profile parent_map must be an object")
    output: dict[str, str | None] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or (value is not None and not isinstance(value, str)):
            raise PlanningError("profile parent_map must map strings to strings/null")
        output[key] = value
    return output


def _stored_variables(
    schema: DatabaseSchema,
    *,
    entity_name: str,
    policy: str,
    blocked: frozenset[str],
) -> tuple[str, ...]:
    if entity_name not in schema.entities:
        raise PlanningError(f"profile references unknown entity {entity_name}")
    if policy != "all-stored":
        raise PlanningError(f"unsupported variable policy {policy!r} for {entity_name}")

    variables: list[str] = []
    for variable in schema.entities[entity_name].variables:
        qualified = f"{entity_name}.{variable.name}"
        if variable.ambiguous_name_alias and qualified not in blocked:
            raise PlanningError(
                f"ambiguous variable {qualified} must be explicitly blocked by profile"
            )
        variables.append(qualified)
    unknown_blocked = blocked - set(variables)
    if unknown_blocked:
        raise PlanningError(
            "profile blocks variables absent from schema: "
            + ", ".join(sorted(unknown_blocked))
        )
    return tuple(variables)


def compile_profile(
    schema: DatabaseSchema,
    profile: Mapping[str, object],
    *,
    selection_code: str,
    batch_width: int | None = None,
    use_cmpcode: bool = True,
) -> SliceSpec:
    """Compile a portable adapter profile into the generic extraction contract.

    A profile may supply ``parent_map`` when the runtime's metadata API is flat. Any
    parent relationship already supplied by the runtime must agree with the profile.
    """

    parent_map = _parent_map(profile)
    if parent_map:
        try:
            schema = schema.with_parent_map(parent_map)
        except SchemaError as exc:
            raise PlanningError(f"profile hierarchy is incompatible with runtime: {exc}") from exc

    selection_entity = _string(profile, "selection_entity")
    identity_scope = _string(profile, "identity_scope")
    scope_field = _string(profile, "scope_field")
    geography_entities = _strings(profile, "geography_entities")
    id_fields = _id_fields(profile)

    if selection_entity not in schema.entities:
        raise PlanningError(f"selection entity {selection_entity} is absent from schema")
    if not schema.entities[selection_entity].selectable:
        raise PlanningError(f"selection entity {selection_entity} is not selectable")
    if identity_scope not in schema.entities:
        raise PlanningError(f"identity scope {identity_scope} is absent from schema")
    if not selection_code:
        raise PlanningError("selection code is required")

    raw_entities = profile.get("entities")
    if not isinstance(raw_entities, list) or not raw_entities:
        raise PlanningError("profile entities must be a non-empty list")

    jobs: list[EntityJob] = []
    for raw in raw_entities:
        if not isinstance(raw, dict):
            raise PlanningError("every profile entity must be an object")
        entity = _string(raw, "entity")
        own_id = _string(raw, "own_id")
        if id_fields.get(entity) != own_id:
            raise PlanningError(
                f"profile own ID mismatch for {entity}: {own_id!r} != {id_fields.get(entity)!r}"
            )
        ancestor_names = {item.name for item in schema.ancestors(entity)}
        if selection_entity not in ancestor_names:
            raise PlanningError(f"{selection_entity} is not an ancestor of {entity}")
        if identity_scope not in ancestor_names:
            raise PlanningError(f"{identity_scope} is not an ancestor of {entity}")
        unknown_geo = [geo for geo in geography_entities if geo not in ancestor_names]
        if unknown_geo:
            raise PlanningError(
                f"geography entities are not ancestors of {entity}: {', '.join(unknown_geo)}"
            )

        blocked = frozenset(_strings(raw, "blocked_variables"))
        variables = _stored_variables(
            schema,
            entity_name=entity,
            policy=_string(raw, "variable_policy"),
            blocked=blocked,
        )
        projection = build_hierarchy_projection(
            schema,
            target_entity=entity,
            identity_scope=identity_scope,
            id_fields=id_fields,
        )

        raw_keys = raw.get("keys", [])
        if not isinstance(raw_keys, list):
            raise PlanningError(f"profile keys for {entity} must be a list")
        keys: list[KeyProjection] = []
        for key in raw_keys:
            if not isinstance(key, dict):
                raise PlanningError(f"profile key for {entity} must be an object")
            keys.append(
                KeyProjection(
                    _string(key, "sequence_field"),
                    _string(key, "output_field"),
                )
            )

        primary_key = _string(raw, "primary_key")
        jobs.append(
            EntityJob(
                entity=entity,
                own_id=own_id,
                variables=variables,
                prelude_definitions=projection.prelude_definitions,
                parent_inheritance=projection.parent_inheritance,
                geography_entities=geography_entities,
                blocked_variables=blocked,
                keys=tuple(keys),
                primary_key=primary_key,
            )
        )

    raw_relations = profile.get("foreign_keys", [])
    if not isinstance(raw_relations, list):
        raise PlanningError("profile foreign_keys must be a list")
    relations: list[ForeignKeyJob] = []
    for raw in raw_relations:
        if not isinstance(raw, dict):
            raise PlanningError("every profile foreign key must be an object")
        relations.append(
            ForeignKeyJob(
                _string(raw, "child_entity"),
                _string(raw, "child_field"),
                _string(raw, "parent_entity"),
                _string(raw, "parent_field"),
            )
        )

    raw_width = batch_width if batch_width is not None else profile.get("batch_width", 5)
    if isinstance(raw_width, bool) or not isinstance(raw_width, int):
        raise PlanningError("batch width must be an integer")
    if raw_width < 1:
        raise PlanningError("batch width must be >= 1")
    return SliceSpec(
        selection_entity=selection_entity,
        selection_code=selection_code,
        identity_scope=identity_scope,
        scope_field=scope_field,
        entities=tuple(jobs),
        foreign_keys=tuple(relations),
        batch_width=raw_width,
        use_cmpcode=use_cmpcode,
    )
