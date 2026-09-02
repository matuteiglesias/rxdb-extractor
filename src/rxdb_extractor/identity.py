from collections.abc import Iterable, Mapping
import math
import re

from .errors import PlanningError


_POSITIVE_INTEGER_TEXT = re.compile(r"^[1-9][0-9]*$")


def _normalize_sequence(sequence: object) -> int:
    """Normalize a RedEngine entity sequence without weakening integer semantics.

    RedEngine NUMBER values may travel through R/jsonlite either as numeric vectors
    (``1.0``) or as table-code strings (``"1"``). Accept only exact positive integer
    representations while rejecting fractional values, booleans, labels and invalid
    ranges.
    """
    if isinstance(sequence, bool):
        raise PlanningError(
            f"entity sequence must be an integer >= 1; got {sequence!r} ({type(sequence).__name__})"
        )
    if isinstance(sequence, int):
        value = sequence
    elif isinstance(sequence, float):
        if not math.isfinite(sequence) or not sequence.is_integer():
            raise PlanningError(
                f"entity sequence must be an integer >= 1; got {sequence!r} ({type(sequence).__name__})"
            )
        value = int(sequence)
    elif isinstance(sequence, str):
        text = sequence.strip()
        if not _POSITIVE_INTEGER_TEXT.fullmatch(text):
            raise PlanningError(
                f"entity sequence must be an integer >= 1; got {sequence!r} ({type(sequence).__name__})"
            )
        value = int(text)
    else:
        raise PlanningError(
            f"entity sequence must be an integer >= 1; got {sequence!r} ({type(sequence).__name__})"
        )
    if value < 1:
        raise PlanningError(
            f"entity sequence must be an integer >= 1; got {sequence!r} ({type(sequence).__name__})"
        )
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
            raise PlanningError(
                f"{scope_field} must be a string; got {scope!r} ({type(scope).__name__})"
            )
        record = dict(row)
        try:
            record[output_field] = canonical_entity_key(scope, sequence)
        except PlanningError as exc:
            raise PlanningError(
                f"cannot build {output_field} from {scope_field}={scope!r}, "
                f"{sequence_field}={sequence!r} ({type(sequence).__name__}): {exc}"
            ) from exc
        output.append(record)
    return output
