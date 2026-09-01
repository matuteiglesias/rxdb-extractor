from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol

from .capabilities import CapabilitySet
from .normalizer import normalize_frequency_rows
from .planner import RecordQueryPlan


@dataclass(frozen=True)
class FrequencyResult:
    rows: tuple[Mapping[str, object], ...]
    mask_fields: Mapping[str, str]
    count_field: str = "count"


class RuntimeAdapter(Protocol):
    """Boundary between extraction logic and a concrete RedEngine binding."""

    def capabilities(self) -> CapabilitySet: ...

    def inspect(self, database: str) -> dict[str, object]: ...

    def execute_record_plan(
        self, database: str, plan: RecordQueryPlan
    ) -> FrequencyResult: ...


def normalized_plan_executor(runtime: RuntimeAdapter, database: str):
    """Adapt a concrete runtime into the normalized executor used by the core."""

    runtime.capabilities().require_record_extraction()

    def execute(plan: RecordQueryPlan) -> list[dict[str, object]]:
        result = runtime.execute_record_plan(database, plan)
        return normalize_frequency_rows(
            result.rows,
            id_field=plan.own_id,
            dimension_fields=plan.dimension_fields[1:],
            mask_fields=result.mask_fields,
            count_field=result.count_field,
        )

    return execute
