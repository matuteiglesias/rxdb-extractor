from collections.abc import Iterable, Mapping

from .errors import NormalizationError


def normalize_frequency_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    id_field: str,
    dimension_fields: tuple[str, ...],
    mask_fields: Mapping[str, str],
    count_field: str = "count",
    preserve_mask_fields: tuple[str, ...] = (),
) -> list[dict[str, object]]:
    """Keep complete non-margin FREQ cells and enforce record invariants.

    ``mask_fields`` maps every dimension field to the corresponding RedEngine mask
    field. Mask value 1 denotes a margin/total cell in the validated baseline. Other
    source mask states are retained; for stored variables requested through
    ``preserve_mask_fields`` they are emitted as ``<field>__mask`` companion columns.

    Identity and hierarchy dimensions must never be null in a surviving record cell.
    Stored variables may legitimately be null when their non-margin mask represents a
    source missing/structural state.
    """
    required_dimensions = (id_field, *dimension_fields)
    missing_masks = [field for field in required_dimensions if field not in mask_fields]
    if missing_masks:
        raise NormalizationError(
            "missing mask mapping for dimensions: " + ", ".join(missing_masks)
        )
    unknown_preserved = set(preserve_mask_fields) - set(required_dimensions)
    if unknown_preserved:
        raise NormalizationError(
            "cannot preserve masks for non-dimensions: "
            + ", ".join(sorted(unknown_preserved))
        )

    # Stored variables are allowed to carry source-missing values. Every other
    # dimension is structural identity/hierarchy/geography and must be concrete.
    structural_dimensions = tuple(
        field for field in required_dimensions if field not in preserve_mask_fields
    )

    output: list[dict[str, object]] = []
    seen: set[object] = set()
    for raw in rows:
        if any(raw.get(mask_fields[field]) == 1 for field in required_dimensions):
            continue

        missing_structural = [
            field for field in structural_dimensions if raw.get(field) is None
        ]
        if missing_structural:
            details = ", ".join(
                f"{field}={raw.get(field)!r} mask={raw.get(mask_fields[field])!r}"
                for field in structural_dimensions
            )
            raise NormalizationError(
                "complete record cell has null structural dimension(s) "
                + ", ".join(missing_structural)
                + "; "
                + details
            )

        record_id = raw.get(id_field)
        if record_id in seen:
            raise NormalizationError(f"duplicate record ID: {record_id!r}")
        count = raw.get(count_field)
        if count != 1:
            raise NormalizationError(
                f"record cell {record_id!r} has non-unit count {count!r}"
            )
        seen.add(record_id)
        record = {field: raw.get(field) for field in required_dimensions}
        for field in preserve_mask_fields:
            record[f"{field}__mask"] = raw.get(mask_fields[field])
        output.append(record)
    return output


def normalize_frequency_distribution(
    rows: Iterable[Mapping[str, object]],
    *,
    dimension_field: str,
    mask_field: str,
    count_field: str = "count",
) -> dict[tuple[object, object], int]:
    """Normalize a one-dimensional source FREQ for independent reaggregation.

    The key is ``(value, mask)`` so structural/missing states remain distinct. Margin
    cells (mask=1) are excluded, matching the record-emission semantics.
    """
    distribution: dict[tuple[object, object], int] = {}
    for raw in rows:
        mask = raw.get(mask_field)
        if mask == 1:
            continue
        count = raw.get(count_field)
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise NormalizationError(f"invalid frequency count {count!r}")
        key = (raw.get(dimension_field), mask)
        if key in distribution:
            raise NormalizationError(f"duplicate source frequency cell {key!r}")
        distribution[key] = count
    return distribution
