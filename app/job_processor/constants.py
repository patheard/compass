"""Job processor specific shared constants and helpers.

Moved from app.constants to be closer to job processor domain logic.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict


class AwsComplianceType(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    ERROR = "ERROR"


AwsComplianceSummary = Dict[AwsComplianceType, int]


def empty_compliance_summary() -> AwsComplianceSummary:
    """Return a new empty compliance summary dict with zero counts."""
    return {m: 0 for m in AwsComplianceType}
