import json
import sys

from rxdb_extractor.artifacts import read_parquet_rows
from rxdb_extractor.cli import main


def _profile():
    return {
        "name": "fixture-vp",
        "source_database": "VP",
        "selection_entity": "RADIO",
        "identity_scope": "RADIO",
        "scope_field": "XRADIO",
        "geography_entities": ["PROV", "DPTO", "FRAC", "RADIO"],
        "id_fields": {"VIVIENDA": "XVID", "HOGAR": "XHID", "PERSONA": "XPID"},
        "entities": [
            {"entity":"VIVIENDA","own_id":"XVID","variable_policy":"all-stored","blocked_variables":[],"keys":[{"sequence_field":"XVID","output_field":"vivienda_key"}],"primary_key":"vivienda_key"},
            {"entity":"HOGAR","own_id":"XHID","variable_policy":"all-stored","blocked_variables":[],"keys":[{"sequence_field":"XHID","output_field":"hogar_key"},{"sequence_field":"XVID","output_field":"vivienda_key"}],"primary_key":"hogar_key"},
            {"entity":"PERSONA","own_id":"XPID","variable_policy":"all-stored","blocked_variables":["PERSONA.HNVUA"],"keys":[{"sequence_field":"XPID","output_field":"persona_key"},{"sequence_field":"XHID","output_field":"hogar_key"},{"sequence_field":"XVID","output_field":"vivienda_key"}],"primary_key":"persona_key"},
        ],
        "foreign_keys": [
            {"child_entity":"HOGAR","child_field":"vivienda_key","parent_entity":"VIVIENDA","parent_field":"vivienda_key"},
            {"child_entity":"PERSONA","child_field":"hogar_key","parent_entity":"HOGAR","parent_field":"hogar_key"},
            {"child_entity":"PERSONA","child_field":"vivienda_key","parent_entity":"VIVIENDA","parent_field":"vivienda_key"},
        ],
    }


def _write_bridge(path):
    path.write_text(
        r'''import json, sys
req = json.load(sys.stdin)
action = req["action"]
if action == "capabilities":
    result = {"redengine_version":"1.3.0-final","selection":True,"number":True,"inherited_define":True,"freq":True,"cmpcode":True,"table_view":False}
elif action == "inspect":
    result = {
      "entities": [
        {"name":"CPV2022","parent":None,"selectable":False,"variables":[]},
        {"name":"PROV","parent":"CPV2022","selectable":True,"variables":[]},
        {"name":"DPTO","parent":"PROV","selectable":True,"variables":[]},
        {"name":"FRAC","parent":"DPTO","selectable":True,"variables":[]},
        {"name":"RADIO","parent":"FRAC","selectable":True,"variables":[]},
        {"name":"VIVIENDA","parent":"RADIO","selectable":False,"variables":[{"name":"V01"}]},
        {"name":"HOGAR","parent":"VIVIENDA","selectable":False,"variables":[{"name":"H10"}]},
        {"name":"PERSONA","parent":"HOGAR","selectable":False,"variables":[{"name":"P02","alias":"SEXO"},{"name":"HNVUA","alias":"HNVUA"}]}
      ],
      "metadata": {"database": req["database"], "fixture": True}
    }
elif action == "execute_record_plan":
    plan = req["plan"]
    bases = {
      "VIVIENDA": [{"XVID":1},{"XVID":2}],
      "HOGAR": [{"XHID":1,"XVID":1},{"XHID":2,"XVID":2}],
      "PERSONA": [{"XPID":1,"XVID":1,"XHID":1},{"XPID":2,"XVID":1,"XHID":1},{"XPID":3,"XVID":2,"XHID":2}]
    }
    geo = {"XPROV":"06","XDPTO":"06147","XFRAC":"0614711","XRADIO":"061471101"}
    masks = {field: field + "__mask" for field in plan["dimension_fields"]}
    rows = []
    for base in bases[plan["entity"]]:
      row = {}
      for field in plan["dimension_fields"]:
        if field in base:
          value = base[field]
        elif field in geo:
          value = geo[field]
        else:
          value = field + "-" + str(base[plan["own_id"]])
        row[field] = value
        row[masks[field]] = 0
      row["count"] = 1
      rows.append(row)
    result = {"rows":rows,"mask_fields":masks,"count_field":"count"}
else:
    print(json.dumps({"protocol_version":"1","ok":False,"error":"unsupported action"}))
    raise SystemExit(0)
print(json.dumps({"protocol_version":"1","ok":True,"result":result}))
''',
        encoding="utf-8",
    )


def test_cli_extract_runs_full_profile_driven_relational_slice(tmp_path, capsys):
    bridge = tmp_path / "bridge.py"
    _write_bridge(bridge)
    profile = tmp_path / "profile.json"
    profile.write_text(json.dumps(_profile()), encoding="utf-8")
    output = tmp_path / "out"
    command = f'{sys.executable} "{bridge}"'

    code = main([
        "--bridge", command,
        "extract", "demo.rxdb",
        "--profile", str(profile),
        "--selection-code", "061471101",
        "--output", str(output),
        "--batch-width", "1",
    ])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "pass"

    persons = read_parquet_rows(output / "persona.parquet")
    assert len(persons) == 3
    assert persons[0]["persona_key"] == "061471101:1"
    assert persons[1]["hogar_key"] == "061471101:1"
    assert persons[2]["vivienda_key"] == "061471101:2"
    assert "HNVUA" not in persons[0]

    manifest = json.loads((output / "dataset-manifest.json").read_text())
    validation = json.loads((output / "validation.json").read_text())
    assert manifest["validation_status"] == "pass"
    assert manifest["provenance"]["runtime"]["redengine_version"] == "1.3.0-final"
    assert manifest["entities"]["PERSONA"]["blocked_variables"] == ["PERSONA.HNVUA"]
    assert validation["status"] == "pass"
