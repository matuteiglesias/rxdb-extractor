import pytest

from rxdb_extractor.errors import SchemaError
from rxdb_extractor.schema import DatabaseSchema, Entity, Variable


def vp_schema():
    return DatabaseSchema.from_entities([
        Entity("CPV2022", selectable=True),
        Entity("PROV", parent="CPV2022", selectable=True),
        Entity("DPTO", parent="PROV", selectable=True),
        Entity("FRAC", parent="DPTO", selectable=True),
        Entity("RADIO", parent="FRAC", selectable=True),
        Entity("VIVIENDA", parent="RADIO", variables=(Variable("V01"),)),
        Entity("HOGAR", parent="VIVIENDA", variables=(Variable("H10"),)),
        Entity(
            "PERSONA",
            parent="HOGAR",
            variables=(Variable("P02", "SEXO"), Variable("HNVUA", "HNVUA")),
        ),
    ])


def test_hierarchy_and_nearest_selectable_ancestor():
    schema = vp_schema()
    assert [x.name for x in schema.ancestors("PERSONA")][-3:] == ["RADIO", "VIVIENDA", "HOGAR"]
    assert schema.nearest_selectable_ancestor("PERSONA").name == "RADIO"
    assert [x.name for x in schema.leaves()] == ["PERSONA"]
    assert [x.name for x in schema.path("RADIO", "PERSONA")] == [
        "RADIO", "VIVIENDA", "HOGAR", "PERSONA"
    ]
    assert [x.name for x in schema.descendants("VIVIENDA")] == ["HOGAR", "PERSONA"]


def test_schema_roundtrip_preserves_entities_variables_and_aliases():
    original = vp_schema()
    restored = DatabaseSchema.from_dict(original.to_dict())
    assert restored.to_dict() == original.to_dict()
    assert restored.entities["PERSONA"].variables[0].alias == "SEXO"
    assert restored.entities["PERSONA"].variables[1].ambiguous_name_alias


def test_invalid_schema_payload_is_rejected():
    with pytest.raises(SchemaError, match="entities list"):
        DatabaseSchema.from_dict({})


def test_missing_parent_rejected():
    with pytest.raises(SchemaError, match="missing parent"):
        DatabaseSchema.from_entities([Entity("PERSONA", parent="HOGAR")])


def test_cycle_rejected():
    with pytest.raises(SchemaError, match="cycle"):
        DatabaseSchema.from_entities([
            Entity("A", parent="B"), Entity("B", parent="A")
        ])
