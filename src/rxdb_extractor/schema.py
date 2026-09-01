from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .errors import SchemaError


@dataclass(frozen=True)
class Variable:
    name: str
    alias: str | None = None
    label: str | None = None
    type_name: str | None = None

    @property
    def ambiguous_name_alias(self) -> bool:
        return self.alias is not None and self.alias == self.name

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "alias": self.alias,
            "label": self.label,
            "type_name": self.type_name,
        }


@dataclass
class Entity:
    name: str
    alias: str | None = None
    parent: str | None = None
    selectable: bool = False
    variables: tuple[Variable, ...] = ()
    children: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "alias": self.alias,
            "parent": self.parent,
            "selectable": self.selectable,
            "variables": [variable.to_dict() for variable in self.variables],
        }


@dataclass
class DatabaseSchema:
    entities: dict[str, Entity]

    @classmethod
    def from_entities(cls, entities: list[Entity]) -> "DatabaseSchema":
        by_name: dict[str, Entity] = {}
        for entity in entities:
            if entity.name in by_name:
                raise SchemaError(f"duplicate entity: {entity.name}")
            entity.children = []
            by_name[entity.name] = entity
        for entity in by_name.values():
            if entity.parent is None:
                continue
            if entity.parent not in by_name:
                raise SchemaError(
                    f"entity {entity.name} references missing parent {entity.parent}"
                )
            by_name[entity.parent].children.append(entity.name)
        schema = cls(by_name)
        schema._assert_acyclic()
        return schema

    @classmethod
    def from_dict(cls, payload: Mapping[str, object]) -> "DatabaseSchema":
        raw_entities = payload.get("entities")
        if not isinstance(raw_entities, list):
            raise SchemaError("schema payload must contain an entities list")
        entities: list[Entity] = []
        for raw in raw_entities:
            if not isinstance(raw, dict) or not isinstance(raw.get("name"), str):
                raise SchemaError("every entity payload must contain a string name")
            raw_variables = raw.get("variables", [])
            if not isinstance(raw_variables, list):
                raise SchemaError(f"entity {raw['name']} variables must be a list")
            variables: list[Variable] = []
            for variable in raw_variables:
                if not isinstance(variable, dict) or not isinstance(variable.get("name"), str):
                    raise SchemaError("every variable payload must contain a string name")
                alias = variable.get("alias")
                label = variable.get("label")
                type_name = variable.get("type_name")
                if alias is not None and not isinstance(alias, str):
                    raise SchemaError("variable alias must be string or null")
                if label is not None and not isinstance(label, str):
                    raise SchemaError("variable label must be string or null")
                if type_name is not None and not isinstance(type_name, str):
                    raise SchemaError("variable type_name must be string or null")
                variables.append(Variable(variable["name"], alias, label, type_name))
            alias = raw.get("alias")
            parent = raw.get("parent")
            if alias is not None and not isinstance(alias, str):
                raise SchemaError("entity alias must be string or null")
            if parent is not None and not isinstance(parent, str):
                raise SchemaError("entity parent must be string or null")
            entities.append(
                Entity(
                    name=raw["name"],
                    alias=alias,
                    parent=parent,
                    selectable=bool(raw.get("selectable", False)),
                    variables=tuple(variables),
                )
            )
        return cls.from_entities(entities)

    def to_dict(self) -> dict[str, object]:
        return {"entities": [entity.to_dict() for entity in self.entities.values()]}

    def with_parent_map(self, parent_map: Mapping[str, str | None]) -> "DatabaseSchema":
        """Apply a validated external hierarchy without mutating this schema.

        Existing non-null runtime parents are treated as evidence and must agree with
        the supplied map. This permits flat metadata APIs to be augmented by an adapter
        profile without ever silently overriding contradictory runtime information.
        """
        unknown = set(parent_map) - set(self.entities)
        if unknown:
            raise SchemaError(
                "parent map references unknown entities: " + ", ".join(sorted(unknown))
            )
        cloned: list[Entity] = []
        for entity in self.entities.values():
            requested = parent_map.get(entity.name, entity.parent)
            if entity.parent is not None and entity.name in parent_map and requested != entity.parent:
                raise SchemaError(
                    f"parent map conflicts for {entity.name}: runtime={entity.parent!r} profile={requested!r}"
                )
            if requested is not None and requested not in self.entities:
                raise SchemaError(
                    f"parent map for {entity.name} references missing entity {requested}"
                )
            cloned.append(
                Entity(
                    name=entity.name,
                    alias=entity.alias,
                    parent=requested,
                    selectable=entity.selectable,
                    variables=entity.variables,
                )
            )
        return DatabaseSchema.from_entities(cloned)

    def _assert_acyclic(self) -> None:
        for name in self.entities:
            seen: set[str] = set()
            cur: str | None = name
            while cur is not None:
                if cur in seen:
                    raise SchemaError(f"entity cycle detected at {cur}")
                seen.add(cur)
                cur = self.entities[cur].parent

    def ancestors(self, entity_name: str) -> list[Entity]:
        if entity_name not in self.entities:
            raise SchemaError(f"unknown entity: {entity_name}")
        result: list[Entity] = []
        cur = self.entities[entity_name].parent
        while cur is not None:
            result.append(self.entities[cur])
            cur = self.entities[cur].parent
        result.reverse()
        return result

    def descendants(self, entity_name: str) -> list[Entity]:
        if entity_name not in self.entities:
            raise SchemaError(f"unknown entity: {entity_name}")
        result: list[Entity] = []
        stack = list(reversed(self.entities[entity_name].children))
        while stack:
            name = stack.pop()
            entity = self.entities[name]
            result.append(entity)
            stack.extend(reversed(entity.children))
        return result

    def path(self, ancestor_name: str, descendant_name: str) -> list[Entity]:
        if ancestor_name not in self.entities or descendant_name not in self.entities:
            raise SchemaError("path endpoints must be known entities")
        chain = [self.entities[descendant_name]]
        cur = self.entities[descendant_name].parent
        while cur is not None and cur != ancestor_name:
            chain.append(self.entities[cur])
            cur = self.entities[cur].parent
        if cur != ancestor_name:
            raise SchemaError(f"{ancestor_name} is not an ancestor of {descendant_name}")
        chain.append(self.entities[ancestor_name])
        chain.reverse()
        return chain

    def nearest_selectable_ancestor(self, entity_name: str) -> Entity:
        ancestors = self.ancestors(entity_name)
        for entity in reversed(ancestors):
            if entity.selectable:
                return entity
        raise SchemaError(f"no selectable ancestor for {entity_name}")

    def leaves(self) -> list[Entity]:
        return [entity for entity in self.entities.values() if not entity.children]
