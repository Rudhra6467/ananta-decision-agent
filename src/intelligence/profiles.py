"""SAFE / MODERATE / AGGRESSIVE — behavior profiles, not agents.

One decision engine. Three parameter sets.
Hard Ananta limits always win. Aggressive never means uncontrolled.
Wave A WATCH is outside the profile: no profile can enable or KEEP.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from src.memory import load_memory, save_memory

DEFAULT_PROFILE = "MODERATE"
PROFILE_NAMES = ("SAFE", "MODERATE", "AGGRESSIVE")

# Charter hard ceiling — profiles may be stricter, never looser.
CHARTER_MAX_ENABLED = 5
CHARTER_MAX_SLOTS_PREFERRED = 6
CHARTER_MAX_SLOTS_ABSOLUTE = 8


@dataclass(frozen=True)
class RiskProfile:
    name: str
    max_slots: int
    max_enabled_strategies: int
    max_notional_pct_equity: float
    autonomy_level: int  # 0 recommend-only, 1 constrained, 2 higher-within-hard-limits
    confirmation_required_for_take: bool
    weak_evidence_action: str  # WAIT or SKIP
    min_evidence_confidence_for_take: float
    min_decision_confidence_for_take: float
    allow_uncertain_regime_take: bool
    max_concurrent_takes: int
    skip_on_misclassified: bool
    prefer_wait_when_weak: bool
    description: str

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["cannot_override_ananta"] = True
        d["cannot_promote_wave_a"] = True
        d["cannot_mutate_strategy"] = True
        d["charter_max_enabled"] = CHARTER_MAX_ENABLED
        d["charter_max_slots_absolute"] = CHARTER_MAX_SLOTS_ABSOLUTE
        return d


SAFE = RiskProfile(
    name="SAFE",
    max_slots=2,
    max_enabled_strategies=2,
    max_notional_pct_equity=0.05,
    autonomy_level=0,
    confirmation_required_for_take=True,
    weak_evidence_action="WAIT",
    min_evidence_confidence_for_take=0.75,
    min_decision_confidence_for_take=0.70,
    allow_uncertain_regime_take=False,
    max_concurrent_takes=1,
    skip_on_misclassified=True,
    prefer_wait_when_weak=True,
    description=(
        "Maximum capital/exposure constraints. Strictest strategy/regime gates. "
        "Lowest autonomy. Strongest confirmation. Prefer WAIT/SKIP when evidence is weak."
    ),
)

MODERATE = RiskProfile(
    name="MODERATE",
    max_slots=4,
    max_enabled_strategies=3,
    max_notional_pct_equity=0.15,
    autonomy_level=1,
    confirmation_required_for_take=True,
    weak_evidence_action="WAIT",
    min_evidence_confidence_for_take=0.55,
    min_decision_confidence_for_take=0.55,
    allow_uncertain_regime_take=False,
    max_concurrent_takes=2,
    skip_on_misclassified=False,
    prefer_wait_when_weak=True,
    description=(
        "Balanced exposure and opportunity capture. Normal strategy/risk gates. "
        "More autonomy within predefined limits. Still cannot override Ananta."
    ),
)

AGGRESSIVE = RiskProfile(
    name="AGGRESSIVE",
    max_slots=6,
    max_enabled_strategies=5,
    max_notional_pct_equity=0.30,
    autonomy_level=2,
    confirmation_required_for_take=True,  # Wave A WATCH still requires confirm
    weak_evidence_action="SKIP",
    min_evidence_confidence_for_take=0.40,
    min_decision_confidence_for_take=0.40,
    allow_uncertain_regime_take=True,  # recommend only; execution still gated
    max_concurrent_takes=4,
    skip_on_misclassified=False,
    prefer_wait_when_weak=False,
    description=(
        "Higher permitted exposure and opportunity participation. "
        "More tolerance for uncertainty. Still subject to kill switch, "
        "portfolio constraints, and Ananta execution authority. "
        "Aggressive never means uncontrolled."
    ),
)

PROFILES: Dict[str, RiskProfile] = {
    "SAFE": SAFE,
    "MODERATE": MODERATE,
    "AGGRESSIVE": AGGRESSIVE,
}

_TOLERANCE_MAP = {
    "LOW": "SAFE",
    "SAFE": "SAFE",
    "MEDIUM": "MODERATE",
    "MODERATE": "MODERATE",
    "MID": "MODERATE",
    "HIGH": "AGGRESSIVE",
    "AGGRESSIVE": "AGGRESSIVE",
}


def normalize_profile_name(raw: Optional[str]) -> str:
    key = str(raw or DEFAULT_PROFILE).upper().strip()
    return _TOLERANCE_MAP.get(key, DEFAULT_PROFILE if key not in PROFILES else key)


def get_profile(name: Optional[str] = None) -> RiskProfile:
    return PROFILES[normalize_profile_name(name or get_active_profile_name())]


def get_active_profile_name() -> str:
    mem = load_memory() or {}
    stored = mem.get("risk_profile")
    if stored:
        return normalize_profile_name(stored)
    profile = (mem.get("user_profile") or {}).get("risk_tolerance")
    return normalize_profile_name(profile or DEFAULT_PROFILE)


def set_active_profile(name: str) -> RiskProfile:
    prof = get_profile(name)
    mem = load_memory() or {}
    mem["risk_profile"] = prof.name
    save_memory(mem)
    return prof


def profile_from_user_tolerance(risk_tolerance: Optional[str]) -> RiskProfile:
    return get_profile(normalize_profile_name(risk_tolerance))
