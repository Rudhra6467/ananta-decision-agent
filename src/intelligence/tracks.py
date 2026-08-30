"""Four parallel tracks.

T1 is time-blocked. T2/T3/T4 are not. Capital authority is.
"""
from __future__ import annotations

from typing import Any, Dict

VERSION = "TRACKS-v1.2"

TRACKS = {
    "T1_LIVE_VALIDATION": {
        "status": "RUNNING_FROZEN_RULES",
        "job": "lab watch 15. Needs time. Do not contaminate.",
    },
    "T2_HIST_UNIVERSE": {
        "status": "OFFLINE_ACTIVE",
        "job": "BTC+ETH+SOL 1h done. Next slice = one TF or one family or one asset, not all three.",
        "done": ["BTC/USD 1h", "ETH/USD 1h", "SOL/USD 1h"],
    },
    "T3_INTELLIGENCE": {
        "status": "OFFLINE_ACTIVE",
        "job": "grid + cite + excursion-v0 (MFE/MAE proxy). Next: richer fingerprints / hist vs live.",
    },
    "T4_SCANNER_FV": {
        "status": "DESIGN_PLUS_INTERFACE",
        "job": "contracts exist. Next: named FV estimator interface, still execute=False.",
    },
}

LAW = (
    "Unfinished intelligence can be researched offline. "
    "Nothing earns capital authority until forward DQ proves it."
)
NORTH_STAR = (
    "Not wait-until-I5. Build the machine; evidence grants authority."
)


def spec() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "ananta_finished": False,
        "tracks": TRACKS,
        "law": LAW,
        "north_star": NORTH_STAR,
        "capital_gated": ["I5", "I6", "KEEP", "TREND_UP", "live scanner", "FV execute"],
        "offline_open": ["T2 slices", "T3 tables", "T4 interfaces"],
    }


def print_tracks() -> Dict[str, Any]:
    r = spec()
    print(f"\nPROJECT TRACKS  {r['version']}")
    print("=" * 64)
    print(r["north_star"])
    print(f"  {r['law']}")
    print("-" * 64)
    for k, t in r["tracks"].items():
        print(f"  {k:<22} {t.get('status'):<24} {t.get('job')}")
    print("-" * 64)
    print("  capital gated: I5 I6 KEEP TREND_UP live-scan FV-execute")
    print("=" * 64)
    print()
    return r
