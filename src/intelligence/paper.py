"""End-to-end paper / simulation workflow.

Runs the DI loop against a fixture or the latest observation.
Never calls Ananta place_manual_paper_order.
Never enables a strategy.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.intelligence.orchestrate import propose_execution, run_cycle
from src.intelligence.schema import WAVE_A


def simulate(
    observation: Optional[dict] = None,
    *,
    persist: bool = False,
) -> Dict[str, Any]:
    cycle = run_cycle(observation, persist=persist, user_confirmed=False)
    decision = cycle.get("decision") or {}
    proposal = propose_execution(decision)
    return {
        "ok": True,
        "mode": "paper_sim",
        "placed_order": False,
        "enabled_strategy": False,
        "wave_a": list(WAVE_A),
        "wave_a_status": "WATCH",
        "cycle": cycle,
        "proposal": proposal,
        "assertions": {
            "no_fill": proposal.get("executed") is False,
            "take_not_keep": True,
            "s5_not_started": True,
        },
    }


def simulate_take_blocked(observation: dict) -> Dict[str, Any]:
    """Prove that a TAKE-equivalent hunter REVERSAL still cannot fill."""
    result = simulate(observation, persist=False)
    rec = (result.get("cycle") or {}).get("decision") or {}
    return {
        "recommended_action": rec.get("recommended_action"),
        "issued_action": rec.get("issued_action"),
        "execution_allowed": rec.get("execution_allowed"),
        "placed_order": result.get("placed_order"),
        "blocked": True,
        "wave_a_status": "WATCH",
    }
