"""Four parallel tracks. Lab complete ≠ Ananta finished.

Data collection continuous. Research continuous.
Strategy discovery continuous. Opportunity discovery continuous.
Capital exposure gated.
"""
from __future__ import annotations

from typing import Any, Dict

VERSION = "TRACKS-v1.1"

TRACKS = {
    "T1_LIVE_VALIDATION": {
        "status": "RUNNING",
        "job": "lab watch 15 Wave A frozen",
        "is": "out-of-sample validation",
        "is_not": "the primary research engine",
    },
    "T2_HIST_UNIVERSE": {
        "status": "PAUSE_ASSETS",
        "job": "BTC + ETH + SOL 1h scored. SUITABLE=0 on all three.",
        "done": ["BTC/USD 1h", "ETH/USD 1h", "SOL/USD 1h"],
        "next": "do not add AVAX/turtle until a cell is SUITABLE or live DQ contradicts WASH",
        "not_next": ["AVAX", "turtle", "ema-cross", "4y dump", "live enable"],
    },
    "T3_INTELLIGENCE": {
        "status": "BASELINE",
        "job": "knowledge_grid.json + grid_cite. Queryable. Cite cannot TAKE.",
    },
    "T4_SCANNER_FV_DESIGN": {
        "status": "DESIGN_ONLY",
        "job": "T4-CONTRACT-v0. live_scan=False execute=False llm_price=False",
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
        "weekend_closed": True,
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
    print("  T2 assets paused. T3 cite works. T4 design only.")
    print("  KEEP / TREND_UP / I5 / I6 still gated.")
    print("=" * 64)
    print()
    return r
