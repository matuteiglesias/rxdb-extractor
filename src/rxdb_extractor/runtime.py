from typing import Protocol

from .capabilities import CapabilitySet


class RuntimeAdapter(Protocol):
    """Boundary between extraction logic and a concrete RedEngine binding."""

    def capabilities(self) -> CapabilitySet: ...

    def inspect(self, database: str) -> dict[str, object]: ...

    def run_spc(self, database: str, spc: str) -> object: ...
