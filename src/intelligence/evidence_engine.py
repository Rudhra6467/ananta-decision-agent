"""Strategy Evidence Engine — destination layer (not live).

Memory may inform TAKE/WAIT/SKIP. Memory may not KEEP.
No blended 81/100. No LLM-invented 95% confidence.
Similarity search is later — only after TAKE n is real.

CLI uses Universe cards today: lab universe
"""
from __future__ import annotations

from typing import Any, Dict, Optional

VERSION = "EVIDENCE-v0"
# Destination sequence. Do not skip to similarity.
SEQUENCE = (
    "Wave A frozen",
    "DQ-v0 locked",
    "Universe v1 scaffold",
    "Universe v1.1 evidence depth",  # NOW
    "One extra spec on observation_v0 (continuation, not live watch)",
    "Setup records = observation_v0 joins",
    "Evidence cards (cells, not a score)",
    "Market-state fingerprints from Market Truth",
    "Similarity search",
    "Contextual ranking (separate boards)",
    "Forward paper vs historical",
    "DQ updates knowledge",
    "Constrained autonomy",
)

LAWS = {
    "unknown_is_valid": True,
    "unknown_is_not_unsuitable": True,
    "suitable_is_not_keep": True,
    "win_rate_is_not_confidence": True,
    "no_blended_dq_score": True,
    "no_llm_percent_confidence": True,
    "hist_is_not_forward": True,
    "memory_does_not_authorize_keep": True,
    "fat_sample_of_a_bad_rule_is_still_bad": True,
    "similarity_is_structured_features_not_chart_lookalike": True,
}


def coverage_band(n_rows: int, *, tested: bool) -> str:
    if not tested:
        return "NONE"
    if n_rows <= 0:
        return "NONE"
    if n_rows < 30:
        return "LOW"
    if n_rows < 200:
        return "MEDIUM"
    return "HIGH"


def confidence_band(status: str, depth: str, n_take: int) -> str:
    """Computed band. Never a 0–100. Never LLM-authored."""
    if status == "UNTESTED":
        return "NONE"
    if n_take <= 0 or depth in ("NONE", "ANECDOTE"):
        return "VERY_LOW"
    if depth == "THIN":
        return "LOW"
    if status in ("WASH", "TESTED_UNKNOWN"):
        return "MEDIUM" if depth in ("ADEQUATE", "SOLID") else "LOW"
    if status in ("SUITABLE", "UNSUITABLE") and depth == "SOLID":
        return "HIGH"
    if status in ("SUITABLE", "UNSUITABLE"):
        return "MEDIUM"
    return "LOW"


def status_class(*, tested: bool, fit: str, why: str) -> str:
    """UNTESTED vs TESTED_UNKNOWN vs WASH vs fit.

    UNKNOWN because we never ran the evaluator ≠ UNKNOWN after a wash.
    """
    if not tested:
        return "UNTESTED"
    if fit == "SUITABLE":
        return "SUITABLE"
    if fit == "UNSUITABLE":
        return "UNSUITABLE"
    if why == "WASH":
        return "WASH"
    return "TESTED_UNKNOWN"


def completeness(n_fwd: int, n_rows: int) -> Optional[float]:
    if n_rows <= 0:
        return None
    return round(n_fwd / n_rows, 4)


def card_from_cell(cell: dict) -> Dict[str, Any]:
    """Setup Evidence Card v0 — cells, not 81/100."""
    take = cell.get("take_1h") or {}
    return {
        "schema": "setup_evidence_card_v0",
        "version": VERSION,
        "strategy": cell.get("strategy"),
        "asset": cell.get("asset"),
        "timeframe": cell.get("timeframe"),
        "regime": cell.get("regime"),
        "policy": cell.get("policy"),
        "status_class": cell.get("status_class"),
        "fit": cell.get("fit"),
        "why": cell.get("why"),
        "samples": cell.get("n_rows"),
        "n_setup": cell.get("n_setup"),
        "n_take": cell.get("n_take"),
        "n_skip_setup": cell.get("n_skip_setup"),
        "outcome_completeness_1h": cell.get("outcome_completeness_1h"),
        "evidence_depth": cell.get("evidence_depth"),
        "coverage_band": cell.get("coverage_band"),
        "confidence_band": cell.get("confidence_band"),
        "take_1h": take,
        "skip_setup_1h": cell.get("skip_setup_1h"),
        "failure_top": cell.get("failure_top") or {},
        "blended_score": None,
        "keep": False,
        "live_enable": False,
        "laws": LAWS,
        "note": (
            "Card is DQ cells + depth. "
            "No 81/100. Confidence is a band computed from n/depth/status."
        ),
    }
