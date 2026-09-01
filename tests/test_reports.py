from rxdb_extractor.reports import (
    build_validation_report,
    read_validation_report,
    write_validation_report,
)
from rxdb_extractor.validation import CheckResult


def test_validation_report_pass_and_roundtrip(tmp_path):
    report = build_validation_report(
        [
            CheckResult("pk", True, observed=2, expected=2),
            CheckResult("fk", True, observed=2, expected=2),
        ]
    )
    assert report.passed
    path = tmp_path / "validation.json"
    write_validation_report(path, report)
    payload = read_validation_report(path)
    assert payload["status"] == "pass"
    assert [check["name"] for check in payload["checks"]] == ["pk", "fk"]
    assert not list(tmp_path.glob("*.tmp"))


def test_validation_report_fails_if_any_check_fails():
    report = build_validation_report(
        [CheckResult("pk", True), CheckResult("fk", False, detail="invalid=1")]
    )
    assert not report.passed
    assert report.to_dict()["status"] == "fail"
