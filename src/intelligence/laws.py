"""Project laws. TAKE is not KEEP.

Aggressive about discovery and evidence.
Conservative about capital and authority.
"""
from __future__ import annotations

from typing import Dict

LAWS: Dict[str, bool] = {
    "take_is_not_keep": True,
    "take_eq_is_not_paper_take": True,
    "paper_take_is_not_live_take": True,
    "live_take_is_not_keep": True,
    "keep_is_earned_authority": True,
    "live_take_zero_is_watch_not_gap": True,
    "skip_is_a_decision": True,
    "wait_is_a_decision": True,
    "unknown_is_valid": True,
    "wash_is_not_unsuitable": True,
    "sparse_key_does_not_inherit_parent": True,
    "consult_cannot_take": True,
    "consult_cannot_override_issued": True,
    "wave_a_watch": True,
    "i2_hist_baseline_locked": True,
    "ananta_regime_is_hypothesis": True,
    "hard_safety_outside_llm": True,
    "coverage_is_not_intelligence": True,
    "aggressive_discovery": True,
    "conservative_capital": True,
    "conservative_authority": True,
    "acquire_years_progressively": True,
    "do_not_refuse_data_if_pipeline_can_keep_pit": True,
    "four_years_is_fuel_not_the_process": True,
}

VOCAB = {
    "TAKE": "Decision at one observation to act on a setup. Not strategy promotion.",
    "KEEP": "Earned continued authority for a strategy/cell after repeated measured outcomes.",
    "WAIT": "Issued stand-down. Still a decision. Opportunity cost is measured.",
    "SKIP": "Refused a detected setup. Still a decision. Aftermath is COSTLY/PROTECTIVE/WASH.",
    "UNKNOWN": "Not enough evidence to act or to inherit a parent bucket.",
    "WATCH": "Wave A policy: TAKE may be recommended, not issued, not executed.",
    "DISCOVERY": "Search states, setups, missed setups, outcomes. Not a license to trade.",
}


def laws() -> Dict[str, bool]:
    return dict(LAWS)
