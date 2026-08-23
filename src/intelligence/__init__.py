"""Decision Intelligence foundation.

Feature-complete behavior machine. Wave A stays WATCH.
No extra agents. Hard safety lives here, outside any LLM.
S5 H1/H2/H3 are parked — this package does not run them.
"""

from src.intelligence.schema import (
    SCHEMA,
    TRADE_ACTIONS,
    TypedDecision,
    ConfidenceTriplet,
    EvidenceCitation,
)
from src.intelligence.profiles import (
    PROFILES,
    DEFAULT_PROFILE,
    get_profile,
    get_active_profile_name,
    set_active_profile,
)

__all__ = [
    "SCHEMA",
    "TRADE_ACTIONS",
    "TypedDecision",
    "ConfidenceTriplet",
    "EvidenceCitation",
    "PROFILES",
    "DEFAULT_PROFILE",
    "get_profile",
    "get_active_profile_name",
    "set_active_profile",
]
