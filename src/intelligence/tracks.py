"""Four parallel tracks. Lab complete ≠ Ananta finished.

Data collection continuous. Research continuous.
Strategy discovery continuous. Opportunity discovery continuous.
Capital exposure gated.
"""
from __future__ import annotations

from typing import Any, Dict

VERSION = "TRACKS-v1"

TRACKS = {
    "T1_LIVE_VALIDATION": {
        "status": "RUNNING",
        "job": "lab watch 15 Wave A frozen",
        "is": "out-of-sample validation",
        "is_not": "the primary research engine",
        "asks": [
            "Do states recur?",
            "Does hist behaviour survive?",
            "Are WAIT/SKIP useful?",
            "Does TAKE beat sit-out if it ever appears?",
            "Do rankings hold on new tape?",
        ],
    },
    "T2_HIST_UNIVERSE": {
        "status": "ACTIVE",
        "job": "one controlled slice at a time through PIPELINE-v1",
        "done": ["BTC/USD 1h", "ETH/USD 1h"],
        "next": "SOL/USD 1h existing specs only",
        "not_next": ["turtle", "ema-cross", "supertrend", "4y dump", "live enable"],
        "goal": "25+ research hypotheses, not 25 live bots",
    },
    "T3_INTELLIGENCE": {
        "status": "BUILD",
        "job": "contextual knowledge objects the agent can query",
        "shape": "state × strategy × n × outcome × risk × regime × recency × DQ",
        "not_shape": "one blended 87/100 score",
        "filters": "P1 market state + P2 capability evidence + veto-only",
    },
    "T4_SCANNER_FV_DESIGN": {
        "status": "DESIGN_ONLY",
        "job": "contracts for continuous scan + fair value",
        "scanner_says": "something interesting is happening",
        "fv_says": "price vs estimate with uncertainty",
        "neither_says": "BUY",
        "live_scan": False,
        "execute": False,
        "llm_price": False,
    },
}

LAW = (
    "Data collection is continuous. Research is continuous. "
    "Strategy discovery is continuous. Opportunity discovery is continuous. "
    "Capital exposure is gated."
)


def spec() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "lab_feature_complete": True,
        "ananta_finished": False,
        "tracks": TRACKS,
        "law": LAW,
        "ladder": [
            "controlled slice hist",
            "knowledge tables",
            "scanner/FV design",
            "human-gated paper",
            "forward DQ",
            "SAFE then MODERATE then AGGRESSIVE autonomy",
            "KEEP only after evidence",
        ],
    }


def print_tracks() -> Dict[str, Any]:
    r = spec()
    print(f"\nPROJECT TRACKS  {r['version']}")
    print("=" * 64)
    print("Lab feature-complete ≠ Ananta finished.")
    print(f"  {r['law']}")
    print("-" * 64)
    for k, t in r["tracks"].items():
        print(f"  {k:<22} {t.get('status'):<14} {t.get('job')}")
    print("-" * 64)
    print("  NEXT hist slice = SOL/USD 1h existing specs. Not turtle. Not live.")
    print("  KEEP / TREND_UP / I5 / I6 still gated.")
    print("=" * 64)
    print()
    return r
