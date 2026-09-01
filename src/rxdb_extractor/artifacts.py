from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable, Mapping

import pyarrow as pa
import pyarrow.parquet as pq

from .errors import RxdbError
from .manifest import semantic_hash


class ArtifactError(RxdbError):
    """Raised when a durable output artifact cannot be created safely."""


@dataclass(frozen=True)
class ParquetArtifact:
    path: str
    rows: int
    columns: tuple[str, ...]
    sha256: str
    schema_hash: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def hash_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _schema_fingerprint(schema: pa.Schema) -> str:
    payload = {
        "fields": [
            {"name": field.name, "type": str(field.type), "nullable": field.nullable}
            for field in schema
        ]
    }
    return semantic_hash(payload)


def write_parquet_atomic(
    path: str | Path,
    rows: Iterable[Mapping[str, object]],
    *,
    compression: str = "snappy",
) -> ParquetArtifact:
    """Write a complete Parquet artifact atomically and return its provenance record."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    materialized = [dict(row) for row in rows]
    if not materialized:
        raise ArtifactError("cannot infer Parquet schema from an empty row set")

    first_columns = tuple(materialized[0].keys())
    if any(tuple(row.keys()) != first_columns for row in materialized):
        raise ArtifactError("all rows must have identical deterministic column order")

    table = pa.Table.from_pylist(materialized)
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp:
            temp_path = Path(temp.name)
        pq.write_table(table, temp_path, compression=compression)
        temp_path.replace(destination)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise

    return ParquetArtifact(
        path=str(destination),
        rows=table.num_rows,
        columns=tuple(table.column_names),
        sha256=hash_file(destination),
        schema_hash=_schema_fingerprint(table.schema),
    )


def read_parquet_rows(path: str | Path) -> list[dict[str, object]]:
    return pq.read_table(path).to_pylist()
