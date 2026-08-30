"""Market Research & Evidence Pipeline v1. Process lock. Not a 4-year dump.

Same engines we already run. Venue adapters plug in later.
India/Canada/US are adapters after Trust — not this week's ingest.

CLI: lab pipeline
"""
from __future__ import annotations

from typing import Any, Dict, List

VERSION = "PIPELINE-v1"
RUN_EVERYTHING = False
YEARS_TARGET = "3-4 when Ananta coverage exists"
YEARS_NOW = "~1.2 BTC 1h historical_lab + live 15m Wave A"

STAGES: List[str] = [
    "market_adapter",
    "normalize_validate",
    "canonical_market_truth",
    "feature_regime_engine",
    "strategy_replay",
    "cell_strategy_asset_tf_regime_setup",
    "outcome_truth",
    "dq_risk_consistency",
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
POST_ONLY = ("fwd_15m", "fwd_1h", "fwd_4h", "costly_protective_wash")


def spec() -> Dict[str, Any]:
    return {
        "ok": True,
        "schema": "research_pipeline_v1",
        "version": VERSION,
        "keep": False,
        "run_everything": RUN_EVERYTHING,
        "years_now": YEARS_NOW,
        "years_target": YEARS_TARGET,
        "stages": list(STAGES),
        "ladder": list(LADDER),
        "adapters": dict(ADAPTERS),
        "point_in_time": {
            "allowed_at_decision": list(PIT_ALLOWED),
            "forbidden_at_decision": list(PIT_FORBIDDEN),
            "join_after": list(POST_ONLY),
        },
        "objective": "repeatable state → opportunity → strategy → outcome relationships",
        "not_objective": "thousands of scores from running everything over everything",
        "reuse_existing": [
            "observation_v0", "market_truth", "lab_replay", "outcome_truth",
            "decision_quality", "universe", "setup_memory", "fingerprints",
            "evidence_cards", "knowledge_tables",
        ],
        "do_not_fork": "a second crypto-only analytics product",
        "next_slice": "one offline cell (ETH 1h or BTC 15m on an existing spec) if Ananta can serve it",
        "laws": {
            "point_in_time_only": True,
            "adapter_not_new_brain": True,
            "india_after_trust": True,
            "coverage_is_not_intelligence": True,
            "ananta_owns_candles": True,
            "agent_does_not_grow_a_private_market_db": True,
            "wave_a_frozen": True,
            "four_years_is_fuel_not_the_process": True,
        },
    }


def refuse_bulk_score(*, years: int = 4, assets: int = 10) -> Dict[str, Any]:
    return {
        "ok": False,
        "ran": False,
        "reason": "NO_RUN_EVERYTHING",
        "requested": {"years": years, "assets": assets},
        "keep": False,
        "note": "Pipeline v1 scores one named slice. Bulk dump is coverage theater.",
    }


def print_pipeline() -> Dict[str, Any]:
    report = spec()
    print(f"\nRESEARCH PIPELINE  {report['version']}")
    print("=" * 64)
    print("Process lock. Not a 4-year dump. Not KEEP. Not India ingest.")
    print(f"  now={report['years_now']}")
    print(f"  target={report['years_target']}")
    print("-" * 64)
    print("  " + " → ".join(report["stages"][:5]))
    print("  " + " → ".join(report["stages"][5:]))
    print("-" * 64)
    print("  ladder: " + " → ".join(report["ladder"]))
    print("  adapters:")
    for name, a in report["adapters"].items():
        print(f"    {name:<8} {a['status']:<14} now={a['now']}")
    print("-" * 64)
    print("  PIT at decision. Outcomes join after. No look-ahead features.")
    print("  Next slice = one offline cell. Wave A stays WATCH.")
    print("=" * 64)
    print()
    return report
