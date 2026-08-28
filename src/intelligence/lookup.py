"""State lookup v0.1 — invert fingerprints + +1h TAKE vs sit-out.

Not similarity. Not KEEP. Counts ≠ edge.

CLI: lab lookup [UP|DOWN|FLAT|BULLISH|BEARISH|NEUTRAL]
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.intelligence.decision_quality import NOISE_PCT, evidence_depth, path_call
from src.intelligence.fingerprint import from_record
from src.intelligence.setup_memory import extract

VERSION = "LOOKUP-v0.1"
OUT = Path("state_lookup.json")
TREND_FLAGS = ("UP", "DOWN", "FLAT")
LABEL_FLAGS = ("BULLISH", "BEARISH", "NEUTRAL", "UNCLEAR")


def _mean(xs: List[float]) -> Optional[float]:
    return round(sum(xs) / len(xs), 4) if xs else None


def _flag_of(fp: dict, axis: str) -> str:
    if axis == "by_independent_label":
        return str(fp.get("independent_label") or "UNCLEAR")
    return str(fp.get("trend") or "UNKNOWN")


def lookup(flag: str = "UP", source: str = "replay") -> Dict[str, Any]:
    flag = (flag or "UP").upper().strip()
    axis = "by_trend"
    if flag in LABEL_FLAGS:
        axis = "by_independent_label"
    elif flag not in TREND_FLAGS:
        flag = "UP"
        axis = "by_trend"

    mem = extract(source)
    buckets: Dict[str, dict] = defaultdict(lambda: {
        "n": 0, "TAKE": 0, "COSTLY": 0, "PROTECTIVE": 0, "WASH": 0,
        "take_rets": [], "skip_rets": [],
    })
    for rec in mem.get("records") or []:
        fp = from_record(rec)
        if _flag_of(fp, axis) != flag:
            continue
        key = str(rec.get("strategy") or "?")
        b = buckets[key]
        b["n"] += 1
        role = rec.get("population_role")
        ret = (rec.get("outcomes") or {}).get("+1h")
        if role == "TAKE":
            b["TAKE"] += 1
            if isinstance(ret, (int, float)):
                b["take_rets"].append(float(ret))
        else:
            stamp = ((rec.get("refusal") or {}).get("+1h") or {}).get("stamp")
            if stamp in ("COSTLY", "PROTECTIVE", "WASH"):
                b[stamp] += 1
            if isinstance(ret, (int, float)):
                b["skip_rets"].append(float(ret))

    rows = []
    for key, b in buckets.items():
        n_take = int(b["TAKE"])
        take_mean = _mean(b["take_rets"])
        skip_mean = _mean(b["skip_rets"])
        take_call = path_call(take_mean, len(b["take_rets"]), usable=True, role="TAKE")
        skip_call = path_call(skip_mean, len(b["skip_rets"]), usable=True, role="SKIP")
        depth = evidence_depth(n_take, role="TAKE")
        vs = "NO_TAKE" if n_take <= 0 else take_call
        if n_take > 0 and take_call not in ("INSUFFICIENT_EVIDENCE", "NO_SAMPLE") and skip_mean is not None and take_mean is not None:
            delta = take_mean - skip_mean
            if abs(delta) < NOISE_PCT:
                vs = "WASH"
            elif delta >= NOISE_PCT:
                vs = "TAKE_GT_SITOUT"
            else:
                vs = "TAKE_LT_SITOUT"
        rows.append({
            "strategy": key,
            "flag": flag,
            "axis": axis,
            "n": b["n"],
            "TAKE": n_take,
            "COSTLY": b["COSTLY"],
            "PROTECTIVE": b["PROTECTIVE"],
            "WASH": b["WASH"],
            "depth": depth,
            "mean_1h_take": take_mean,
            "mean_1h_skip": skip_mean,
            "take_call": take_call,
            "skip_call": skip_call,
            "vs_sitout": vs,
            "keep": False,
            "live_enable": False,
        })
    rows.sort(key=lambda r: (-r["TAKE"], -r["n"], r["strategy"]))
    report = {
        "ok": True,
        "version": VERSION,
        "source": mem.get("source"),
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
            "take_gt_sitout_is_not_keep": True,
            "counts_are_not_edge": True,
        },
        "note": (
            "Inverted Market Truth + +1h TAKE vs skip on that flag. "
            "TAKE_GT_SITOUT is a finding, not KEEP. Hunter COSTLY on UP ≠ TREND_UP enable."
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
    print("Given this tape flag: counts AND +1h TAKE vs sit-out. Not KEEP.")
    print(f"  flag={report.get('flag')}  axis={report.get('axis')}  n={report.get('n_strategies')}  keep=False")
    print("-" * 64)
    rows = report.get("rows") or []
    if not rows:
        print("  (empty — UNKNOWN is valid)")
    for r in rows:
        mt = "—" if r.get("mean_1h_take") is None else f"{r['mean_1h_take']}%"
        ms = "—" if r.get("mean_1h_skip") is None else f"{r['mean_1h_skip']}%"
        print(
            f"  {r['strategy']:<18} n={r['n']:<5} TAKE={r['TAKE']:<4} "
            f"COSTLY={r['COSTLY']:<4} PROT={r['PROTECTIVE']:<4} WASH={r['WASH']}"
        )
        print(
            f"    {'':<18} depth={r.get('depth')}  +1h_TAKE={mt}  +1h_SKIP={ms}  "
            f"vs_sitout={r.get('vs_sitout')}"
        )
    print("-" * 64)
    print("  vs_sitout ≠ KEEP. COSTLY ≠ TREND_UP enable. Wave A stays WATCH.")
    if report.get("saved"):
        print(f"  saved: {report['saved']}")
    print("=" * 64)
    return report
