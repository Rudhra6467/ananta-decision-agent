"""I2 breakout hist baseline — locked 2026-08-28.

Every vs_sitout on UP/DOWN is INSUFFICIENT_EVIDENCE or WASH.
Donchian/Keltner/ATR TAKE point estimates on UP are ≤ sit-out.
Bollinger DOWN is ADEQUATE WASH.

Do not add turtle/ema. Do not KEEP. Do not TREND_UP enable.
Live Wave A watch continues as the other track.

CLI: lab baseline
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from src.intelligence.boards import boards
from src.intelligence.lookup import lookup

VERSION = "I2-BASELINE-v0"
OUT = Path("i2_baseline.json")
I2_FAMILIES = ("donchian-breakout", "atr-breakout", "keltner-breakout")
DO_NOT_ADD = ("turtle", "ema-cross", "supertrend", "macd-trend")


def snapshot() -> Dict[str, Any]:
    up = lookup("UP")
    down = lookup("DOWN")
    b = boards()
    up_rows = {r["strategy"]: r for r in (up.get("rows") or [])}
    down_rows = {r["strategy"]: r for r in (down.get("rows") or [])}
    vs = []
    for key, r in list(up_rows.items()) + list(down_rows.items()):
        vs.append(r.get("vs_sitout"))
    earned = any(x in ("TAKE_GT_SITOUT",) for x in vs)
    suitable_n = int(b.get("n_suitable") or 0)
    report = {
        "ok": True,
        "version": VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "locked": True,
        "keep": False,
        "live_enable": False,
        "trend_up_enable": False,
        "hunter_rewrite": False,
        "i2_families": list(I2_FAMILIES),
        "do_not_add_yet": list(DO_NOT_ADD),
        "n_suitable": suitable_n,
        "authority_earned": False,
        "up": {
            k: {
                "TAKE": r.get("TAKE"),
                "depth": r.get("depth"),
                "mean_1h_take": r.get("mean_1h_take"),
                "mean_1h_skip": r.get("mean_1h_skip"),
                "vs_sitout": r.get("vs_sitout"),
            }
            for k, r in up_rows.items()
        },
        "down": {
            k: {
                "TAKE": r.get("TAKE"),
                "depth": r.get("depth"),
                "mean_1h_take": r.get("mean_1h_take"),
                "mean_1h_skip": r.get("mean_1h_skip"),
                "vs_sitout": r.get("vs_sitout"),
            }
            for k, r in down_rows.items()
        },
        "findings": [
            "Donchian/Keltner aligned to SMA-20 UP. Coherent. TAKE n THIN. +1h TAKE ≤ sit-out.",
            "ATR UP TAKE n=9 ANECDOTE. +1h TAKE ≤ sit-out.",
            "Bollinger DOWN ADEQUATE +1h WASH. Sit-out not worse.",
            "Hunter UP TAKE=0. COSTLY skip ≠ TREND_UP enable.",
            "Hunter DOWN TAKE=4 ANECDOTE (REVERSAL). Not a rewrite.",
            "Continuation TREND_UP vs independent DOWN remains a named clash.",
            "SUITABLE=0. Authority not earned.",
        ],
        "next": [
            "Leave lab watch 15 running (Wave A live tape).",
            "Do not add turtle/ema/supertrend to hist shadow.",
            "Do not KEEP / TREND_UP / Hunter rewrite.",
            "Re-open I2 expansion only if a cell becomes SUITABLE or live DQ contradicts hist WASH.",
        ],
        "laws": {
            "i2_hist_baseline_locked": True,
            "coverage_is_not_intelligence": True,
            "insufficient_is_valid": True,
            "wash_is_not_unsuitable": True,
            "take_gt_sitout_is_not_keep": True,
            "point_estimate_is_not_edge": True,
        },
        "point_estimates_negative_on_up": True,
        "any_take_gt_sitout": earned,
        "note": "Locked hist baseline. Empty SUITABLE is the result. Not a pause in Wave A live collection.",
    }
    try:
        OUT.write_text(json.dumps(report, indent=2, default=str))
        report["saved"] = str(OUT)
    except Exception:
        report["saved"] = None
    return report


def print_baseline() -> Dict[str, Any]:
    report = snapshot()
    print(f"\nI2 HIST BASELINE  {report.get('version')}")
    print("=" * 64)
    print("Locked. Not KEEP. Not a new family. Wave A live watch continues.")
    print(
        f"  locked={report.get('locked')}  SUITABLE={report.get('n_suitable')}  "
        f"authority={report.get('authority_earned')}  keep=False"
    )
    print("-" * 64)
    print("  FINDINGS")
    for line in report.get("findings") or []:
        print(f"    - {line}")
    print("-" * 64)
    print("  NEXT")
    for line in report.get("next") or []:
        print(f"    - {line}")
    print("-" * 64)
    print("  do_not_add_yet:", ", ".join(report.get("do_not_add_yet") or []))
    if report.get("saved"):
        print(f"  saved: {report['saved']}")
    print("=" * 64)
    return report
