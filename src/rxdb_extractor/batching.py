from dataclasses import dataclass

from .errors import PlanningError


@dataclass(frozen=True)
class VariableBatch:
    index: int
    variables: tuple[str, ...]


def batch_variables(
    variables: tuple[str, ...],
    *,
    width: int,
    blocked: frozenset[str] = frozenset(),
) -> tuple[VariableBatch, ...]:
    if width < 1:
        raise PlanningError("batch width must be >= 1")
    usable = tuple(v for v in variables if v not in blocked)
    return tuple(
        VariableBatch(i // width, usable[i : i + width])
        for i in range(0, len(usable), width)
    )
