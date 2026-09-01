import json

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
