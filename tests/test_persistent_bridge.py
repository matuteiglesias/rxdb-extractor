import sys

from rxdb_extractor.persistent_bridge import JsonPersistentSubprocessRuntime
from rxdb_extractor.planner import build_record_query
from rxdb_extractor.runtime import normalized_plan_executor


def _write_server(path):
    path.write_text(
        r'''import json, sys
count = 0
for line in sys.stdin:
    if not line.strip():
        continue
    count += 1
    req = json.loads(line)
    action = req["action"]
    if action == "capabilities":
        result = {
            "redengine_version": "1.1.0-final",
            "redatamx_version": "1.1.3",
            "selection": True,
            "number": True,
            "inherited_define": True,
            "freq": True,
            "cmpcode": False,
            "table_view": False,
        }
    elif action == "inspect":
        result = {
            "entities": [
                {"name":"RADIO","alias":None,"parent":None,"selectable":True,"variables":[]},
                {"name":"PERSONA","alias":None,"parent":"RADIO","selectable":False,
                 "variables":[{"name":"P02","alias":"SEXO","label":"Sex","type_name":"INTEGER"}]},
            ],
            "metadata": {"database": req["database"], "request_count": count},
        }
    elif action == "execute_record_plan":
        plan = req["plan"]
        masks = {field: field + "__mask" for field in plan["dimension_fields"]}
        rows = []
        for seq in (1, 2):
            row = {}
            for field in plan["dimension_fields"]:
                if field == plan["own_id"]:
                    value = seq
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
        response = {"protocol_version":"1", "ok":False, "error":"bad action"}
        print(json.dumps(response), flush=True)
        continue
    response = {"protocol_version":"1", "ok":True, "result":result}
    print(json.dumps(response), flush=True)
''',
        encoding="utf-8",
    )


def test_persistent_runtime_reuses_one_process_for_many_requests(tmp_path):
    bridge = tmp_path / "bridge_server.py"
    _write_server(bridge)
    runtime = JsonPersistentSubprocessRuntime([sys.executable, str(bridge)])
    try:
        capabilities = runtime.capabilities()
        assert capabilities.redengine_version == "1.1.0-final"
        assert capabilities.redatamx_version == "1.1.3"
        assert not capabilities.cmpcode

        inspection = runtime.inspect("demo.rxdb")
        # capabilities was request 1; inspect is request 2 in the same process.
        assert inspection.metadata["request_count"] == 2

        plan = build_record_query(
            entity="PERSONA",
            selection_entity="RADIO",
            selection_code="061471101",
            identity_scope="RADIO",
            own_id="XPID",
            variables=("PERSONA.P02",),
            use_cmpcode=False,
        )
        rows = normalized_plan_executor(runtime, "demo.rxdb")(plan)
        assert [row["XPID"] for row in rows] == [1, 2]
        assert [row["P02"] for row in rows] == ["P02-1", "P02-2"]
    finally:
        runtime.close()
