"""Core contracts for rxdb-extractor."""

from .capabilities import CapabilitySet
from .planner import RecordQueryPlan, build_record_query
from .schema import DatabaseSchema, Entity, Variable

__all__ = [
    "CapabilitySet",
    "DatabaseSchema",
    "Entity",
    "RecordQueryPlan",
    "Variable",
    "build_record_query",
]

__version__ = "0.0.1"
