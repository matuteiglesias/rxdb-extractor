import pytest

from rxdb_extractor.capabilities import CapabilitySet
from rxdb_extractor.errors import CapabilityError


def test_required_capabilities_green():
    caps = CapabilitySet("1.3.0-final", True, True, True, True, True, False)
    caps.require_record_extraction()


def test_required_capabilities_fail_closed():
    caps = CapabilitySet("x", True, False, True, True)
    with pytest.raises(CapabilityError, match="number"):
        caps.require_record_extraction()
