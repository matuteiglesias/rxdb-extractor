import pytest

from rxdb_extractor.errors import PlanningError
from rxdb_extractor.identity import add_canonical_keys, canonical_entity_key


def test_canonical_key():
    assert canonical_entity_key("061471101", 137) == "061471101:137"


@pytest.mark.parametrize("seq", [0, -1, True, 1.2, "1"])
def test_bad_sequence(seq):
    with pytest.raises(PlanningError):
        canonical_entity_key("061471101", seq)


def test_add_keys():
    rows = [{"radio": "061", "seq": 1}, {"radio": "061", "seq": 2}]
    out = add_canonical_keys(
        rows, scope_field="radio", sequence_field="seq", output_field="id"
    )
    assert [x["id"] for x in out] == ["061:1", "061:2"]
