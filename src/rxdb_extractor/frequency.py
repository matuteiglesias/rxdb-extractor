from __future__ import annotations

from dataclasses import asdict, dataclass

from .errors import PlanningError


@dataclass(frozen=True)
class FrequencyQuery:
    entity: str
    selection_entity: str
    selection_code: str
    source_expression: str
    output_field: str
    spc: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def build_frequency_query(
    *,
    entity: str,
    selection_entity: str,
    selection_code: str,
    source_expression: str,
) -> FrequencyQuery:
    if not all((entity, selection_entity, selection_code, source_expression)):
        raise PlanningError("frequency query fields must be non-empty")
    if not source_expression.startswith(f"{entity}."):
        raise PlanningError(
            f"frequency expression {source_expression!r} is not qualified by {entity}"
        )
    output_field = source_expression.rsplit(".", 1)[-1]
    if not output_field or "@" in output_field:
        raise PlanningError(f"unsupported frequency expression: {source_expression!r}")
    spc = "\n".join(
        [
            "RUNDEF RXDB_VALIDATE",
            f'SELECTION {selection_entity} == "{selection_code}"',
            f"FREQ {source_expression}",
        ]
    )
    return FrequencyQuery(
        entity=entity,
        selection_entity=selection_entity,
        selection_code=selection_code,
        source_expression=source_expression,
        output_field=output_field,
        spc=spc,
    )
