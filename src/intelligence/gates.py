"""Hard safety gates — outside the LLM, outside profiles.

Pipeline:
    Agent recommendation
      → profile gates (stricter than charter, never looser)
      → hard gates (cannot be overridden by profile, LLM, or user intent)
      → Ananta execution authority

The agent can recommend TAKE. Nothing in this package places a Wave A fill.
Aggressive never bypasses these gates.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.intelligence.profiles import (
    CHARTER_MAX_ENABLED,
    CHARTER_MAX_SLOTS_ABSOLUTE,
    RiskProfile,
    get_profile,
)
from src.intelligence.schema import WAVE_A, GateHit, _norm_action

# Hard codes — tests and CLI key off these strings.
WAVE_A_WATCH = "WAVE_A_WATCH"
NON_WAVE_A_LOCKED = "NON_WAVE_A_LOCKED"
ANANTA_UNREACHABLE = "ANANTA_UNREACHABLE"
ANANTA_KILL = "ANANTA_KILL"
SLOT_CAP = "SLOT_CAP"
ENABLED_CAP = "ENABLED_CAP"
REGIME_FILTER = "REGIME_FILTER"
NO_SETUP_IS_WAIT = "NO_SETUP_IS_WAIT"
UNKNOWN_IS_DATA_GAP = "UNKNOWN_IS_DATA_GAP"
NO_STRATEGY_MUTATION = "NO_STRATEGY_MUTATION"
NO_KEEP_WITHOUT_TAKE = "NO_KEEP_WITHOUT_TAKE"
NO_S5_RUN = "NO_S5_RUN"
NO_EXTRA_AGENTS = "NO_EXTRA_AGENTS"
PAPER_ONLY = "PAPER_ONLY"
CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
WEAK_EVIDENCE = "WEAK_EVIDENCE"
MISCLASSIFIED_BLOCK = "MISCLASSIFIED_BLOCK"
PROFILE_SLOT_CAP = "PROFILE_SLOT_CAP"
PROFILE_ENABLED_CAP = "PROFILE_ENABLED_CAP"
INTENT_FORBIDS_TAKE = "INTENT_FORBIDS_TAKE"
EXECUTION_AUTHORITY_ANANTA = "EXECUTION_AUTHORITY_ANANTA"

HARD_ALWAYS = (
    WAVE_A_WATCH,
    NON_WAVE_A_LOCKED,
    ANANTA_KILL,
    NO_STRATEGY_MUTATION,
    NO_KEEP_WITHOUT_TAKE,
    NO_S5_RUN,
    NO_EXTRA_AGENTS,
    PAPER_ONLY,
    EXECUTION_AUTHORITY_ANANTA,
)


def evaluate_gates(
    *,
    recommended_action: str,
    strategy_key: Optional[str] = None,
    setup_detected: Optional[bool] = None,
    skip_reason: Optional[str] = None,
    profile: Optional[RiskProfile] = None,
    user_intent: str = "OBSERVE",
    ananta_ok: bool = True,
    kill_switch: bool = False,
    slots_used: int = 0,
    enabled_count: int = 0,
    evidence_confidence: float = 0.0,
    decision_confidence: float = 0.0,
    regime_audit: Optional[str] = None,
    user_confirmed: bool = False,
    missing_observations: bool = False,
) -> Tuple[bool, str, List[GateHit]]:
    """Return (execution_allowed, issued_action, hits).

    execution_allowed is True only for a TAKE that passed every gate.
    Today that is always False for Wave A (WATCH) and for every other key
    (other 12 locked). WAIT/SKIP/HOLD are issued locally; they are not fills.
    """
    profile = profile or get_profile()
    rec = _norm_action(recommended_action)
    hits: List[GateHit] = []
    key = (strategy_key or "").lower().strip() or None

    def hard(code: str, passed: bool, detail: str) -> None:
        hits.append(GateHit(code=code, layer="hard", passed=passed, detail=detail))

    def prof(code: str, passed: bool, detail: str) -> None:
        hits.append(GateHit(code=code, layer="profile", passed=passed, detail=detail))

    def ananta(code: str, passed: bool, detail: str) -> None:
        hits.append(GateHit(code=code, layer="ananta", passed=passed, detail=detail))

    # --- always-on laws (even for WAIT/SKIP) ---
    hard(NO_STRATEGY_MUTATION, True, "Agent may propose experiments; it may not rewrite hunter/squeeze/bollinger-mr")
    hard(NO_S5_RUN, True, "H1/H2/H3 are parked pending tape; this gate refuses to start them")
    hard(NO_EXTRA_AGENTS, True, "SAFE/MODERATE/AGGRESSIVE are profiles, not agents")
    hard(PAPER_ONLY, True, "No live capital until Trust Report")
    hard(NO_KEEP_WITHOUT_TAKE, True, "WAIT/SKIP marks are not KEEP evidence")
    ananta(EXECUTION_AUTHORITY_ANANTA, True, "Ananta owns fills, slots, kill switch, regime router, exits")

    if missing_observations:
        hard(UNKNOWN_IS_DATA_GAP, False, "Missing strategy_observations is DATA_GAP, never 'no setup'")
    else:
        hard(UNKNOWN_IS_DATA_GAP, True, "Observations present")

    if setup_detected is False and rec == "TAKE":
        hard(NO_SETUP_IS_WAIT, False, "No setup cannot become TAKE")
        rec = "WAIT"
    else:
        hard(NO_SETUP_IS_WAIT, True, "TAKE requires a detected setup")

    if str(skip_reason or "").upper() == "REGIME_FILTERED" and rec == "TAKE":
        hard(REGIME_FILTER, False, "Ananta router filtered this setup; Agent cannot override")
        rec = "SKIP"
    else:
        hard(
            REGIME_FILTER,
            True,
            "No REGIME_FILTERED override attempted"
            if str(skip_reason or "").upper() != "REGIME_FILTERED"
            else "REGIME_FILTERED honored as SKIP",
        )

    if kill_switch:
        ananta(ANANTA_KILL, False, "Kill switch on — TAKE forbidden")
        if rec == "TAKE":
            rec = "WAIT"
    else:
        ananta(ANANTA_KILL, True, "Kill switch not asserted")

    if not ananta_ok and rec == "TAKE":
        ananta(ANANTA_UNREACHABLE, False, "Ananta cycle failed; cannot TAKE into a hole")
        rec = "WAIT"
    else:
        ananta(ANANTA_UNREACHABLE, ananta_ok, "Ananta reachable" if ananta_ok else "Ananta down (non-TAKE ok)")

    # Charter ceilings
    if slots_used >= CHARTER_MAX_SLOTS_ABSOLUTE and rec == "TAKE":
        hard(SLOT_CAP, False, f"slots_used={slots_used} >= absolute max {CHARTER_MAX_SLOTS_ABSOLUTE}")
        rec = "WAIT"
    else:
        hard(SLOT_CAP, True, f"slots_used={slots_used} charter_abs={CHARTER_MAX_SLOTS_ABSOLUTE}")

    if enabled_count > CHARTER_MAX_ENABLED:
        hard(ENABLED_CAP, False, f"enabled={enabled_count} > charter max {CHARTER_MAX_ENABLED}")
    else:
        hard(ENABLED_CAP, True, f"enabled={enabled_count} <= {CHARTER_MAX_ENABLED}")

    # Profile (stricter)
    if slots_used >= profile.max_slots and rec == "TAKE":
        prof(PROFILE_SLOT_CAP, False, f"slots_used={slots_used} >= profile {profile.name} max {profile.max_slots}")
        rec = "WAIT"
    else:
        prof(PROFILE_SLOT_CAP, True, f"profile {profile.name} max_slots={profile.max_slots}")

    if enabled_count > profile.max_enabled_strategies:
        prof(
            PROFILE_ENABLED_CAP,
            False,
            f"enabled={enabled_count} > profile {profile.name} max {profile.max_enabled_strategies}",
        )
    else:
        prof(PROFILE_ENABLED_CAP, True, f"profile {profile.name} max_enabled={profile.max_enabled_strategies}")

    intent = str(user_intent or "OBSERVE").upper()
    if rec == "TAKE" and intent in ("OBSERVE", "RESEARCH"):
        prof(INTENT_FORBIDS_TAKE, False, f"intent={intent} forbids TAKE")
        rec = "WAIT"
    else:
        prof(INTENT_FORBIDS_TAKE, True, f"intent={intent}")

    if rec == "TAKE" and evidence_confidence < profile.min_evidence_confidence_for_take:
        prof(
            WEAK_EVIDENCE,
            False,
            f"evidence={evidence_confidence:.2f} < {profile.min_evidence_confidence_for_take:.2f} ({profile.name})",
        )
        rec = profile.weak_evidence_action if profile.weak_evidence_action in ("WAIT", "SKIP") else "WAIT"
    elif rec == "TAKE" and decision_confidence < profile.min_decision_confidence_for_take:
        prof(
            WEAK_EVIDENCE,
            False,
            f"decision={decision_confidence:.2f} < {profile.min_decision_confidence_for_take:.2f} ({profile.name})",
        )
        rec = profile.weak_evidence_action if profile.weak_evidence_action in ("WAIT", "SKIP") else "WAIT"
    else:
        prof(WEAK_EVIDENCE, True, f"confidence vs {profile.name} thresholds")

    audit = str(regime_audit or "").upper()
    if rec == "TAKE" and audit == "MISCLASSIFIED" and profile.skip_on_misclassified:
        prof(MISCLASSIFIED_BLOCK, False, "SAFE profile treats MISCLASSIFIED as SKIP")
        rec = "SKIP"
    else:
        prof(MISCLASSIFIED_BLOCK, True, f"regime_audit={audit or 'none'}")

    if rec == "TAKE" and (not profile.allow_uncertain_regime_take) and audit in ("UNCERTAIN", "UNCLEAR"):
        prof(MISCLASSIFIED_BLOCK, False, f"{profile.name} refuses TAKE under UNCERTAIN regime audit")
        rec = profile.weak_evidence_action if profile.weak_evidence_action in ("WAIT", "SKIP") else "WAIT"

    if rec == "TAKE" and profile.confirmation_required_for_take and not user_confirmed:
        prof(CONFIRMATION_REQUIRED, False, f"{profile.name} requires human confirm for TAKE")
        # recommendation stays TAKE; issued becomes WAIT until confirmed — handled below
        issued_if_confirmed = "TAKE"
    else:
        prof(CONFIRMATION_REQUIRED, True, "confirmation not required or already given")
        issued_if_confirmed = rec

    # Wave A / other-12 locks — last, never overridable
    if rec == "TAKE" and key in WAVE_A:
        hard(WAVE_A_WATCH, False, f"{key} is WATCH; TAKE is a recommendation, not a fill, not KEEP")
        issued = "WAIT"
        allowed = False
    elif rec == "TAKE" and key and key not in WAVE_A:
        hard(NON_WAVE_A_LOCKED, False, f"{key} is outside Wave A; the other 12 stay locked")
        issued = "WAIT"
        allowed = False
    elif rec == "TAKE" and not key:
        hard(WAVE_A_WATCH, False, "TAKE without strategy_key cannot execute")
        issued = "WAIT"
        allowed = False
    else:
        hard(WAVE_A_WATCH, True, "No Wave A TAKE execution attempted")
        hard(NON_WAVE_A_LOCKED, True, "No non-Wave-A enable/TAKE attempted")
        issued = rec
        allowed = False  # this package never self-executes; Ananta is authority
        if rec == "TAKE" and user_confirmed:
            # Still false: even a confirmed TAKE is a proposal to Ananta, not a fill.
            allowed = False
            issued = "WAIT"
            hard(
                EXECUTION_AUTHORITY_ANANTA,
                False,
                "Confirmed TAKE is still a proposal; Ananta must accept. Package will not place the order.",
            )

    # Non-TAKE issued actions are local (SKIP/WAIT/HOLD) — not fills.
    if issued != "TAKE":
        allowed = False

    # Collapse: if profile confirmation blocked TAKE, issued is WAIT
    if recommended_action and _norm_action(recommended_action) == "TAKE" and issued_if_confirmed != "TAKE":
        issued = issued if issued != "TAKE" else "WAIT"

    return allowed, issued, hits


def gate_summary(hits: Sequence[GateHit]) -> Dict[str, Any]:
    failed = [h.as_dict() for h in hits if not h.passed]
    return {
        "n_gates": len(hits),
        "n_failed": len(failed),
        "failed": failed,
        "hard_always": list(HARD_ALWAYS),
    }
