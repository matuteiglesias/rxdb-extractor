from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import tempfile

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


class CheckpointStore:
    """Atomic local checkpoint store keyed by provenance identity."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def path_for(self, name: str) -> Path:
        if not name or "/" in name or "\\" in name or name in {".", ".."}:
            raise CheckpointError("checkpoint name must be a simple path component")
        return self.root / f"{name}.json"

    def write(self, name: str, checkpoint: PartitionCheckpoint) -> Path:
        if not checkpoint.is_complete:
            raise CheckpointError("refusing to persist an incomplete checkpoint")
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.path_for(name)
        payload = canonical_json(asdict(checkpoint)) + "\n"
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
        return (
            checkpoint.is_complete
            and checkpoint.checkpoint_identity == expected_identity
        )
