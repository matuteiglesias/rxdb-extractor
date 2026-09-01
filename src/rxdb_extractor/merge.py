from collections.abc import Iterable, Mapping

from .errors import NormalizationError


def merge_record_batches(
    batches: Iterable[Iterable[Mapping[str, object]]],
    *,
    key_field: str,
) -> list[dict[str, object]]:
    """Join normalized variable batches by explicit record key.

    Every batch must contain exactly the same key set. Column collisions are only
    accepted when values are identical.
    """
    merged: dict[object, dict[str, object]] | None = None
    for batch_index, batch in enumerate(batches):
        current: dict[object, dict[str, object]] = {}
        for row in batch:
            key = row.get(key_field)
            if key is None:
                raise NormalizationError(f"batch {batch_index} has row without {key_field}")
            if key in current:
                raise NormalizationError(f"batch {batch_index} duplicates key {key!r}")
            current[key] = dict(row)

        if merged is None:
            merged = current
            continue
        if set(current) != set(merged):
            missing = sorted(set(merged) - set(current), key=repr)
            extra = sorted(set(current) - set(merged), key=repr)
            raise NormalizationError(
                f"batch {batch_index} key set mismatch: missing={missing[:5]!r} extra={extra[:5]!r}"
            )
        for key, row in current.items():
            target = merged[key]
            for column, value in row.items():
                if column in target and target[column] != value:
                    raise NormalizationError(
                        f"conflicting column {column!r} for key {key!r}"
                    )
                target[column] = value

    if merged is None:
        return []
    return [merged[key] for key in sorted(merged, key=repr)]
