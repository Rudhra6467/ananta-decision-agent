"""BTC 15m hist slice. Smoke passed. Full 1y not earned."""
from __future__ import annotations

from typing import Any, Dict

VERSION = "SLICE-15M-v0.1"


def spec() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "smoke": {
            "ok": True,
            "file": "observation_replay_smoke_15m.jsonl",
            "n": 80,
            "span_days": 15.5,
            "usable_1y": False,
            "ananta_flag_15m": False,
            "btc_1h_untouched": True,
        },
        "full": {
            "status": "NOT_YET",
            "file": "observation_replay_BTCUSD_15m.jsonl",
            "why_wait": "smoke window is 15.5d not 1y; all-bars 15m is huge",
        },
        "do_not": [
            "downsample 1h into fake 15m",
            "run max_bars=all this session",
            "replace observation_replay.jsonl",
            "KEEP from 80-bar smoke",
        ],
    }


def print_slice() -> Dict[str, Any]:
    r = spec()
    print(f"\nT2 NEXT SLICE  {r['version']}")
    print("=" * 64)
    print("Smoke 15m OK. Not a 1y book. Not KEEP.")
    s = r["smoke"]
    print(f"  file={s['file']} n={s['n']} span={s['span_days']}d usable_1y={s['usable_1y']}")
    print(f"  Ananta has_15m flag={s['ananta_flag_15m']} (summary quirk — span is 15m density)")
    print("-" * 64)
    print(f"  full dump: {r['full']['status']}  {r['full']['why_wait']}")
    print("  do not: " + "; ".join(r["do_not"]))
    print("=" * 64)
    print()
    return r
