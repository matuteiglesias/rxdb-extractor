import json

import pytest

from rxdb_extractor.errors import PlanningError
from rxdb_extractor.profile import compile_profile, load_profile
from rxdb_extractor.schema import DatabaseSchema, Entity, Variable


_PARENT_MAP = {
    "CPV2022": None,
    "PROV": "CPV2022",
    "DPTO": "PROV",
    "FRAC": "DPTO",
    "RADIO": "FRAC",
    "VIVIENDA": "RADIO",
    "HOGAR": "VIVIENDA",
    "PERSONA": "HOGAR",
}


def _schema():
    return DatabaseSchema.from_entities(
        [
            Entity("CPV2022"),
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
        ]
    )


def _flat_schema():
    entities = []
    for entity in _schema().entities.values():
        entities.append(
            Entity(
                entity.name,
                selectable=entity.selectable,
                variables=entity.variables,
            )
        )
    return DatabaseSchema.from_entities(entities)


def _profile():
    return {
        "selection_entity": "RADIO",
        "identity_scope": "RADIO",
        "scope_field": "XRADIO",
        "geography_entities": ["PROV", "DPTO", "FRAC", "RADIO"],
        "id_fields": {"VIVIENDA": "XVID", "HOGAR": "XHID", "PERSONA": "XPID"},
        "entities": [
            {
                "entity": "VIVIENDA",
                "own_id": "XVID",
                "variable_policy": "all-stored",
                "blocked_variables": [],
                "keys": [{"sequence_field": "XVID", "output_field": "vivienda_key"}],
                "primary_key": "vivienda_key",
            },
            {
                "entity": "HOGAR",
                "own_id": "XHID",
                "variable_policy": "all-stored",
                "blocked_variables": [],
                "keys": [
                    {"sequence_field": "XHID", "output_field": "hogar_key"},
                    {"sequence_field": "XVID", "output_field": "vivienda_key"},
                ],
                "primary_key": "hogar_key",
            },
            {
                "entity": "PERSONA",
                "own_id": "XPID",
                "variable_policy": "all-stored",
                "blocked_variables": ["PERSONA.HNVUA"],
                "keys": [
                    {"sequence_field": "XPID", "output_field": "persona_key"},
                    {"sequence_field": "XHID", "output_field": "hogar_key"},
                    {"sequence_field": "XVID", "output_field": "vivienda_key"},
                ],
                "primary_key": "persona_key",
            },
        ],
        "foreign_keys": [
            {"child_entity": "HOGAR", "child_field": "vivienda_key", "parent_entity": "VIVIENDA", "parent_field": "vivienda_key"},
            {"child_entity": "PERSONA", "child_field": "hogar_key", "parent_entity": "HOGAR", "parent_field": "hogar_key"},
            {"child_entity": "PERSONA", "child_field": "vivienda_key", "parent_entity": "VIVIENDA", "parent_field": "vivienda_key"},
        ],
    }


def test_compile_profile_derives_variables_and_native_hierarchy():
    spec = compile_profile(_schema(), _profile(), selection_code="061471101", batch_width=3)
    assert spec.selection_entity == "RADIO"
    assert spec.batch_width == 3
    persona = next(job for job in spec.entities if job.entity == "PERSONA")
    assert persona.variables == ("PERSONA.P02", "PERSONA.HNVUA")
    assert persona.blocked_variables == frozenset({"PERSONA.HNVUA"})
    assert persona.prelude_definitions == (
        ("VIVIENDA", "XVID", "NUMBER RADIO"),
        ("HOGAR", "XHID", "NUMBER RADIO"),
        ("HOGAR", "XVID", "VIVIENDA.XVID"),
    )
    assert set(persona.parent_inheritance) == {
        ("XVID", "HOGAR.XVID"),
        ("XHID", "HOGAR.XHID"),
    }
    assert len(spec.foreign_keys) == 3


def test_profile_parent_map_can_augment_flat_runtime_metadata():
    profile = _profile()
    profile["parent_map"] = _PARENT_MAP
    spec = compile_profile(_flat_schema(), profile, selection_code="061471101")
    persona = next(job for job in spec.entities if job.entity == "PERSONA")
    assert persona.prelude_definitions[-1] == ("HOGAR", "XVID", "VIVIENDA.XVID")


def test_profile_parent_map_cannot_override_runtime_parent():
    profile = _profile()
    profile["parent_map"] = dict(_PARENT_MAP, HOGAR="RADIO")
    with pytest.raises(PlanningError, match="conflicts for HOGAR"):
        compile_profile(_schema(), profile, selection_code="061471101")


def test_ambiguous_variable_must_be_explicitly_blocked():
    profile = _profile()
    profile["entities"][2]["blocked_variables"] = []
    with pytest.raises(PlanningError, match="must be explicitly blocked"):
        compile_profile(_schema(), profile, selection_code="061471101")


def test_selection_entity_must_be_selectable():
    profile = _profile()
    profile["selection_entity"] = "VIVIENDA"
    with pytest.raises(PlanningError, match="not selectable"):
        compile_profile(_schema(), profile, selection_code="x")


def test_load_profile_requires_json_object(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(_profile()), encoding="utf-8")
    assert load_profile(path)["selection_entity"] == "RADIO"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(PlanningError, match="JSON object"):
        load_profile(path)
