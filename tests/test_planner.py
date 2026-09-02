import pytest

from rxdb_extractor.errors import PlanningError
from rxdb_extractor.planner import build_record_query


def test_person_query_is_deterministic_and_explicit():
    kwargs = dict(
        entity="PERSONA",
        selection_entity="RADIO",
        selection_code="061471101",
        identity_scope="RADIO",
        own_id="XPID",
        prelude_definitions=(
            ("VIVIENDA", "XVID", "NUMBER RADIO"),
            ("HOGAR", "XHID", "NUMBER RADIO"),
        ),
        parent_inheritance=(("XHID", "HOGAR.XHID"), ("XVID", "VIVIENDA.XVID")),
        geography_entities=("PROV", "DPTO", "FRAC", "RADIO"),
        variables=("PERSONA.P02", "PERSONA.EDAD"),
    )
    a = build_record_query(**kwargs)
    b = build_record_query(**kwargs)
    assert a.spc == b.spc
    assert 'SELECTION RADIO == "061471101"' in a.spc
    assert "DEFINE VIVIENDA.XVID AS NUMBER RADIO" in a.spc
    assert "DEFINE HOGAR.XHID AS NUMBER RADIO" in a.spc
    assert "DEFINE HOGAR.XVID AS VIVIENDA.XVID" not in a.spc
    assert a.spc.index("DEFINE HOGAR.XHID") < a.spc.index("DEFINE PERSONA.XHID")
    assert "DEFINE PERSONA.XPID AS NUMBER RADIO" in a.spc
    assert "DEFINE PERSONA.XHID AS HOGAR.XHID" in a.spc
    assert "DEFINE PERSONA.XVID AS VIVIENDA.XVID" in a.spc
    assert "DEFINE PERSONA.XRADIO AS RADIO@cmpcode TYPE STRING SIZE 32" in a.spc
    assert a.spc.endswith(
        "FREQ PERSONA.XPID BY PERSONA.XHID BY PERSONA.XVID BY "
        "PERSONA.XPROV BY PERSONA.XDPTO BY PERSONA.XFRAC BY PERSONA.XRADIO BY "
        "PERSONA.P02 BY PERSONA.EDAD"
    )


def test_cmpcode_can_be_disabled_for_older_runtime():
    plan = build_record_query(
        entity="VIVIENDA",
        selection_entity="RADIO",
        selection_code="x",
        identity_scope="RADIO",
        own_id="XVID",
        geography_entities=("RADIO",),
        use_cmpcode=False,
    )
    assert "@cmpcode" not in plan.spc


def test_duplicate_prelude_definition_is_rejected():
    with pytest.raises(PlanningError):
        build_record_query(
            entity="PERSONA",
            selection_entity="RADIO",
            selection_code="x",
            identity_scope="RADIO",
            own_id="XPID",
            prelude_definitions=(
                ("HOGAR", "XHID", "NUMBER RADIO"),
                ("HOGAR", "XHID", "NUMBER RADIO"),
            ),
        )
