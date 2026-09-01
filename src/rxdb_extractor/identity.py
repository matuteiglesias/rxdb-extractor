from collections.abc import Iterable, Mapping

from .errors import PlanningError


def canonical_entity_key(scope_cmpcode: str, sequence: int) -> str:
    """Build a deterministic composite key from source geography and sequence."""
    if not scope_cmpcode:
        raise PlanningError("scope cmpcode is required")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise PlanningError("entity sequence must be an integer >= 1")
    return f"{scope_cmpcode}:{sequence}"


def add_canonical_keys(
    rows: Iterable[Mapping[str, object]],
    *,
    scope_field: str,
    sequence_field: str,
    output_field: str,
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for row in rows:
        scope = row.get(scope_field)
        sequence = row.get(sequence_field)
        if not isinstance(scope, str):
            raise PlanningError(f"{scope_field} must be a string")
        record = dict(row)
        record[output_field] = canonical_entity_key(scope, sequence)  # type: ignore[arg-type]
        output.append(record)
    return output
