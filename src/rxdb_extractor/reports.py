from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable

from .validation import CheckResult


@dataclass(frozen=True)
class ValidationReport:
    checks: tuple[CheckResult, ...]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def to_dict(self) -> dict[str, object]:
        return {
            "status": "pass" if self.passed else "fail",
            "checks": [asdict(check) for check in self.checks],
        }


def build_validation_report(checks: Iterable[CheckResult]) -> ValidationReport:
    return ValidationReport(tuple(checks))


def write_validation_report(path: str | Path, report: ValidationReport) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp:
            temp.write(payload)
            temp_path = Path(temp.name)
        temp_path.replace(destination)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def read_validation_report(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
