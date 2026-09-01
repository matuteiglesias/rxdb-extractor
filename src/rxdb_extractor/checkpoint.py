from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Mapping

from .errors import CheckpointError
from .manifest import canonical_json


@dataclass(frozen=True)
class PartitionCheckpoint:
    checkpoint_identity: str
    entity: str
    selection_entity: str
    selection_code: str
    expected_count: int
    actual_count: int
    output_hash: str
    validation_status: str

    @property
    def is_complete(self) -> bool:
        return (
            self.validation_status == "pass"
            and self.expected_count == self.actual_count
            and bool(self.output_hash)
        )


@dataclass(frozen=True)
class SliceCheckpoint:
    checkpoint_identity: str
    selection_entity: str
    selection_code: str
    row_counts: Mapping[str, int]
    output_hashes: Mapping[str, str]
    dataset_manifest_hash: str
    validation_status: str

    @property
    def is_complete(self) -> bool:
        return (
            self.validation_status == "pass"
            and bool(self.row_counts)
            and bool(self.output_hashes)
            and set(self.row_counts) == set(self.output_hashes)
            and all(isinstance(count, int) and count >= 0 for count in self.row_counts.values())
            and all(bool(value) for value in self.output_hashes.values())
            and bool(self.dataset_manifest_hash)
        )


class CheckpointStore:
    """Atomic local checkpoint store keyed by provenance identity."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def path_for(self, name: str) -> Path:
        if not name or "/" in name or "\\" in name or name in {".", ".."}:
            raise CheckpointError("checkpoint name must be a simple path component")
        return self.root / f"{name}.json"

    def _write_payload(self, name: str, payload: str) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.path_for(name)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{name}.", suffix=".tmp", dir=self.root
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, target)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        return target

    def write(self, name: str, checkpoint: PartitionCheckpoint) -> Path:
        if not checkpoint.is_complete:
            raise CheckpointError("refusing to persist an incomplete checkpoint")
        return self._write_payload(name, canonical_json(asdict(checkpoint)) + "\n")

    def read(self, name: str) -> PartitionCheckpoint:
        target = self.path_for(name)
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            return PartitionCheckpoint(**data)
        except (OSError, ValueError, TypeError) as exc:
            raise CheckpointError(f"invalid checkpoint {target}: {exc}") from exc

    def matches(self, name: str, expected_identity: str) -> bool:
        try:
            checkpoint = self.read(name)
        except CheckpointError:
            return False
        return checkpoint.is_complete and checkpoint.checkpoint_identity == expected_identity

    def write_slice(self, name: str, checkpoint: SliceCheckpoint) -> Path:
        if not checkpoint.is_complete:
            raise CheckpointError("refusing to persist an incomplete slice checkpoint")
        return self._write_payload(name, canonical_json(asdict(checkpoint)) + "\n")

    def read_slice(self, name: str) -> SliceCheckpoint:
        target = self.path_for(name)
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            return SliceCheckpoint(**data)
        except (OSError, ValueError, TypeError) as exc:
            raise CheckpointError(f"invalid slice checkpoint {target}: {exc}") from exc

    def matches_slice(self, name: str, expected_identity: str) -> bool:
        try:
            checkpoint = self.read_slice(name)
        except CheckpointError:
            return False
        return checkpoint.is_complete and checkpoint.checkpoint_identity == expected_identity
