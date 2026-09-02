from __future__ import annotations

import json
import select
import subprocess
from typing import Mapping, Sequence

from .bridge import PROTOCOL_VERSION
from .capabilities import CapabilitySet
from .errors import RuntimeBridgeError, SchemaError
from .planner import RecordQueryPlan
from .runtime import FrequencyResult, RuntimeInspection
from .schema import DatabaseSchema


class JsonPersistentSubprocessRuntime:
    """Long-lived JSON-lines runtime for expensive RedEngine workloads.

    The regular :class:`JsonSubprocessRuntime` intentionally launches one bridge
    process per request because that is extremely simple and robust.  National
    extraction is different: one RADIO requires many FREQ batches, so repeatedly
    starting R, loading ``redatamx`` and opening the same RXDB becomes dominant.

    This runtime starts the supplied bridge command once, appends ``--serve``, and
    exchanges one JSON request/response per line until ``close()``.  The reference
    R bridge caches opened databases while serving.  Protocol payloads are otherwise
    identical to protocol v1, so extraction logic does not know which transport is
    in use.
    """

    def __init__(self, command: Sequence[str], timeout_seconds: float = 120.0):
        self.command = tuple(command)
        self.timeout_seconds = float(timeout_seconds)
        self._process: subprocess.Popen[str] | None = None
        if not self.command:
            raise RuntimeBridgeError("bridge command must not be empty")
        if self.timeout_seconds <= 0:
            raise RuntimeBridgeError("bridge timeout must be positive")

    def _ensure_process(self) -> subprocess.Popen[str]:
        process = self._process
        if process is not None and process.poll() is None:
            return process
        try:
            process = subprocess.Popen(
                (*self.command, "--serve"),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=None,
                text=True,
                bufsize=1,
            )
        except OSError as exc:
            raise RuntimeBridgeError(f"bridge execution failed: {exc}") from exc
        if process.stdin is None or process.stdout is None:  # pragma: no cover
            process.kill()
            raise RuntimeBridgeError("bridge process is missing stdin/stdout pipes")
        self._process = process
        return process

    @staticmethod
    def _result_from_response(line: str) -> Mapping[str, object]:
        try:
            response = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeBridgeError("bridge returned invalid JSON") from exc
        if not isinstance(response, dict):
            raise RuntimeBridgeError("bridge response must be a JSON object")
        if response.get("protocol_version") != PROTOCOL_VERSION:
            raise RuntimeBridgeError("bridge protocol version mismatch")
        if response.get("ok") is not True:
            raise RuntimeBridgeError(str(response.get("error", "unknown bridge error")))
        result = response.get("result")
        if not isinstance(result, dict):
            raise RuntimeBridgeError("bridge response is missing object result")
        return result

    def _request(self, action: str, **payload: object) -> Mapping[str, object]:
        process = self._ensure_process()
        assert process.stdin is not None
        assert process.stdout is not None
        request = {
            "protocol_version": PROTOCOL_VERSION,
            "action": action,
            **payload,
        }
        try:
            process.stdin.write(json.dumps(request, separators=(",", ":")) + "\n")
            process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            status = process.poll()
            self.close()
            raise RuntimeBridgeError(
                f"persistent bridge write failed (status={status}): {exc}"
            ) from exc

        ready, _, _ = select.select(
            [process.stdout], [], [], self.timeout_seconds
        )
        if not ready:
            self.close(force=True)
            raise RuntimeBridgeError(
                f"persistent bridge timed out after {self.timeout_seconds:g}s"
            )
        line = process.stdout.readline()
        if not line:
            status = process.poll()
            self.close(force=True)
            raise RuntimeBridgeError(
                f"persistent bridge closed stdout unexpectedly (status={status})"
            )
        return self._result_from_response(line)

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
                redatamx_version=(
                    str(result["redatamx_version"])
                    if result.get("redatamx_version") is not None
                    else None
                ),
            )
        except KeyError as exc:
            raise RuntimeBridgeError(f"capability response missing {exc.args[0]}") from exc

    def inspect(self, database: str) -> RuntimeInspection:
        result = self._request("inspect", database=database)
        try:
            schema = DatabaseSchema.from_dict(result)
        except SchemaError as exc:
            raise RuntimeBridgeError(f"invalid inspect schema: {exc}") from exc
        metadata = result.get("metadata", {})
        if not isinstance(metadata, dict):
            raise RuntimeBridgeError("inspect metadata must be an object")
        return RuntimeInspection(schema=schema, metadata=metadata)

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

    def close(self, *, force: bool = False) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        try:
            if process.stdin is not None:
                process.stdin.close()
        except OSError:
            pass
        if force:
            process.kill()
            process.wait(timeout=5)
            return
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:  # pragma: no cover
                process.kill()
                process.wait(timeout=5)

    def __enter__(self) -> "JsonPersistentSubprocessRuntime":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
