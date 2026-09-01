from dataclasses import dataclass, field

from .errors import SchemaError


@dataclass(frozen=True)
class Variable:
    name: str
    alias: str | None = None
    label: str | None = None

    @property
    def ambiguous_name_alias(self) -> bool:
        return self.alias is not None and self.alias == self.name


@dataclass
class Entity:
    name: str
    alias: str | None = None
    parent: str | None = None
    selectable: bool = False
    variables: tuple[Variable, ...] = ()
    children: list[str] = field(default_factory=list)


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

    def nearest_selectable_ancestor(self, entity_name: str) -> Entity:
        ancestors = self.ancestors(entity_name)
        for entity in reversed(ancestors):
            if entity.selectable:
                return entity
        raise SchemaError(f"no selectable ancestor for {entity_name}")

    def leaves(self) -> list[Entity]:
        return [entity for entity in self.entities.values() if not entity.children]
