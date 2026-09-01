import sys

import pytest

from rxdb_extractor.bridge import JsonSubprocessRuntime
from rxdb_extractor.errors import RuntimeBridgeError
from rxdb_extractor.planner import build_record_query
from rxdb_extractor.runtime import normalized_plan_executor


def _write_bridge(path):
    path.write_text(
        r'''import json, sys
req = json.load(sys.stdin)
action = req["action"]
if action == "capabilities":
    result = {
        "redengine_version": "1.3.0-final",
        "selection": True,
        "number": True,
        "inherited_define": True,
        "freq": True,
        "cmpcode": True,
        "table_view": False,
    }
elif action == "inspect":
    result = {
        "entities": [
            {"name":"RADIO","alias":None,"parent":None,"selectable":True,"variables":[]},
            {"name":"PERSONA","alias":None,"parent":"RADIO","selectable":False,
             "variables":[{"name":"P02","alias":"SEXO","label":"Sex"}]},
        ],
        "metadata": {"database": req["database"]},
    }
elif action == "execute_record_plan":
    plan = req["plan"]
    rows = []
    masks = {}
    for field in plan["dimension_fields"]:
        masks[field] = field + "__mask"
    for seq in (1, 2):
        row = {}
        for field in plan["dimension_fields"]:
            if field == plan["own_id"]:
                value = seq
            elif field == "XRADIO":
                value = "061471101"
            elif field.startswith("X"):
                value = 10 + seq
            else:
                value = field + "-" + str(seq)
            row[field] = value
            row[masks[field]] = 0
        row["count"] = 1
        rows.append(row)
    result = {"rows": rows, "mask_fields": masks, "count_field": "count"}
else:
    print(json.dumps({"protocol_version": "1", "ok": False, "error": "bad action"}))
    raise SystemExit(0)
print(json.dumps({"protocol_version": "1", "ok": True, "result": result}))
''',
        encoding="utf-8",
    )


def test_json_subprocess_runtime_capabilities_inspect_and_records(tmp_path):
    bridge = tmp_path / "bridge.py"
    _write_bridge(bridge)
    runtime = JsonSubprocessRuntime([sys.executable, str(bridge)])

    capabilities = runtime.capabilities()
    assert capabilities.redengine_version == "1.3.0-final"
    assert capabilities.cmpcode
    assert not capabilities.table_view
    inspection = runtime.inspect("demo.rxdb")
    assert inspection.metadata["database"] == "demo.rxdb"
    assert inspection.schema.entities["PERSONA"].parent == "RADIO"
    assert inspection.schema.entities["PERSONA"].variables[0].alias == "SEXO"

    plan = build_record_query(
        entity="PERSONA",
        selection_entity="RADIO",
        selection_code="061471101",
        identity_scope="RADIO",
        own_id="XPID",
        geography_entities=("RADIO",),
        variables=("PERSONA.P02",),
    )
    execute = normalized_plan_executor(runtime, "demo.rxdb")
    rows = execute(plan)
    assert rows == [
        {"XPID": 1, "XRADIO": "061471101", "P02": "P02-1"},
        {"XPID": 2, "XRADIO": "061471101", "P02": "P02-2"},
    ]


def test_json_subprocess_runtime_rejects_invalid_json(tmp_path):
    bridge = tmp_path / "bad.py"
    bridge.write_text('print("not json")\n', encoding="utf-8")
    runtime = JsonSubprocessRuntime([sys.executable, str(bridge)])
    with pytest.raises(RuntimeBridgeError, match="invalid JSON"):
        runtime.capabilities()


def test_json_subprocess_runtime_rejects_protocol_mismatch(tmp_path):
    bridge = tmp_path / "bad_version.py"
    bridge.write_text(
        'import json\nprint(json.dumps({"protocol_version":"2","ok":True,"result":{}}))\n',
        encoding="utf-8",
    )
    runtime = JsonSubprocessRuntime([sys.executable, str(bridge)])
    with pytest.raises(RuntimeBridgeError, match="version mismatch"):
        runtime.inspect("demo.rxdb")
