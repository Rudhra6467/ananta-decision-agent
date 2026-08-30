"""Four tracks. No capital ≠ no development. Progressive T2 coverage."""
from __future__ import annotations

from typing import Any, Dict

VERSION = "TRACKS-v1.4"

VISION = (
    "Give Ananta a growing empirical model of markets, strategies, states, "
    "opportunities and outcomes. Discover what repeatedly works and fails. "
    "Act only when evidence justifies it."
)

LAW = (
    "Aggressive discovery. Conservative capital. Continuous learning. "
    "Explicit uncertainty. No authority from architecture alone."
)

TRACKS = {
    "T1_LIVE_VALIDATION": {
        "status": "RUNNING_FROZEN_RULES",
        "job": "lab watch 15. Validate. Do not contaminate Wave A.",
    },
    "T2_HIST_UNIVERSE": {
        "status": "EXPANDING",
        "job": "Prototype process exists. Universe is not finished. Next 1h book = LINK.",
        "done": ["BTC/USD 1h", "ETH/USD 1h", "SOL/USD 1h", "AVAX/USD 1h", "15m smoke only"],
        "next": ["LINK/USD 1h", "XRP/USD 1h", "budgeted BTC 15m 1y", "4h", "3-4y if PIT clean"],
        "not_final": "4 coins × 1h is a prototype of the process, not the Universe.",
    },
    "T3_INTELLIGENCE": {
        "status": "DESK_PLUS_FINDINGS",
        "job": "Searchable evidence. UNKNOWN/WASH/UNSUITABLE stay first-class.",
    },
    "T4_SCANNER_FV": {
        "status": "SMA_AND_VWAP_NOW",
        "job": "Named PIT methods. execute=False. Scanner still interface.",
    },
}


def spec() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "suitable": 0,
        "i5": False,
        "vision": VISION,
        "law": LAW,
        "tracks": TRACKS,
        "years_objective": "3-4y remains on the roadmap if candles stay PIT-clean",
        "do_not_confuse": "no capital authority ≠ no development",
    }


def print_tracks() -> Dict[str, Any]:
    r = spec()
    print(f"\nPROJECT TRACKS  {r['version']}")
    print("=" * 64)
    print(r["law"])
    print(r["vision"])
    print("-" * 64)
    for k, t in r["tracks"].items():
        print(f"  {k:<22} {t.get('status'):<22} {t.get('job')}")
    print("-" * 64)
    print("  T2 next: LINK 1h sibling file. SUITABLE is not KEEP.")
    print("  3-4y still on the map. I5 still closed.")
    print("=" * 64)
    print()
    return r
