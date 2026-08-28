"""Live vs hist sit-out — Wave A WAIT/SKIP opportunity cost.

Live TAKE=0 is WATCH, not a missing collector. The live sample we have
is SKIP/WAIT. Compare that to historical sit-out. Not KEEP.

CLI: lab sitout
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from src.intelligence.decision_quality import meter
from src.intelligence.laws import LAWS
from src.intelligence.schema import WAVE_A

VERSION = "SITOUT-v0"
OUT = Path("sitout_report.json")


def sitout() -> Dict[str, Any]:
    m = meter()
    rows = []
    for s in m.get("strategies") or []:
        live = s.get("live") or {}
        hist = s.get("historical") or {}
        lc = live.get("cells") or {}
        hc = hist.get("cells") or {}
        rows.append({
            "strategy": s.get("strategy"),
            "live_take": live.get("n_take"),
            "live_wait_1h": (lc.get("WAIT") or {}).get("+1h"),
            "live_skip_setup_1h": (lc.get("SKIP_SETUP") or {}).get("+1h"),
            "hist_take": hist.get("n_take"),
            "hist_wait_1h": (hc.get("WAIT") or {}).get("+1h"),
            "hist_skip_setup_1h": (hc.get("SKIP_SETUP") or {}).get("+1h"),
            "keep": False,
        })
    live_take = sum(int(r.get("live_take") or 0) for r in rows)
    report = {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "wave_a": list(WAVE_A),
        "live_take_n": live_take,
        "live_take_zero_means": "WAVE_A_WATCH",
        "rows": rows,
        "laws": {
            **{k: LAWS[k] for k in (
                "take_is_not_keep",
                "live_take_zero_is_watch_not_gap",
                "wait_is_a_decision",
                "skip_is_a_decision",
                "wave_a_watch",
            )},
        },
        "note": (
            "Sit-out is the live DQ sample while WATCH holds. "
            "Do not enable TREND_UP to manufacture live TAKEs. KEEP=False."
        ),
    }
    try:
        OUT.write_text(json.dumps(report, indent=2, default=str))
        report["saved"] = str(OUT)
    except Exception:
        report["saved"] = None
    return report


def print_sitout() -> Dict[str, Any]:
    report = sitout()
    print(f"\nSIT-OUT  {report.get('version')}  (Wave A live vs hist)")
    print("=" * 64)
    print("WAIT/SKIP opportunity cost. Live TAKE=0 is WATCH, not a gap. Not KEEP.")
    print(f"  live_TAKE={report.get('live_take_n')}  means={report.get('live_take_zero_means')}  keep=False")
    print("-" * 64)
    for r in report.get("rows") or []:
        lw = r.get("live_wait_1h") or {}
        ls = r.get("live_skip_setup_1h") or {}
        hw = r.get("hist_wait_1h") or {}
        hs = r.get("hist_skip_setup_1h") or {}
        print(f"  {r.get('strategy')}")
        print(
            f"    live  TAKE={r.get('live_take')}  "
            f"WAIT +1h n={lw.get('n')} {lw.get('verdict')} mean={lw.get('mean_pct')}  "
            f"SKIP_SETUP +1h n={ls.get('n')} {ls.get('verdict')} mean={ls.get('mean_pct')}"
        )
        print(
            f"    hist  TAKE-eq={r.get('hist_take')}  "
            f"WAIT +1h n={hw.get('n')} {hw.get('verdict')} mean={hw.get('mean_pct')}  "
            f"SKIP_SETUP +1h n={hs.get('n')} {hs.get('verdict')} mean={hs.get('mean_pct')}"
        )
    print("-" * 64)
    print("  TAKE ≠ KEEP. Hist TAKE-eq ≠ live TAKE. Do not enable TREND_UP to fill TAKE n.")
    if report.get("saved"):
        print(f"  saved: {report['saved']}")
    print("=" * 64)
    return report
