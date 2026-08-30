"""Four parallel tracks. T1 time-blocked. T2/T3/T4 offline. Capital gated."""
from __future__ import annotations

from typing import Any, Dict

VERSION = "TRACKS-v1.3"

TRACKS = {
    "T1_LIVE_VALIDATION": {
        "status": "RUNNING_FROZEN_RULES",
        "job": "lab watch 15. Do not contaminate.",
    },
    "T2_HIST_UNIVERSE": {
        "status": "PAUSE_1H_COINS",
        "job": "BTC ETH SOL AVAX 1h scored. First UNSUITABLE=Donchian AVAX UP.",
        "done": ["BTC/USD 1h", "ETH/USD 1h", "SOL/USD 1h", "AVAX/USD 1h"],
        "next": "BTC 15m book or one new family — not LINK/XRP today",
    },
    "T3_INTELLIGENCE": {
        "status": "DESK_PLUS_FINDINGS",
        "job": "grid + excursion + desk + findings.json",
    },
    "T4_SCANNER_FV": {
        "status": "SMA20_LIVE_ONLY",
        "job": "sma20_close PIT on live obs. vwap still PENDING. execute=False.",
    },
}


def spec() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "suitable": 0,
        "tracks": TRACKS,
        "law": "Discover offline. Capital waits on forward DQ.",
    }


def print_tracks() -> Dict[str, Any]:
    r = spec()
    print(f"\nPROJECT TRACKS  {r['version']}")
    print("=" * 64)
    print(r["law"])
    print("-" * 64)
    for k, t in r["tracks"].items():
        print(f"  {k:<22} {t.get('status'):<22} {t.get('job')}")
    print("-" * 64)
    print("  I5 blocked. KEEP false. LINK not today.")
    print("=" * 64)
    print()
    return r
