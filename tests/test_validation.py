from rxdb_extractor.validation import validate_count, validate_foreign_key, validate_unique_key


def test_count_validation():
    rows = [{"id": 1}, {"id": 2}]
    passed = validate_count(rows, entity="PERSONA", expected=2)
    failed = validate_count(rows, entity="PERSONA", expected=3)
    assert passed.passed and passed.observed == passed.expected == 2
    assert not failed.passed and failed.detail == "delta=-1"


def test_unique_key_pass_and_fail():
    assert validate_unique_key([{"id": 1}, {"id": 2}], "id").passed
    assert not validate_unique_key([{"id": 1}, {"id": 1}], "id").passed


def test_foreign_key():
    parents = [{"vid": "r:1"}, {"vid": "r:2"}]
    children = [{"vid": "r:1"}, {"vid": "r:2"}]
    assert validate_foreign_key(children, child_field="vid", parent_rows=parents, parent_key="vid").passed
    assert not validate_foreign_key([{"vid": "r:3"}], child_field="vid", parent_rows=parents, parent_key="vid").passed
