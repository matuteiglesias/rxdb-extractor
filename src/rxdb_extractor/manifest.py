import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from tempfile import NamedTemporaryFile


def canonical_json(value: Mapping[str, object]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def semantic_hash(value: Mapping[str, object]) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def checkpoint_identity(
    *,
    source_hash: str,
    schema_hash: str,
    query_hash: str,
    runtime_hash: str,
) -> str:
    return semantic_hash(
        {
            "source_hash": source_hash,
            "schema_hash": schema_hash,
            "query_hash": query_hash,
            "runtime_hash": runtime_hash,
        }
    )


def write_json_atomic(path: str | Path, value: Mapping[str, object]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp:
            temp.write(payload)
            temp_path = Path(temp.name)
        temp_path.replace(destination)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise
