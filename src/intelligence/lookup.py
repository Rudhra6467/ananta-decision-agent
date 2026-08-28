"""State lookup v0 — invert fingerprints. Not similarity. Not KEEP.

Question: given this Market Truth flag, which capabilities have setups,
what were TAKE vs COSTLY/PROTECTIVE/WASH, how deep is that?

CLI: lab lookup [UP|DOWN|FLAT|BULLISH|BEARISH|NEUTRAL]
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.intelligence.fingerprint import fingerprints

VERSION = "LOOKUP-v0"
OUT = Path("state_lookup.json")
TREND_FLAGS = ("UP", "DOWN", "FLAT")
LABEL_FLAGS = ("BULLISH", "BEARISH", "NEUTRAL", "UNCLEAR")


def lookup(flag: str = "UP", source: str = "replay") -> Dict[str, Any]:
    flag = (flag or "UP").upper().strip()
    fp = fingerprints(source)
    axis = "by_trend"
    if flag in LABEL_FLAGS:
        axis = "by_independent_label"
    elif flag not in TREND_FLAGS:
        flag = "UP"
        axis = "by_trend"
    rows = []
    for key, sl in (fp.get("by_strategy") or {}).items():
        bucket = (sl.get(axis) or {}).get(flag) or {}
        n = int(bucket.get("n") or 0)
        if n <= 0:
            continue
        take = int(bucket.get("TAKE") or 0)
        rows.append({
            "strategy": key,
            "flag": flag,
            "axis": axis,
            "n": n,
            "TAKE": take,
            "COSTLY": int(bucket.get("COSTLY") or 0),
            "PROTECTIVE": int(bucket.get("PROTECTIVE") or 0),
            "WASH": int(bucket.get("WASH") or 0),
            "keep": False,
            "live_enable": False,
        })
    rows.sort(key=lambda r: (-r["TAKE"], -r["n"], r["strategy"]))
    report = {
        "ok": True,
        "version": VERSION,
        "source": fp.get("source"),
        "flag": flag,
        "axis": axis,
        "keep": False,
        "similarity": False,
        "ranker": False,
        "n_strategies": len(rows),
        "rows": rows,
        "laws": {
            "lookup_is_not_similarity": True,
            "lookup_is_not_keep": True,
            "empty_is_valid": True,
            "costly_is_not_enable": True,
        },
        "note": (
            "Inverted Market Truth. Not chart lookalike. "
            "A fat sample of a bad rule is still bad. Not KEEP."
        ),
    }
    try:
        OUT.write_text(json.dumps(report, indent=2, default=str))
        report["saved"] = str(OUT)
    except Exception:
        report["saved"] = None
    return report


def print_lookup(flag: str = "UP", source: str = "replay") -> Dict[str, Any]:
    report = lookup(flag, source)
    print(f"\nSTATE LOOKUP  {report.get('version')}  ({report.get('source')})")
    print("=" * 64)
    print("Given this tape flag, what did setups do? Not similarity. Not KEEP.")
    print(f"  flag={report.get('flag')}  axis={report.get('axis')}  n={report.get('n_strategies')}  keep=False")
    print("-" * 64)
    rows = report.get("rows") or []
    if not rows:
        print("  (empty — UNKNOWN is valid)")
    for r in rows:
        print(
            f"  {r['strategy']:<18} n={r['n']:<5} TAKE={r['TAKE']:<4} "
            f"COSTLY={r['COSTLY']:<4} PROT={r['PROTECTIVE']:<4} WASH={r['WASH']}"
        )
    print("-" * 64)
    print("  Lookup ≠ TAKE. COSTLY ≠ TREND_UP enable. Wave A stays WATCH.")
    if report.get("saved"):
        print(f"  saved: {report['saved']}")
    print("=" * 64)
    return report
