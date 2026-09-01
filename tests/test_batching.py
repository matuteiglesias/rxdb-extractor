import pytest

from rxdb_extractor.batching import batch_variables
from rxdb_extractor.errors import PlanningError


def test_batch_variables_preserves_order_and_blocks_known_anomaly():
    batches = batch_variables(
        ("P01", "P02", "HNVUA", "EDAD", "P06"), width=2, blocked=frozenset({"HNVUA"})
    )
    assert [b.variables for b in batches] == [("P01", "P02"), ("EDAD", "P06")]


def test_invalid_width_rejected():
    with pytest.raises(PlanningError):
        batch_variables(("P01",), width=0)
