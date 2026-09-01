import pyarrow.parquet as pq
import pytest

from rxdb_extractor.artifacts import ArtifactError, read_parquet_rows, write_parquet_atomic


def test_write_parquet_atomic_roundtrip(tmp_path):
    path = tmp_path / "persona.parquet"
    rows = [
        {"persona_key": "061:1", "edad": 30},
        {"persona_key": "061:2", "edad": 40},
    ]
    artifact = write_parquet_atomic(path, rows)

    assert artifact.rows == 2
    assert artifact.columns == ("persona_key", "edad")
    assert len(artifact.sha256) == 64
    assert len(artifact.schema_hash) == 64
    assert read_parquet_rows(path) == rows
    assert pq.read_table(path).num_rows == 2
    assert not list(tmp_path.glob("*.tmp"))


def test_write_parquet_rejects_empty_rows(tmp_path):
    with pytest.raises(ArtifactError):
        write_parquet_atomic(tmp_path / "empty.parquet", [])


def test_write_parquet_rejects_inconsistent_column_order(tmp_path):
    rows = [{"a": 1, "b": 2}, {"b": 3, "a": 4}]
    with pytest.raises(ArtifactError):
        write_parquet_atomic(tmp_path / "bad.parquet", rows)
