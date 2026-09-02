import pytest

from rxdb_extractor.errors import NormalizationError
from rxdb_extractor.normalizer import normalize_frequency_distribution, normalize_frequency_rows

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


def test_source_variable_mask_can_be_preserved_without_preserving_id_mask():
    rows = [
        {"xpid": 1, "xpid_mask": 0, "p02": None, "p02_mask": 2, "count": 1},
    ]
    out = normalize_frequency_rows(
        rows,
        id_field="xpid",
        dimension_fields=("p02",),
        mask_fields=MASKS,
        preserve_mask_fields=("p02",),
    )
    assert out == [{"xpid": 1, "p02": None, "p02__mask": 2}]


def test_null_parent_identity_dimension_is_fatal_with_mask_diagnostics():
    masks = {"xhid": "xhid_mask", "xvid": "xvid_mask", "h10": "h10_mask"}
    rows = [
        {
            "xhid": 1,
            "xhid_mask": 0,
            "xvid": None,
            "xvid_mask": 0,
            "h10": 2,
            "h10_mask": 0,
            "count": 1,
        }
    ]
    with pytest.raises(NormalizationError, match=r"xvid=None mask=0"):
        normalize_frequency_rows(
            rows,
            id_field="xhid",
            dimension_fields=("xvid", "h10"),
            mask_fields=masks,
            preserve_mask_fields=("h10",),
        )


def test_frequency_distribution_keeps_non_margin_missing_state_distinct():
    rows = [
        {"p02": 1, "p02_mask": 0, "count": 5},
        {"p02": None, "p02_mask": 2, "count": 3},
        {"p02": None, "p02_mask": 1, "count": 8},
    ]
    assert normalize_frequency_distribution(
        rows, dimension_field="p02", mask_field="p02_mask"
    ) == {(1, 0): 5, (None, 2): 3}


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
