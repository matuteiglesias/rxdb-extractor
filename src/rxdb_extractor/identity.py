from collections.abc import Iterable, Mapping
import math

from .errors import PlanningError


def _normalize_sequence(sequence: object) -> int:
    """Normalize a RedEngine entity sequence without weakening integer semantics.

    RedEngine NUMBER values travel through R/jsonlite as numeric vectors, so an exact
    sequence may arrive in Python as ``1.0`` rather than ``1``. Accept integer-valued
    finite floats while rejecting fractional values, booleans, strings and invalid
    ranges.
    """
    if isinstance(sequence, bool):
        raise PlanningError("entity sequence must be an integer >= 1")
    if isinstance(sequence, int):
        value = sequence
    elif isinstance(sequence, float):
        if not math.isfinite(sequence) or not sequence.is_integer():
            raise PlanningError("entity sequence must be an integer >= 1")
        value = int(sequence)
    else:
        raise PlanningError("entity sequence must be an integer >= 1")
    if value < 1:
        raise PlanningError("entity sequence must be an integer >= 1")
    return value


def canonical_entity_key(scope_cmpcode: str, sequence: object) -> str:
    """Build a deterministic composite key from source geography and sequence."""
    if not scope_cmpcode:
        raise PlanningError("scope cmpcode is required")
    value = _normalize_sequence(sequence)
    return f"{scope_cmpcode}:{value}"


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
        record[output_field] = canonical_entity_key(scope, sequence)
        output.append(record)
    return output
