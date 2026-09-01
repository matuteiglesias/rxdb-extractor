import pytest

from rxdb_extractor.errors import NormalizationError
from rxdb_extractor.merge import merge_record_batches


def test_explicit_key_merge():
    out = merge_record_batches(
        [
            [{"id": 2, "a": "y"}, {"id": 1, "a": "x"}],
            [{"id": 1, "b": 10}, {"id": 2, "b": 20}],
        ],
        key_field="id",
    )
    assert out == [{"id": 1, "a": "x", "b": 10}, {"id": 2, "a": "y", "b": 20}]


def test_key_set_mismatch_fails_closed():
    with pytest.raises(NormalizationError, match="key set mismatch"):
        merge_record_batches(
            [[{"id": 1}], [{"id": 2}]], key_field="id"
        )


def test_conflicting_repeated_control_fails_closed():
    with pytest.raises(NormalizationError, match="conflicting"):
        merge_record_batches(
            [[{"id": 1, "control": 2}], [{"id": 1, "control": 3}]], key_field="id"
        )
