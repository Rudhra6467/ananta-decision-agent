"""Next T2 slice: BTC 15m historical book.

Live watch is already 15m (observation_log). That is T1, not this slice.
A hist 15m book needs Ananta observation-replay at 15m without overwriting
observation_replay.jsonl. If the API cannot do that, we do not invent bars.
"""
from __future__ import annotations

from typing import Any, Dict

VERSION = "SLICE-15M-v0"


def spec() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "live_enable": False,
        "wanted": {
            "symbol": "BTC/USD",
            "timeframe": "15m",
            "file": "observation_replay_BTCUSD_15m.jsonl",
            "must_not_touch": [
                "observation_replay.jsonl",
                "observation_log.jsonl",
            ],
        },
        "today": {
            "live_15m": "T1 observation_log.jsonl — already running",
            "hist_15m_book": "NOT_WIRED",
        },
        "gate": "Ananta lab replay must accept timeframe=15m and write a sibling file",
        "if_missing": "Do not downsample 1h into fake 15m. Leave NOT_WIRED.",
        "also_ok_instead": "one new strategy family on existing 1h books",
        "not_today": ["LINK", "XRP", "turtle live", "TREND_UP"],
    }


def print_slice() -> Dict[str, Any]:
    r = spec()
    print(f"\nT2 NEXT SLICE  {r['version']}")
    print("=" * 64)
    print("Hist BTC 15m book. Live 15m watch is T1 and already running.")
    print(f"  hist book: {r['today']['hist_15m_book']}")
    print(f"  gate: {r['gate']}")
    print("-" * 64)
    print(f"  want file: {r['wanted']['file']}")
    print("  must not touch BTC 1y or live log")
    print("-" * 64)
    print(f"  if missing: {r['if_missing']}")
    print("  alt: new family on 1h books already in memory")
    print("=" * 64)
    print()
    return r
