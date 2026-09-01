from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Mapping, Sequence

from .capabilities import CapabilitySet
from .errors import RuntimeBridgeError
from .planner import RecordQueryPlan
from .runtime import FrequencyResult


PROTOCOL_VERSION = "1"


@dataclass(frozen=True)
class JsonSubprocessRuntime:
    """Runtime adapter backed by an external JSON-speaking process.

    This is the stable language-neutral boundary for RedEngine integration. The bridge
    implementation may be R/redatamx, a native C/C++ executable, or another binding,
    as long as it implements protocol version 1.
    """

    command: tuple[str, ...]
    timeout_seconds: float = 120.0

    def __init__(self, command: Sequence[str], timeout_seconds: float = 120.0):
        object.__setattr__(self, "command", tuple(command))
        object.__setattr__(self, "timeout_seconds", timeout_seconds)
        if not self.command:
            raise RuntimeBridgeError("bridge command must not be empty")

    def _request(self, action: str, **payload: object) -> Mapping[str, object]:
        request = {
            "protocol_version": PROTOCOL_VERSION,
            "action": action,
            **payload,
        }
        try:
            completed = subprocess.run(
                self.command,
                input=json.dumps(request),
                text=True,
                capture_output=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeBridgeError(f"bridge execution failed: {exc}") from exc

        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            raise RuntimeBridgeError(
                f"bridge exited with status {completed.returncode}: {stderr}"
            )
        try:
            response = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeBridgeError("bridge returned invalid JSON") from exc
        if not isinstance(response, dict):
            raise RuntimeBridgeError("bridge response must be a JSON object")
        if response.get("protocol_version") != PROTOCOL_VERSION:
            raise RuntimeBridgeError("bridge protocol version mismatch")
        if response.get("ok") is not True:
            error = response.get("error", "unknown bridge error")
            raise RuntimeBridgeError(str(error))
        result = response.get("result")
        if not isinstance(result, dict):
            raise RuntimeBridgeError("bridge response is missing object result")
        return result

    def capabilities(self) -> CapabilitySet:
        result = self._request("capabilities")
        try:
            return CapabilitySet(
                redengine_version=str(result["redengine_version"]),
                selection=bool(result["selection"]),
                number=bool(result["number"]),
                inherited_define=bool(result["inherited_define"]),
                freq=bool(result["freq"]),
                cmpcode=bool(result.get("cmpcode", False)),
                table_view=bool(result.get("table_view", False)),
            )
        except KeyError as exc:
            raise RuntimeBridgeError(f"capability response missing {exc.args[0]}") from exc

    def inspect(self, database: str) -> dict[str, object]:
        return dict(self._request("inspect", database=database))

    def execute_record_plan(
        self, database: str, plan: RecordQueryPlan
    ) -> FrequencyResult:
        result = self._request(
            "execute_record_plan",
            database=database,
            plan=plan.to_dict(),
        )
        rows = result.get("rows")
        masks = result.get("mask_fields")
        count_field = result.get("count_field", "count")
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise RuntimeBridgeError("record-plan result rows must be a list of objects")
        if not isinstance(masks, dict) or not all(
            isinstance(key, str) and isinstance(value, str) for key, value in masks.items()
        ):
            raise RuntimeBridgeError("record-plan result mask_fields must map strings")
        if not isinstance(count_field, str):
            raise RuntimeBridgeError("record-plan count_field must be a string")
        return FrequencyResult(
            rows=tuple(rows),
            mask_fields=masks,
            count_field=count_field,
        )
