import pytest

from rxdb_extractor.errors import SchemaError
from rxdb_extractor.schema import DatabaseSchema, Entity


def vp_schema():
    return DatabaseSchema.from_entities([
        Entity("CPV2022", selectable=True),
        Entity("PROV", parent="CPV2022", selectable=True),
        Entity("DPTO", parent="PROV", selectable=True),
        Entity("FRAC", parent="DPTO", selectable=True),
        Entity("RADIO", parent="FRAC", selectable=True),
        Entity("VIVIENDA", parent="RADIO"),
        Entity("HOGAR", parent="VIVIENDA"),
        Entity("PERSONA", parent="HOGAR"),
    ])


def test_hierarchy_and_nearest_selectable_ancestor():
    schema = vp_schema()
    assert [x.name for x in schema.ancestors("PERSONA")][-3:] == ["RADIO", "VIVIENDA", "HOGAR"]
    assert schema.nearest_selectable_ancestor("PERSONA").name == "RADIO"
    assert [x.name for x in schema.leaves()] == ["PERSONA"]


def test_missing_parent_rejected():
    with pytest.raises(SchemaError, match="missing parent"):
        DatabaseSchema.from_entities([Entity("PERSONA", parent="HOGAR")])


def test_cycle_rejected():
    with pytest.raises(SchemaError, match="cycle"):
        DatabaseSchema.from_entities([
            Entity("A", parent="B"), Entity("B", parent="A")
        ])
