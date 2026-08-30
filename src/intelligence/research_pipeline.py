"""Market Research & Evidence Pipeline v1.2.

Four tracks. Lab complete ≠ product finished.
Aggressive discovery. Conservative capital. Conservative authority.
"""
from __future__ import annotations

from typing import Any, Dict, List

VERSION = "PIPELINE-v1.2"
RUN_EVERYTHING = False
ACQUIRE_YEARS = True
YEARS_TARGET = "3-4 if Ananta can serve PIT-clean candles"
YEARS_NOW = "~1.2y BTC 1h + ETH 1h books + live 15m Wave A"

NEXT_SLICE = {
    "asset": "SOL/USD",
    "timeframe": "1h",
    "family": "existing specs only",
    "live": False,
    "keep": False,
    "needs": "lab replay SOL/USD after git pull (sibling file)",
    "alt": "BTC/USD 15m if SOL replay is short",
}

STAGES: List[str] = [
    "market_adapter",
    "normalize_validate",
    "canonical_market_truth",
    "feature_regime_engine",
    "strategy_replay",
    "cell_strategy_asset_tf_regime_setup",
    "outcome_truth",
    "dq_mfe_mae_risk",
    "pattern_opportunity",
    "evidence_cards_rankings",
    "agent_knowledge_interface",
]

LADDER: List[str] = [
    "in_sample_hist",
    "held_out_hist",
    "frozen_live_watch",
    "human_gated_paper",
    "constrained_autonomy",
]

ADAPTERS = {
    "crypto": {"status": "ACTIVE_LAB", "venue": "ananta+kraken", "now": True},
    "india": {"status": "ADAPTER_SLOT", "venue": None, "now": False},
    "canada": {"status": "ADAPTER_SLOT", "venue": None, "now": False},
    "us": {"status": "ADAPTER_SLOT", "venue": None, "now": False},
}

PIT_ALLOWED = (
    "ohlcv", "volatility", "trend", "compression", "volume",
    "structure", "strategy_state", "regime_hypothesis", "setup_conditions",
    "indicators_asof", "decision", "reason_codes", "provenance",
)
PIT_FORBIDDEN = (
    "future_ohlc", "forward_return_as_feature", "post_decision_news_as_input",
    "llm_invented_fair_value", "look_ahead_fingerprint",
)
POST_ONLY = (
    "fwd_15m", "fwd_1h", "fwd_4h", "costly_protective_wash", "mfe", "mae",
)


def spec() -> Dict[str, Any]:
    return {
        "ok": True,
        "schema": "research_pipeline_v1",
        "version": VERSION,
        "keep": False,
        "run_everything": RUN_EVERYTHING,
        "acquire_years": ACQUIRE_YEARS,
        "years_now": YEARS_NOW,
        "years_target": YEARS_TARGET,
        "next_slice": dict(NEXT_SLICE),
        "stages": list(STAGES),
        "ladder": list(LADDER),
        "adapters": dict(ADAPTERS),
        "point_in_time": {
            "allowed_at_decision": list(PIT_ALLOWED),
            "forbidden_at_decision": list(PIT_FORBIDDEN),
            "join_after": list(POST_ONLY),
        },
        "objective": "state → similar hist → which capabilities → evidence depth → TAKE/WAIT/SKIP/UNKNOWN",
        "not_objective": "wait for tape as the only project motion",
        "stance": {
            "discovery": "aggressive",
            "evidence": "aggressive",
            "capital": "conservative",
            "authority": "conservative",
        },
        "four_tracks": True,
        "laws": {
            "point_in_time_only": True,
            "acquire_years_progressively": True,
            "coverage_is_not_intelligence": True,
            "wave_a_frozen": True,
            "i2_families_locked": True,
            "asset_slices_allowed": True,
            "aggressive_discovery": True,
            "conservative_capital": True,
            "capital_exposure_is_gated": True,
        },
    }


def refuse_bulk_score(*, years: int = 4, assets: int = 10) -> Dict[str, Any]:
    return {
        "ok": False,
        "ran": False,
        "reason": "NO_RUN_EVERYTHING",
        "requested": {"years": years, "assets": assets},
        "keep": False,
        "note": "One named slice. Do not dump 4y × all assets.",
    }


def print_pipeline() -> Dict[str, Any]:
    report = spec()
    sl = report["next_slice"]
    print(f"\nRESEARCH PIPELINE  {report['version']}")
    print("=" * 64)
    print("Four tracks. Lab complete ≠ finished. Not KEEP.")
    print(f"  now={report['years_now']}")
    print(f"  want={report['years_target']}")
    print("  stance=discover-aggressive  capital-conservative  authority-conservative")
    print("-" * 64)
    print(f"  NEXT SLICE  {sl['asset']} {sl['timeframe']}  live={sl['live']}")
    print(f"    needs={sl['needs']}")
    print(f"    alt={sl['alt']}")
    print("-" * 64)
    print("  ladder: " + " → ".join(report["ladder"]))
    print("  T1 watch  T2 hist slice  T3 knowledge tables  T4 scanner/FV design")
    print("=" * 64)
    print()
    return report
