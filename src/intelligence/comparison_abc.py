"""Daily A/B/C comparison. Human thesis frozen before Ananta is shown."""
from __future__ import annotations

from typing import Any

DIVERGENCE_CLASSES = (
    "SCAN_COVERAGE", "STATE_RECOGNITION", "KNOWLEDGE_RETRIEVAL", "STRATEGY_MATCH",
    "STRATEGY_RANKING", "AUTHORITY", "RISK", "ENTRY", "EXIT", "OUTCOME", "NONE",
)


def freeze_human(thesis: dict[str, Any]) -> dict[str, Any]:
    required = ("asset", "direction", "setup", "market_state", "reason", "timestamp")
    missing = [k for k in required if not thesis.get(k)]
    return {
        "id": "human.thesis.frozen.v1",
        "frozen": True,
        "may_edit_ananta": False,
        "missing": missing,
        "asset": thesis.get("asset"),
        "direction": thesis.get("direction"),
        "setup": thesis.get("setup"),
        "market_state": thesis.get("market_state"),
        "entry": thesis.get("entry"),
        "invalidation": thesis.get("invalidation"),
        "target": thesis.get("target"),
        "reason": thesis.get("reason"),
        "timestamp": thesis.get("timestamp"),
    }


def reconstruct_external(trade: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "external.recon.v1",
        "source": trade.get("source") or "hyperliquid_or_other",
        "not_a_signal": True,
        "not_m2": True,
        "market_state": trade.get("market_state"),
        "available_information": trade.get("available_information"),
        "timeframe": trade.get("timeframe"),
        "direction": trade.get("direction"),
        "entry_context": trade.get("entry_context"),
        "risk": trade.get("risk"),
        "management": trade.get("management"),
        "outcome": trade.get("outcome"),
        "compare_only": ["market_state", "direction", "regime", "strategy_family"],
    }


def compare(ananta: dict[str, Any], human: dict[str, Any] | None, external: dict[str, Any] | None) -> dict[str, Any]:
    a_state = ((ananta.get("market_state") or ananta.get("l2_state") or {}).get("regime"))
    h_state = (human or {}).get("market_state")
    classes = []
    if human and a_state and h_state and str(a_state).upper() != str(h_state).upper():
        classes.append("STATE_RECOGNITION")
    a_issued = ananta.get("issued") or (ananta.get("decision") if isinstance(ananta.get("decision"), str) else None)
    if human and human.get("direction") not in (None, "NONE") and a_issued in ("NO_TRADE", "SHADOW_PAPER", "WAIT", "WATCH"):
        classes.append("AUTHORITY")
    if ananta.get("class_id"):
        classes.append(ananta["class_id"])
    if not classes:
        classes = ["NONE"]
    return {
        "id": "comparison.abc.v1",
        "ananta": {"issued": a_issued, "regime": a_state, "best_id": ananta.get("best_id") or ananta.get("selected_strategy"), "reason": ananta.get("reason")},
        "human": human,
        "external": external,
        "agreement": "DIVERGE" if classes != ["NONE"] else "AGREE",
        "divergence_classes": classes,
        "research_case": classes != ["NONE"],
        "counts_for_m2": False,
        "do_not_copy_external": True,
        "human_must_be_frozen_first": True,
    }
