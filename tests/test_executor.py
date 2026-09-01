import pytest

from rxdb_extractor.artifacts import read_parquet_rows
from rxdb_extractor.errors import NormalizationError
from rxdb_extractor.executor import extract_entity_batches, extract_entity_to_parquet


def _field(expression: str) -> str:
    return expression.rsplit(".", 1)[-1]


def _fixture_executor(plan):
    rows = []
    for seq in (1, 2):
        row = {plan.own_id: seq}
        for parent in plan.parent_ids:
            row[parent] = 10 + seq
        for geo in plan.geography_fields:
            row[geo] = "061471101"
        for expression in plan.variables:
            row[_field(expression)] = f"{_field(expression)}-{seq}"
        rows.append(row)
    return rows


def test_batched_executor_merges_by_explicit_id():
    result = extract_entity_batches(
        execute=_fixture_executor,
        entity="PERSONA",
        selection_entity="RADIO",
        selection_code="061471101",
        identity_scope="RADIO",
        own_id="XPID",
        parent_inheritance=(("XHID", "HOGAR.XHID"),),
        geography_entities=("RADIO",),
        variables=("PERSONA.P01", "PERSONA.P02", "PERSONA.EDAD"),
        batch_width=2,
    )
    assert len(result.plans) == 2
    assert [row["XPID"] for row in result.rows] == [1, 2]
    assert result.rows[0]["P01"] == "P01-1"
    assert result.rows[0]["P02"] == "P02-1"
    assert result.rows[0]["EDAD"] == "EDAD-1"
    assert result.rows[0]["XHID"] == 11
    assert result.rows[0]["XRADIO"] == "061471101"


def test_batched_executor_surfaces_blocked_variables():
    result = extract_entity_batches(
        execute=_fixture_executor,
        entity="PERSONA",
        selection_entity="RADIO",
        selection_code="061471101",
        identity_scope="RADIO",
        own_id="XPID",
        variables=("PERSONA.P02", "PERSONA.HNVUA"),
        batch_width=5,
        blocked_variables=frozenset({"PERSONA.HNVUA"}),
        use_cmpcode=False,
    )
    assert result.blocked_variables == ("PERSONA.HNVUA",)
    assert "HNVUA" not in result.rows[0]


def test_batched_executor_rejects_key_set_mismatch():
    calls = 0

    def bad_executor(plan):
        nonlocal calls
        calls += 1
        rows = _fixture_executor(plan)
        return rows if calls == 1 else rows[:1]

    with pytest.raises(NormalizationError):
        extract_entity_batches(
            execute=bad_executor,
            entity="PERSONA",
            selection_entity="RADIO",
            selection_code="061471101",
            identity_scope="RADIO",
            own_id="XPID",
            variables=("PERSONA.P01", "PERSONA.P02"),
            batch_width=1,
            use_cmpcode=False,
        )


def test_executor_can_persist_parquet(tmp_path):
    result = extract_entity_to_parquet(
        tmp_path / "persona.parquet",
        execute=_fixture_executor,
        entity="PERSONA",
        selection_entity="RADIO",
        selection_code="061471101",
        identity_scope="RADIO",
        own_id="XPID",
        variables=("PERSONA.P02",),
        batch_width=1,
        use_cmpcode=False,
    )
    assert result.artifact.rows == 2
    assert read_parquet_rows(tmp_path / "persona.parquet") == list(result.extraction.rows)
