"""Opportunity Engine — interface lock only (I3). Not a scanner. Not KEEP.

Two capabilities are on the roadmap:
  1. Continuous opportunity scanning
  2. Fair-value / mispricing detection

Neither runs now. LLM does not scan unrestricted. LLM does not invent fair value.
Coverage (N strategies × TF × assets) is not intelligence.

CLI: lab opportunity
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

VERSION = "OPP-v0.2"
PHASE = "I2_LOCKED"
SCAN_LIVE = False
MISPRICING_EXECUTE = False
CANDIDATE_FIELDS = (
    "asset", "timeframe", "strategy", "setup", "fingerprint", "evidence_ref", "provenance",
)
FAIR_VALUE_FIELDS = (
    "asset", "asof", "model", "inputs", "fair_value", "spot", "divergence",
    "uncertainty", "provenance",
)

INTELLIGENCE_PHASES = (
    ("I1", "CURRENT", "Wave A frozen, live+hist evidence, DQ, Universe, fingerprints, memory"),
    ("I2", "RESEARCH_EXPANSION", "Broader families offline, more assets/TF, evidence cards"),
    ("I3", "OPPORTUNITY_INTELLIGENCE", "Scanner + state change + capability match + fair-value"),
    ("I4", "DECISION_INTELLIGENCE", "Retrieve similar states, rank, TAKE/WAIT/SKIP/UNKNOWN"),
    ("I5", "FORWARD_PAPER", "Human-gated paper TAKEs, beat DQ-v0.0"),
    ("I6", "EARNED_AUTONOMY", "SAFE/MODERATE/AGGRESSIVE only after evidence"),
)

LAWS = {
    "two_tracks_stay_separate": True,
    "wave_a_frozen": True,
    "watcher_untouched": True,
    "coverage_is_not_intelligence": True,
    "llm_does_not_scan_unrestricted": True,
    "deterministic_market_truth_filters_first": True,
    "di_reasons_only_on_candidates": True,
    "scanner_is_not_live_enable": True,
    "research_universe_can_be_broad": True,
    "live_authority_stays_narrow": True,
    "fair_value_is_not_a_strategy": True,
    "llm_does_not_invent_fair_value": True,
    "fair_value_needs_inputs_provenance_uncertainty": True,
    "mispricing_is_not_execution": True,
    "keep_forbidden": True,
    "no_trend_up_enable": True,
    "no_hunter_rewrite": True,
    "paper_may_be_aggressive_later": True,
    "live_stays_conservative": True,
    "incomplete_candidate_is_not_an_opportunity": True,
}


def spec() -> Dict[str, Any]:
    return {
        "ok": True,
        "schema": "opportunity_engine_v0",
        "version": VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "phase": PHASE,
        "scan_live": SCAN_LIVE,
        "mispricing_execute": MISPRICING_EXECUTE,
        "keep": False,
        "tracks": {
            "wave_a_live": "controlled baseline — lab watch 15 — do not change rules",
            "universe_research": "catalogue + hist memory — not an intelligent library yet",
        },
        "target_flow": [
            "Market APIs",
            "Market Truth",
            "Market State / fingerprint",
            "strategy capability scanners",
            "Opportunity Engine",
            "historical/setup evidence",
            "Decision Intelligence",
            "TAKE / WAIT / SKIP / UNKNOWN",
            "Ananta hard risk",
            "execution",
            "outcome + DQ",
        ],
        "capabilities": {
            "continuous_scan": {
                "status": "INTERFACE_ONLY",
                "live": False,
                "candidate_fields": list(CANDIDATE_FIELDS),
                "note": "Deterministic scanners filter. DI reasons only on candidates.",
            },
            "fair_value": {
                "status": "INTERFACE_ONLY",
                "execute": False,
                "llm_invented_fair_value": False,
                "required_fields": list(FAIR_VALUE_FIELDS),
                "note": "Explicit inputs + provenance + uncertainty. Not a Wave A strategy.",
            },
            "catalysts": {
                "status": "INTERFACE_ONLY",
                "live": False,
                "note": "lab catalysts — headline is not a trade.",
            },
        },
        "intelligence_phases": [
            {"id": i, "name": n, "means": m} for i, n, m in INTELLIGENCE_PHASES
        ],
        "now": "I2_LOCKED",
        "not_now": ["I3 scan", "I3 mispricing execute", "I4 similarity", "I5 paper TAKE", "I6 autonomy"],
        "laws": LAWS,
    }


def refuse_scan(*, universe: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "ok": False,
        "executed": False,
        "scanned": 0,
        "candidates": [],
        "reason": "I3_NOT_NOW",
        "universe_requested": list(universe or []),
        "keep": False,
        "note": "Interface only. Continuous scan is Phase I3. Wave A watch is the live experiment.",
    }


def refuse_fair_value(*, asset: Optional[str] = None) -> Dict[str, Any]:
    return {
        "ok": False,
        "executed": False,
        "fair_value": None,
        "divergence": None,
        "reason": "I3_NOT_NOW",
        "asset": asset,
        "llm_invented": False,
        "keep": False,
        "note": "Fair value is not an LLM price. Not a strategy. Not execution.",
    }


def make_candidate(payload: Optional[dict] = None) -> Dict[str, Any]:
    """Accept only a complete candidate object. Never live-enables."""
    payload = payload or {}
    missing = [f for f in CANDIDATE_FIELDS if not payload.get(f)]
    return {
        "ok": not missing,
        "schema": "opportunity_candidate_v0",
        "live": False,
        "execute": False,
        "keep": False,
        "missing": missing,
        "reason": "INCOMPLETE_CANDIDATE" if missing else "CANDIDATE_RECORDED_NOT_LIVE",
        "candidate": None if missing else {k: payload.get(k) for k in CANDIDATE_FIELDS},
    }


def make_fair_value(payload: Optional[dict] = None) -> Dict[str, Any]:
    """Refuse LLM prices and incomplete models."""
    payload = payload or {}
    missing = [f for f in FAIR_VALUE_FIELDS if payload.get(f) in (None, "", [])]
    invented = bool(payload.get("llm_invented") or payload.get("model") == "llm")
    return {
        "ok": False,
        "schema": "fair_value_v0",
        "execute": False,
        "keep": False,
        "llm_invented": invented,
        "missing": missing,
        "reason": "LLM_INVENTED_FAIR_VALUE" if invented else (
            "INCOMPLETE_FAIR_VALUE" if missing else "I3_NOT_NOW"
        ),
        "fair_value": None,
        "note": "Even a complete object cannot execute while I3 is interface-only.",
    }


def print_opportunity() -> Dict[str, Any]:
    report = spec()
    print(f"\nOPPORTUNITY ENGINE  {report['version']}  phase={report['phase']}")
    print("=" * 64)
    print("Interface lock. Not a scanner. Not mispricing execution. Not KEEP.")
    print("Coverage (N×TF×asset) is not intelligence.")
    print("-" * 64)
    print("  TRACKS (keep separate)")
    print("    Wave A live     lab watch 15 — frozen rules, accumulating tape")
    print("    Universe research  hist memory — catalogue, SUITABLE=0")
    print("-" * 64)
    print("  NOW = I2_LOCKED. Mapped, not running:")
    print("    continuous_scan  INTERFACE_ONLY  live=False")
    print("    fair_value       INTERFACE_ONLY  execute=False  llm_invented=False")
    print("    candidate_v0     incomplete object is not an opportunity")
    print("-" * 64)
    print("  I1 current → I2 research expansion → I3 opportunity intelligence")
    print("  → I4 DI → I5 human-gated paper → I6 earned autonomy")
    print("-" * 64)
    print("  LLM does not scan unrestricted. Deterministic Market Truth filters first.")
    print("  Scanner ≠ live enable. Fair value ≠ strategy. Clash ≠ rewrite.")
    print("=" * 64)
    print()
    return report
