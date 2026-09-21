"""G6 — Strategy-aware exit engine. Does not pretend a fill while paper_take=false."""
from __future__ import annotations

from typing import Any

FAMILY_EXITS = {
    "continuation": {"invalidation": "structure break vs entry swing", "expected_duration": "hours_to_session", "regime_change": ["TREND_DOWN", "RANGE", "EXPANSION"], "trailing": "validated_only"},
    "reversal": {"invalidation": "failed reversal / reclaim of broken level", "expected_duration": "hours", "regime_change": ["TREND_UP", "COMPRESSION"], "trailing": "none_until_validated"},
    "compression": {"invalidation": "squeeze fails / mean re-enter without expansion", "expected_duration": "hours", "regime_change": ["RANGE"], "trailing": "none_until_validated"},
    "lag_catchup": {"invalidation": "leader reverses or lag never starts", "expected_duration": "15m_to_hours", "regime_change": ["TREND_DOWN"], "trailing": "none"},
}


def plan(*, family: str | None, entry: float | None = None, stop: float | None = None, target: float | None = None, direction: str = "NONE", paper_take: bool = False) -> dict[str, Any]:
    spec = FAMILY_EXITS.get(family or "", {})
    return {
        "id": "exit.engine.v1",
        "family": family,
        "entry": entry,
        "initial_stop": stop,
        "target": target,
        "invalidation": spec.get("invalidation") or "named_invalidation_required",
        "expected_duration": spec.get("expected_duration") or "unknown",
        "exit_conditions": ["stop_hit", "target_hit", "invalidation", "regime_change", "adverse_condition", "time_stop_if_validated"],
        "regime_change_conditions": spec.get("regime_change") or [],
        "adverse_condition_handling": "flatten_paper_only_after_grant",
        "trailing_or_management": spec.get("trailing") or "none",
        "exit_reason": None,
        "open": False,
        "paper_take": False,
        "would_open_if_granted": bool(paper_take) and entry is not None and stop is not None,
        "blocked_reason": None if paper_take else "PAPER_GATE_CLOSED",
        "counts_for_m2": False,
    }
