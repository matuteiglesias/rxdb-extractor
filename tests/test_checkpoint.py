import pytest

from rxdb_extractor.checkpoint import CheckpointStore, PartitionCheckpoint
from rxdb_extractor.errors import CheckpointError


def good(identity="abc"):
    return PartitionCheckpoint(
        identity, "PERSONA", "RADIO", "061471101", 137, 137, "deadbeef", "pass"
    )


def test_roundtrip_and_match(tmp_path):
    store = CheckpointStore(tmp_path)
    target = store.write("persona-061471101", good())
    assert target.exists()
    assert store.read("persona-061471101") == good()
    assert store.matches("persona-061471101", "abc")
    assert not store.matches("persona-061471101", "other")


def test_incomplete_checkpoint_refused(tmp_path):
    store = CheckpointStore(tmp_path)
    cp = PartitionCheckpoint("abc", "PERSONA", "RADIO", "x", 2, 1, "hash", "pass")
    with pytest.raises(CheckpointError, match="incomplete"):
        store.write("x", cp)


def test_corrupt_checkpoint_is_not_valid(tmp_path):
    store = CheckpointStore(tmp_path)
    store.path_for("x").write_text("{broken")
    assert not store.matches("x", "abc")


def test_simple_names_only(tmp_path):
    store = CheckpointStore(tmp_path)
    with pytest.raises(CheckpointError):
        store.path_for("../escape")
