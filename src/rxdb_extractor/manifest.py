import hashlib
import json
from collections.abc import Mapping


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
