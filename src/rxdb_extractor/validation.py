from dataclasses import dataclass
from collections.abc import Iterable, Mapping


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    observed: int | None = None
    expected: int | None = None
    detail: str | None = None


def validate_count(
    rows: Iterable[Mapping[str, object]],
    *,
    entity: str,
    expected: int,
) -> CheckResult:
    observed = sum(1 for _ in rows)
    return CheckResult(
        name=f"count:{entity}",
        passed=observed == expected,
        observed=observed,
        expected=expected,
        detail=None if observed == expected else f"delta={observed - expected}",
    )


def validate_unique_key(rows: Iterable[Mapping[str, object]], key: str) -> CheckResult:
    values = [row.get(key) for row in rows]
    missing = sum(value is None for value in values)
    duplicates = len(values) - len(set(values))
    passed = missing == 0 and duplicates == 0
    return CheckResult(
        name=f"unique:{key}",
        passed=passed,
        observed=len(values),
        expected=len(set(values)) if not missing else None,
        detail=f"missing={missing} duplicates={duplicates}",
    )


def validate_foreign_key(
    child_rows: Iterable[Mapping[str, object]],
    *,
    child_field: str,
    parent_rows: Iterable[Mapping[str, object]],
    parent_key: str,
) -> CheckResult:
    parent_values = {row.get(parent_key) for row in parent_rows}
    child_values = [row.get(child_field) for row in child_rows]
    invalid = [value for value in child_values if value is None or value not in parent_values]
    return CheckResult(
        name=f"fk:{child_field}->{parent_key}",
        passed=not invalid,
        observed=len(child_values) - len(invalid),
        expected=len(child_values),
        detail=f"invalid={len(invalid)}",
    )
