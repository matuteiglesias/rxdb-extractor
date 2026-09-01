import json

import pytest

from rxdb_extractor.dataset import EntityJob, ForeignKeyJob, KeyProjection, SliceSpec
from rxdb_extractor.errors import ValidationError
from rxdb_extractor.orchestration import (
    PartitionRequest,
    RunProvenance,
    checkpoint_name,
    partition_output_dir,
    run_partitions,
)


def _spec():
    return SliceSpec(
        selection_entity="RADIO",
        selection_code="placeholder",
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
                prelude_definitions=(("VIVIENDA", "XVID", "NUMBER RADIO"),),
                parent_inheritance=(("XVID", "VIVIENDA.XVID"),),
                geography_entities=("RADIO",),
                variables=("HOGAR.H10",),
                keys=(
                    KeyProjection("XHID", "hogar_key"),
                    KeyProjection("XVID", "vivienda_key"),
                ),
                primary_key="hogar_key",
            ),
        ),
        foreign_keys=(
            ForeignKeyJob("HOGAR", "vivienda_key", "VIVIENDA", "vivienda_key"),
        ),
    )


def _provenance(source_hash="source-a"):
    return RunProvenance(
        source_hash=source_hash,
        schema_hash="schema-a",
        profile_hash="profile-a",
        runtime_hash="runtime-a",
    )


def _executor(counter):
    def execute(plan):
        counter["calls"] += 1
        if plan.entity == "VIVIENDA":
            base = [{"XVID": 1}, {"XVID": 2}]
        else:
            base = [{"XHID": 1, "XVID": 1}, {"XHID": 2, "XVID": 2}]
        rows = []
        for source in base:
            row = {field: source[field] for field in (plan.own_id, *plan.parent_ids)}
            for geo in plan.geography_fields:
                row[geo] = plan.selection_code
            for variable, field in zip(plan.variables, plan.variable_fields):
                row[field] = f"{field}-{source[plan.own_id]}"
            rows.append(row)
        return rows
    return execute


def test_partition_runner_checkpoints_and_resumes(tmp_path):
    counter = {"calls": 0}
    request = PartitionRequest("061471101", {"VIVIENDA": 2, "HOGAR": 2})
    first = run_partitions(
        execute=_executor(counter),
        output_root=tmp_path,
        base_spec=_spec(),
        requests=[request],
        provenance=_provenance(),
    )
    calls_after_first = counter["calls"]
    assert first[0].status == "completed"
    assert calls_after_first > 0

    second = run_partitions(
        execute=_executor(counter),
        output_root=tmp_path,
        base_spec=_spec(),
        requests=[request],
        provenance=_provenance(),
    )
    assert second[0].status == "skipped"
    assert counter["calls"] == calls_after_first


def test_changed_provenance_invalidates_checkpoint(tmp_path):
    counter = {"calls": 0}
    request = PartitionRequest("061471101", {"VIVIENDA": 2, "HOGAR": 2})
    run_partitions(
        execute=_executor(counter), output_root=tmp_path, base_spec=_spec(),
        requests=[request], provenance=_provenance("source-a")
    )
    first_calls = counter["calls"]
    outcome = run_partitions(
        execute=_executor(counter), output_root=tmp_path, base_spec=_spec(),
        requests=[request], provenance=_provenance("source-b")
    )
    assert outcome[0].status == "completed"
    assert counter["calls"] > first_calls


def test_corrupted_artifact_invalidates_checkpoint(tmp_path):
    counter = {"calls": 0}
    request = PartitionRequest("061471101", {"VIVIENDA": 2, "HOGAR": 2})
    run_partitions(
        execute=_executor(counter), output_root=tmp_path, base_spec=_spec(),
        requests=[request], provenance=_provenance()
    )
    first_calls = counter["calls"]
    output_dir = partition_output_dir(tmp_path, "RADIO", "061471101")
    (output_dir / "hogar.parquet").write_bytes(b"corrupt")

    outcome = run_partitions(
        execute=_executor(counter), output_root=tmp_path, base_spec=_spec(),
        requests=[request], provenance=_provenance()
    )
    assert outcome[0].status == "completed"
    assert counter["calls"] > first_calls


def test_invalid_count_never_leaves_success_checkpoint(tmp_path):
    counter = {"calls": 0}
    request = PartitionRequest("061471101", {"VIVIENDA": 999, "HOGAR": 2})
    with pytest.raises(ValidationError, match="count:VIVIENDA"):
        run_partitions(
            execute=_executor(counter), output_root=tmp_path, base_spec=_spec(),
            requests=[request], provenance=_provenance()
        )
    checkpoint = tmp_path / ".checkpoints" / f"{checkpoint_name('RADIO', '061471101')}.json"
    assert not checkpoint.exists()
    validation = json.loads(
        (partition_output_dir(tmp_path, "RADIO", "061471101") / "validation.json").read_text()
    )
    assert validation["status"] == "fail"
