from collections.abc import Iterable, Mapping

from .errors import NormalizationError


def normalize_frequency_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    id_field: str,
    dimension_fields: tuple[str, ...],
    mask_fields: Mapping[str, str],
    count_field: str = "count",
) -> list[dict[str, object]]:
    """Keep complete non-margin FREQ cells and enforce record invariants.

    ``mask_fields`` maps every dimension field to the corresponding RedEngine mask
    field. Mask value 1 denotes a margin/total cell in the validated baseline.
    """
    required_dimensions = (id_field, *dimension_fields)
    missing_masks = [field for field in required_dimensions if field not in mask_fields]
    if missing_masks:
        raise NormalizationError(
            "missing mask mapping for dimensions: " + ", ".join(missing_masks)
        )

    output: list[dict[str, object]] = []
    seen: set[object] = set()
    for raw in rows:
        if any(raw.get(mask_fields[field]) == 1 for field in required_dimensions):
            continue
        record_id = raw.get(id_field)
        if record_id is None:
            raise NormalizationError("complete record cell has no own ID")
        if record_id in seen:
            raise NormalizationError(f"duplicate record ID: {record_id!r}")
        count = raw.get(count_field)
        if count != 1:
            raise NormalizationError(
                f"record cell {record_id!r} has non-unit count {count!r}"
            )
        seen.add(record_id)
        output.append({field: raw.get(field) for field in required_dimensions})
    return output
