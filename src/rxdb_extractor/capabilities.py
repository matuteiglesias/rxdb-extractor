from dataclasses import asdict, dataclass

from .errors import CapabilityError


@dataclass(frozen=True)
class CapabilitySet:
    redengine_version: str
    selection: bool
    number: bool
    inherited_define: bool
    freq: bool
    cmpcode: bool = False
    table_view: bool = False
    redatamx_version: str | None = None

    def require_record_extraction(self) -> None:
        missing = [
            name
            for name in ("selection", "number", "inherited_define", "freq")
            if not getattr(self, name)
        ]
        if missing:
            raise CapabilityError(
                "runtime lacks record-extraction capabilities: " + ", ".join(missing)
            )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
