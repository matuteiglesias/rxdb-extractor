from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

from .orchestration import PartitionRequest


def _request_from_object(value: object) -> PartitionRequest:
    if isinstance(value, str):
        code = value.strip()
        if not code:
            raise ValueError("partition selection code must not be empty")
        return PartitionRequest(code)
    if not isinstance(value, dict):
        raise ValueError("partition entries must be strings or objects")
    code = value.get("selection_code")
    if not isinstance(code, str) or not code.strip():
        raise ValueError("partition object requires non-empty selection_code")
    raw_counts = value.get("expected_counts")
    counts = None
    if raw_counts is not None:
        if not isinstance(raw_counts, dict):
            raise ValueError("expected_counts must be an object")
        counts = {}
        for key, count in raw_counts.items():
            if not isinstance(key, str) or isinstance(count, bool) or not isinstance(count, int):
                raise ValueError("expected_counts must map entity names to integers")
            if count < 0:
                raise ValueError("expected_counts cannot be negative")
            counts[key.upper()] = count
    return PartitionRequest(code.strip(), counts)


def _deduplicate(requests: Iterable[PartitionRequest]) -> tuple[PartitionRequest, ...]:
    output: list[PartitionRequest] = []
    seen: set[str] = set()
    for request in requests:
        if request.selection_code in seen:
            raise ValueError(f"duplicate partition selection code: {request.selection_code}")
        seen.add(request.selection_code)
        output.append(request)
    if not output:
        raise ValueError("partition file contains no requests")
    return tuple(output)


def _csv_requests(path: Path) -> tuple[PartitionRequest, ...]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        sample = stream.read(8192)
        stream.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(stream, dialect=dialect)
        if not reader.fieldnames or "selection_code" not in reader.fieldnames:
            raise ValueError("partition CSV requires selection_code column")
        requests: list[PartitionRequest] = []
        for row in reader:
            code = (row.get("selection_code") or "").strip()
            if not code:
                continue
            counts: dict[str, int] = {}
            for entity in ("VIVIENDA", "HOGAR", "PERSONA"):
                candidates = (entity, entity.lower(), f"{entity.lower()}_count")
                raw = next((row.get(name) for name in candidates if row.get(name) not in {None, ""}), None)
                if raw is not None:
                    counts[entity] = int(raw)
            requests.append(PartitionRequest(code, counts or None))
    return _deduplicate(requests)


def load_partition_requests(path: str | Path) -> tuple[PartitionRequest, ...]:
    """Read partition requests from JSON, CSV/TSV, or newline text.

    JSON may be a list of selection-code strings, a list of objects containing
    ``selection_code`` / optional ``expected_counts``, or an object with a
    ``partitions`` list.  CSV/TSV requires ``selection_code`` and may carry
    VIVIENDA/HOGAR/PERSONA expected counts.  Plain text uses one code per line;
    blank lines and ``#`` comments are ignored.
    """
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise ValueError(f"partition file does not exist: {source}")
    suffix = source.suffix.lower()
    if suffix == ".json":
        payload = json.loads(source.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            payload = payload.get("partitions")
        if not isinstance(payload, list):
            raise ValueError("partition JSON must be a list or contain partitions list")
        return _deduplicate(_request_from_object(item) for item in payload)
    if suffix in {".csv", ".tsv"}:
        return _csv_requests(source)

    requests = []
    for line in source.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        requests.append(PartitionRequest(value))
    return _deduplicate(requests)
