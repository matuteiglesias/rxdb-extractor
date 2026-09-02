import pytest

from rxdb_extractor.errors import PlanningError
from rxdb_extractor.identity import add_canonical_keys, canonical_entity_key


def test_canonical_key():
    assert canonical_entity_key("061471101", 137) == "061471101:137"


def test_canonical_key_accepts_integer_valued_float_from_r_json():
    assert canonical_entity_key("061471101", 137.0) == "061471101:137"


def test_canonical_key_accepts_integer_code_string_from_redatam_table():
    assert canonical_entity_key("061471101", "137") == "061471101:137"


@pytest.mark.parametrize(
    "seq",
    [
        0,
        -1,
        True,
        1.2,
        "0",
        "-1",
        "1.0",
        "1.2",
        "person one",
        "",
        float("nan"),
        float("inf"),
        -float("inf"),
    ],
)
def test_bad_sequence(seq):
    with pytest.raises(PlanningError):
        canonical_entity_key("061471101", seq)


def test_add_keys_accepts_integer_valued_float_sequences():
    rows = [{"radio": "061", "seq": 1.0}, {"radio": "061", "seq": 2.0}]
    out = add_canonical_keys(
        rows, scope_field="radio", sequence_field="seq", output_field="id"
    )
    assert [x["id"] for x in out] == ["061:1", "061:2"]


def test_add_keys_accepts_integer_code_string_sequences():
    rows = [{"radio": "061", "seq": "1"}, {"radio": "061", "seq": "2"}]
    out = add_canonical_keys(
        rows, scope_field="radio", sequence_field="seq", output_field="id"
    )
    assert [x["id"] for x in out] == ["061:1", "061:2"]


def test_add_keys():
    rows = [{"radio": "061", "seq": 1}, {"radio": "061", "seq": 2}]
    out = add_canonical_keys(
        rows, scope_field="radio", sequence_field="seq", output_field="id"
    )
    assert [x["id"] for x in out] == ["061:1", "061:2"]
