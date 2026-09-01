import pytest

from rxdb_extractor.errors import NormalizationError
from rxdb_extractor.normalizer import normalize_frequency_rows

MASKS = {"xpid": "xpid_mask", "p02": "p02_mask"}


def test_margins_removed_and_complete_cells_kept():
    rows = [
        {"xpid": 1, "xpid_mask": 0, "p02": 2, "p02_mask": 0, "count": 1},
        {"xpid": 2, "xpid_mask": 0, "p02": 1, "p02_mask": 0, "count": 1},
        {"xpid": None, "xpid_mask": 1, "p02": 1, "p02_mask": 0, "count": 2},
    ]
    out = normalize_frequency_rows(
        rows, id_field="xpid", dimension_fields=("p02",), mask_fields=MASKS
    )
    assert out == [{"xpid": 1, "p02": 2}, {"xpid": 2, "p02": 1}]


def test_duplicate_id_is_fatal():
    rows = [
        {"xpid": 1, "xpid_mask": 0, "p02": 1, "p02_mask": 0, "count": 1},
        {"xpid": 1, "xpid_mask": 0, "p02": 2, "p02_mask": 0, "count": 1},
    ]
    with pytest.raises(NormalizationError, match="duplicate"):
        normalize_frequency_rows(rows, id_field="xpid", dimension_fields=("p02",), mask_fields=MASKS)


def test_non_unit_count_is_fatal():
    rows = [{"xpid": 1, "xpid_mask": 0, "p02": 1, "p02_mask": 0, "count": 2}]
    with pytest.raises(NormalizationError, match="non-unit"):
        normalize_frequency_rows(rows, id_field="xpid", dimension_fields=("p02",), mask_fields=MASKS)
