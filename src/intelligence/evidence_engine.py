"""Strategy Evidence Engine — destination layer (not live).

Memory may inform TAKE/WAIT/SKIP. Memory may not KEEP.
No blended 81/100. No LLM-invented 95% confidence.
Similarity search is later — only after TAKE n is real.

CLI: lab cards  (also lab universe cells)
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.intelligence.universe_specs import (
    EVALUATORS,
    REGIME_CLASSIFIER,
    REGIME_VERSION,
    STRATEGY_VERSIONS,
    WAVE_A_REGIMES,
)

VERSION = "EVIDENCE-v0"
PROVENANCE_SCHEMA = "evidence_provenance_v0"
DQ_VERSION = "DQ-v0.1"
UNIVERSE_VERSION = "UNIVERSE-v1.5"
OBSERVATION_SCHEMA = "observation_v0"
OUTCOME_HORIZONS = ("+15m", "+1h", "+4h")
# Destination sequence. Do not skip to similarity.
SEQUENCE = (
    "Wave A frozen",
    "DQ-v0 locked",
    "Universe v1 scaffold",
    "Universe v1.1 evidence depth",
    "Universe v1.2 continuation hist shadow (not live watch)",
    "Setup Memory v0 jsonl join",
    "Market Truth fingerprints v0",
    "Strategy-conditioned fingerprints v0.1",
    "Universe v1.3 regime vs independent tape",
    "Opportunity Engine interface lock (I3 mapped, not running)",
    "Evidence cards (cells, not a score)",  # NOW lab cards
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
    "evidence_without_provenance_is_a_speech": True,
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


def provenance(
    *,
    strategy: str,
    asset: str,
    timeframe: str,
    regime: str,
    source: str,
    period: Optional[dict] = None,
) -> Dict[str, Any]:
    """Every claim must answer: which data, version, period, regime, policy, outcomes."""
    strat_ver = STRATEGY_VERSIONS.get(strategy)
    return {
        "schema": PROVENANCE_SCHEMA,
        "source": source if source in ("historical_lab", "live_paper") else "NONE",
        "live_and_hist_are_separate": True,
        "observation_schema": OBSERVATION_SCHEMA,
        "strategy": strategy,
        "strategy_version": strat_ver,
        "strategy_version_gap": strat_ver is None,
        "evaluator": EVALUATORS.get(strategy),
        "asset": asset,
        "timeframe": timeframe,
        "regime": regime,
        "regime_classifier": REGIME_CLASSIFIER,
        "regime_version": REGIME_VERSION,
        "regime_is_hypothesis": True,
        "decision_policy": {
            "wave_a": "WATCH",
            "wave_a_regimes": sorted(WAVE_A_REGIMES.get(strategy, frozenset())),
            "dq_version": DQ_VERSION,
            "universe_version": UNIVERSE_VERSION,
            "keep": False,
            "live_enable": False,
        },
        "outcome_horizons": list(OUTCOME_HORIZONS),
        "hist_15m": "UNUSABLE" if source == "historical_lab" and timeframe == "1h" else None,
        "period": period or {"min_ts": None, "max_ts": None, "n_rows": 0},
        "note": (
            "A claim without this block is a speech. "
            "regime_version DATA_GAP until Ananta stamps classify_regime."
        ),
    }


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
        "provenance": cell.get("provenance") or provenance(
            strategy=str(cell.get("strategy") or ""),
            asset=str(cell.get("asset") or ""),
            timeframe=str(cell.get("timeframe") or ""),
            regime=str(cell.get("regime") or ""),
            source=str(cell.get("coverage") or "NONE"),
        ),
        "take_1h": take,
        "skip_setup_1h": cell.get("skip_setup_1h"),
        "failure_top": cell.get("failure_top") or {},
        "regime_vs_tape": cell.get("regime_vs_tape"),
        "blended_score": None,
        "keep": False,
        "live_enable": False,
        "laws": LAWS,
        "note": (
            "Card is DQ cells + depth. "
            "No 81/100. Confidence is a band computed from n/depth/status."
        ),
    }
