import json

from rxdb_extractor.artifacts import read_parquet_rows
from rxdb_extractor.dataset import (
    EntityJob,
    ForeignKeyJob,
    KeyProjection,
    SliceSpec,
    run_slice,
)


def _short(expression: str) -> str:
    return expression.rsplit(".", 1)[-1]


_BASE = {
    "VIVIENDA": [
        {"XVID": 1},
        {"XVID": 2},
    ],
    "HOGAR": [
        {"XHID": 1, "XVID": 1},
        {"XHID": 2, "XVID": 2},
    ],
    "PERSONA": [
        {"XPID": 1, "XHID": 1, "XVID": 1},
        {"XPID": 2, "XHID": 1, "XVID": 1},
        {"XPID": 3, "XHID": 2, "XVID": 2},
    ],
}


def _executor(plan):
    output = []
    for source in _BASE[plan.entity]:
        row = {field: source[field] for field in (plan.own_id, *plan.parent_ids)}
        for geo in plan.geography_fields:
            row[geo] = "061471101"
        for variable in plan.variables:
            field = _short(variable)
            row[field] = f"{field}-{source[plan.own_id]}"
        output.append(row)
    return output


def _spec():
    return SliceSpec(
        selection_entity="RADIO",
        selection_code="061471101",
        identity_scope="RADIO",
        scope_field="XRADIO",
        batch_width=1,
        entities=(
            EntityJob(
                entity="VIVIENDA",
                own_id="XVID",
                geography_entities=("RADIO",),
                variables=("VIVIENDA.V01",),
                keys=(KeyProjection("XVID", "vivienda_key"),),
                primary_key="vivienda_key",
            ),
            EntityJob(
                entity="HOGAR",
                own_id="XHID",
                parent_inheritance=(("XVID", "VIVIENDA.XVID"),),
                geography_entities=("RADIO",),
                variables=("HOGAR.H10",),
                keys=(
                    KeyProjection("XHID", "hogar_key"),
                    KeyProjection("XVID", "vivienda_key"),
                ),
                primary_key="hogar_key",
            ),
            EntityJob(
                entity="PERSONA",
                own_id="XPID",
                parent_inheritance=(
                    ("XHID", "HOGAR.XHID"),
                    ("XVID", "VIVIENDA.XVID"),
                ),
                geography_entities=("RADIO",),
                variables=("PERSONA.P02", "PERSONA.EDAD"),
                keys=(
                    KeyProjection("XPID", "persona_key"),
                    KeyProjection("XHID", "hogar_key"),
                    KeyProjection("XVID", "vivienda_key"),
                ),
                primary_key="persona_key",
            ),
        ),
        foreign_keys=(
            ForeignKeyJob("HOGAR", "vivienda_key", "VIVIENDA", "vivienda_key"),
            ForeignKeyJob("PERSONA", "hogar_key", "HOGAR", "hogar_key"),
            ForeignKeyJob("PERSONA", "vivienda_key", "VIVIENDA", "vivienda_key"),
        ),
    )


def test_three_entity_slice_writes_relational_dataset(tmp_path):
    result = run_slice(
        execute=_executor,
        output_dir=tmp_path,
        spec=_spec(),
        provenance={"source": "fixture"},
    )

    assert result.validation.passed
    assert len(result.entities["VIVIENDA"].rows) == 2
    assert len(result.entities["HOGAR"].rows) == 2
    assert len(result.entities["PERSONA"].rows) == 3

    persons = read_parquet_rows(tmp_path / "persona.parquet")
    assert persons[0]["persona_key"] == "061471101:1"
    assert persons[1]["hogar_key"] == "061471101:1"
    assert persons[2]["vivienda_key"] == "061471101:2"

    validation = json.loads((tmp_path / "validation.json").read_text())
    manifest = json.loads((tmp_path / "dataset-manifest.json").read_text())
    assert validation["status"] == "pass"
    assert manifest["validation_status"] == "pass"
    assert manifest["provenance"] == {"source": "fixture"}
    assert len(manifest["semantic_hash"]) == 64
    assert set(manifest["entities"]) == {"VIVIENDA", "HOGAR", "PERSONA"}


def test_slice_validation_fails_on_broken_foreign_key(tmp_path):
    def broken_executor(plan):
        rows = _executor(plan)
        if plan.entity == "PERSONA":
            rows[-1]["XHID"] = 99
        return rows

    result = run_slice(execute=broken_executor, output_dir=tmp_path, spec=_spec())
    assert not result.validation.passed
    assert result.manifest["validation_status"] == "fail"
