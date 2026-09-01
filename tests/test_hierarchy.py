from rxdb_extractor.hierarchy import build_hierarchy_projection
from rxdb_extractor.schema import DatabaseSchema, Entity


def _schema():
    return DatabaseSchema.from_entities(
        [
            Entity("CPV2022"),
            Entity("RADIO", parent="CPV2022", selectable=True),
            Entity("VIVIENDA", parent="RADIO"),
            Entity("HOGAR", parent="VIVIENDA"),
            Entity("PERSONA", parent="HOGAR"),
        ]
    )


def test_hogar_projection_defines_vivienda_then_inherits_it():
    projection = build_hierarchy_projection(
        _schema(),
        target_entity="HOGAR",
        identity_scope="RADIO",
        id_fields={"VIVIENDA": "XVID", "HOGAR": "XHID", "PERSONA": "XPID"},
    )
    assert projection.prelude_definitions == (
        ("VIVIENDA", "XVID", "NUMBER RADIO"),
    )
    assert projection.parent_inheritance == (("XVID", "VIVIENDA.XVID"),)


def test_person_projection_propagates_all_parent_ids_through_hogar():
    projection = build_hierarchy_projection(
        _schema(),
        target_entity="PERSONA",
        identity_scope="RADIO",
        id_fields={"VIVIENDA": "XVID", "HOGAR": "XHID", "PERSONA": "XPID"},
    )
    assert projection.prelude_definitions == (
        ("VIVIENDA", "XVID", "NUMBER RADIO"),
        ("HOGAR", "XHID", "NUMBER RADIO"),
        ("HOGAR", "XVID", "VIVIENDA.XVID"),
    )
    assert projection.parent_inheritance == (
        ("XVID", "HOGAR.XVID"),
        ("XHID", "HOGAR.XHID"),
    )
