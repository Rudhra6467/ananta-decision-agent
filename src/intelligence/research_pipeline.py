"""Market Research & Evidence Pipeline v1.1.

Want the years. Run them through this pipe. Do not dump everything at once.
Aggressive discovery. Conservative capital. Conservative authority.
"""
from __future__ import annotations

from typing import Any, Dict, List

VERSION = "PIPELINE-v1.1"
RUN_EVERYTHING = False
ACQUIRE_YEARS = True
YEARS_TARGET = "3-4 if Ananta can serve PIT-clean candles"
YEARS_NOW = "~1.2 BTC 1h historical_lab + live 15m Wave A"

NEXT_SLICE = {
    "asset": "ETH/USD",
    "timeframe": "1h",
    "family": "existing specs only",
    "live": False,
    "keep": False,
    "needs": "Ananta observation-replay coverage for ETH/USD 1h",
    "alt": "BTC/USD 15m if ETH coverage is short",
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
        "objective": "live situation → resemble prior states → which capabilities handled them → evidence depth → act or not",
        "not_objective": "wait for authority as the only project motion",
        "stance": {
            "discovery": "aggressive",
            "evidence": "aggressive",
            "capital": "conservative",
            "authority": "conservative",
        },
        "reuse_existing": [
            "observation_v0", "market_truth", "lab_replay", "outcome_truth",
            "decision_quality", "universe", "setup_memory", "fingerprints",
            "evidence_cards", "knowledge_tables",
        ],
        "do_not_fork": "a second crypto-only analytics product",
        "laws": {
            "point_in_time_only": True,
            "acquire_years_progressively": True,
            "do_not_refuse_data_if_pipeline_can_keep_pit": True,
            "adapter_not_new_brain": True,
            "india_after_trust": True,
            "coverage_is_not_intelligence": True,
            "ananta_owns_candles": True,
            "wave_a_frozen": True,
            "aggressive_discovery": True,
            "conservative_capital": True,
        },
    }


def refuse_bulk_score(*, years: int = 4, assets: int = 10) -> Dict[str, Any]:
    return {
        "ok": False,
        "ran": False,
        "reason": "NO_RUN_EVERYTHING",
        "requested": {"years": years, "assets": assets},
        "keep": False,
        "acquire_years": True,
        "note": "Get the years. Score one named slice through this pipe. Do not refuse the data.",
    }


def print_pipeline() -> Dict[str, Any]:
    report = spec()
    sl = report["next_slice"]
    print(f"\nRESEARCH PIPELINE  {report['version']}")
    print("=" * 64)
    print("Acquire years progressively. Do not dump everything. Not KEEP.")
    print(f"  now={report['years_now']}")
    print(f"  want={report['years_target']}")
    print(f"  stance=discover-aggressive  capital-conservative  authority-conservative")
    print("-" * 64)
    print(f"  NEXT SLICE  {sl['asset']} {sl['timeframe']}  live={sl['live']}")
    print(f"    needs={sl['needs']}")
    print(f"    alt={sl['alt']}")
    print("-" * 64)
    print("  ladder: " + " → ".join(report["ladder"]))
    print("  crypto adapter NOW. India/Canada/US = slots after Trust.")
    print("  PIT at decision. Outcomes/MFE/MAE join after.")
    print("=" * 64)
    print()
    return report
