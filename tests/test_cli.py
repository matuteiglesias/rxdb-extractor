import json
import sys

from rxdb_extractor.cli import main
from rxdb_extractor.reports import build_validation_report, write_validation_report
from rxdb_extractor.validation import CheckResult


def test_validate_cli_returns_zero_for_passing_report(tmp_path, capsys):
    write_validation_report(
        tmp_path / "validation.json",
        build_validation_report([CheckResult("pk", True)]),
    )
    assert main(["validate", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "pass"


def test_validate_cli_returns_one_for_failing_report(tmp_path, capsys):
    path = tmp_path / "report.json"
    write_validation_report(path, build_validation_report([CheckResult("pk", False)]))
    assert main(["validate", str(path)]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "fail"


def test_live_commands_fail_explicitly_until_runtime_is_configured(capsys):
    assert main(["inspect", "example.rxdb"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "runtime-not-configured"


def test_inspect_cli_uses_json_bridge(tmp_path, capsys):
    bridge = tmp_path / "bridge.py"
    bridge.write_text(
        r'''import json, sys
req = json.load(sys.stdin)
if req["action"] == "capabilities":
    result = {"redengine_version":"1.3.0-final","selection":True,"number":True,"inherited_define":True,"freq":True,"cmpcode":True,"table_view":False}
elif req["action"] == "inspect":
    result = {
        "entities": [
            {"name":"RADIO","parent":None,"selectable":True,"variables":[]},
            {"name":"PERSONA","parent":"RADIO","selectable":False,
             "variables":[{"name":"P02","alias":"SEXO","label":"Sex"}]},
        ],
        "metadata": {"path": req["database"]},
    }
else:
    result = {}
print(json.dumps({"protocol_version":"1","ok":True,"result":result}))
''',
        encoding="utf-8",
    )
    command = f'{sys.executable} "{bridge}"'
    assert main(["--bridge", command, "inspect", "demo.rxdb"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["capabilities"]["redengine_version"] == "1.3.0-final"
    assert payload["database"]["metadata"]["path"] == "demo.rxdb"
    assert payload["database"]["entities"][1]["parent"] == "RADIO"
