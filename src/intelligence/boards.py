"""Contextual boards v0 — separate boards, not a blended ranker.

SUITABLE / UNSUITABLE / WASH / UNKNOWN.
Empty SUITABLE is a valid result. Board ≠ KEEP. Board ≠ live enable.

CLI: lab boards
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict

from src.intelligence.universe import research as universe_research

VERSION = "BOARDS-v0"
OUT = Path("strategy_boards.json")
ORDER = ("SUITABLE", "UNSUITABLE", "WASH", "TESTED_UNKNOWN", "UNTESTED")


def boards() -> Dict[str, Any]:
    uni = universe_research()
    buckets: Dict[str, list] = defaultdict(list)
    for c in uni.get("cells") or []:
        if c.get("coverage") != "historical_lab":
            if c.get("status_class") == "UNTESTED":
                continue
        status = c.get("status_class") or "UNTESTED"
        if int(c.get("n_take") or 0) == 0 and status == "TESTED_UNKNOWN":
            # idle UNMAPPED cells clutter the board — keep thesis/allowed only
            if c.get("policy") not in ("ALLOWED", "ROUTER_ONLY", "THESIS_ONLY"):
                continue
            if int(c.get("n_setup") or 0) == 0:
                continue
        buckets[status].append({
            "strategy": c.get("strategy"),
            "regime": c.get("regime"),
            "policy": c.get("policy"),
            "n_take": c.get("n_take"),
            "n_setup": c.get("n_setup"),
            "depth": c.get("evidence_depth"),
            "plus_1h": (c.get("take_1h") or {}).get("verdict"),
            "fit": c.get("fit"),
            "clash": (c.get("regime_vs_tape") or {}).get("clash"),
            "keep": False,
        })
    report = {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "ranker": False,
        "blended_score": None,
        "live_watch_frozen": True,
        "n_suitable": len(buckets.get("SUITABLE") or []),
        "n_unsuitable": len(buckets.get("UNSUITABLE") or []),
        "boards": {k: buckets.get(k) or [] for k in ORDER},
        "laws": {
            "empty_suitable_is_valid": True,
            "board_is_not_keep": True,
            "board_is_not_a_score": True,
            "unknown_is_valid": True,
        },
        "note": "Separate boards. No 81/100. Empty SUITABLE means authority not earned.",
    }
    try:
        OUT.write_text(json.dumps(report, indent=2, default=str))
        report["saved"] = str(OUT)
    except Exception:
        report["saved"] = None
    return report


def print_boards() -> Dict[str, Any]:
    report = boards()
    print(f"\nSTRATEGY BOARDS  {report.get('version')}")
    print("=" * 64)
    print("Separate boards. Not a ranker. Not KEEP. Empty SUITABLE is honest.")
    print(f"  SUITABLE={report.get('n_suitable')}  UNSUITABLE={report.get('n_unsuitable')}  keep=False")
    print("-" * 64)
    for name in ORDER:
        rows = (report.get("boards") or {}).get(name) or []
        print(f"  {name}  n={len(rows)}")
        if not rows:
            print("    (empty)")
            continue
        for r in sorted(rows, key=lambda x: (-int(x.get("n_take") or 0), x.get("strategy") or "")):
            print(
                f"    {r.get('strategy'):<18} {r.get('regime'):<12} "
                f"take={r.get('n_take')}  depth={r.get('depth') or 'NONE'}  "
                f"+1h={r.get('plus_1h') or '—'}  clash={r.get('clash')}"
            )
    print("-" * 64)
    print("  Board membership ≠ KEEP. SUITABLE ≠ trade. Wave A stays WATCH.")
    if report.get("saved"):
        print(f"  saved: {report['saved']}")
    print("=" * 64)
    return report
