class RxdbError(Exception):
    """Base error for rxdb-extractor."""


class CapabilityError(RxdbError):
    """Raised when the runtime lacks a launch-critical capability."""


class RuntimeBridgeError(RxdbError):
    """Raised when an external RedEngine bridge violates the runtime protocol."""


class SchemaError(RxdbError):
    """Raised when the database entity graph is inconsistent or unsupported."""


class PlanningError(RxdbError):
    """Raised when a deterministic extraction query cannot be planned."""


class NormalizationError(RxdbError):
    """Raised when a FREQ result cannot safely be interpreted as records."""


class ValidationError(RxdbError):
    """Raised when an extraction fails a required data-integrity validation."""


class CheckpointError(RxdbError):
    """Raised when a provenance checkpoint is invalid or unsafe."""
