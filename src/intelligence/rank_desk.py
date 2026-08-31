"""Rank capabilities from knowledge_grid.json for a tape flag. Not TAKE."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.intelligence.scan_candidates import _fp_from_obs, build as build_scan
from src.tools.observation_log import OBSERVATION_LOG, _read_jsonl

VERSION = "RANK-DESK-v0"
GRID = Path("knowledge_grid.json")
OUT = Path("rank_desk.json")

ORDER = {
    "TAKE_HURT": 0,
    "TAKE_LE_SITOUT": 1,
    "NO_TAKE": 2,
    "NO_SAMPLE": 3,
    "INSUFFICIENT_EVIDENCE": 4,
    "WASH": 5,
    "TAKE_GT_SITOUT": 6,
}


def _rows() -> List[dict]:
    if not GRID.exists():
        return []
    try:
        return json.loads(GRID.read_text()).get("rows") or []
    except Exception:
        return []


def rank_for(fp: str) -> Dict[str, Any]:
    parts = (fp or "").split("|")
    trend = parts[0] if parts else "UNKNOWN"
    comp = parts[1] if len(parts) > 1 else "UNKNOWN"
    unclear = "UNKNOWN" in fp
    issued = "UNKNOWN" if unclear else "WAIT"
    rows = _rows()
    ranked: List[dict] = []
    for row in rows:
        books = row.get("books") or {}
        present = {k: v for k, v in books.items() if not v.get("missing")}
        if not present:
            continue
        hurts = [k for k, v in present.items() if v.get("vs_sitout") == "TAKE_HURT"]
        washes = [k for k, v in present.items() if v.get("vs_sitout") == "WASH"]
        takes = sum(int(v.get("n_take") or 0) for v in present.values())
        worst = "NO_SAMPLE"
        for v in present.values():
            vs = v.get("vs_sitout") or "NO_SAMPLE"
            if ORDER.get(vs, 3) < ORDER.get(worst, 3):
                worst = vs
        ranked.append({
            "strategy": row.get("strategy"),
            "regime": row.get("regime"),
            "books_n": len(present),
            "n_take_sum": takes,
            "worst": worst,
            "hurt_books": hurts,
            "wash_books": washes,
            "keep": False,
        })
    ranked.sort(key=lambda x: (ORDER.get(x["worst"], 3), -x["n_take_sum"]))
    relevant = [
        x for x in ranked
        if (comp == "COMPRESSION" and x["regime"] == "COMPRESSION")
        or (trend == "UP" and x["regime"] == "TREND_UP")
        or (trend == "DOWN" and x["regime"] in ("TREND_DOWN", "COMPRESSION"))
        or x["regime"] in ("REVERSAL",)
    ] or ranked[:5]
    return {
        "ok": True,
        "version": VERSION,
        "fp": fp,
        "issued": issued,
        "why": "I2_BASELINE_NO_SUITABLE" if not unclear else "UNCLEAR_TAPE",
        "keep": False,
        "can_take": False,
        "rows": relevant,
        "tape_trend": trend,
        "tape_compression": comp,
    }


def print_rank_desk() -> Dict[str, Any]:
    rows = _read_jsonl(OBSERVATION_LOG) if OBSERVATION_LOG.exists() else []
    fp = _fp_from_obs(rows[-1]) if rows else "UNKNOWN|UNKNOWN|UNKNOWN|UNCLEAR"
    r = rank_for(fp)
    scan = build_scan()
    r["scan_issued"] = (scan.get("candidate") or {}).get("issued")
    OUT.write_text(json.dumps(r, indent=2, default=str))
    r["saved"] = str(OUT)
    print(f"\nRANK DESK  {r['version']}")
    print("=" * 64)
    print("10-book grid. Rank ≠ TAKE. Issued WAIT/UNKNOWN.")
    print(f"  fp={r.get('fp')}  issued={r.get('issued')}  why={r.get('why')}")
    print("-" * 64)
    for x in r.get("rows") or []:
        print(
            f"  {x['strategy']:<20} {x['regime']:<12} worst={x['worst']:<22} "
            f"hurt={x['hurt_books']} wash_n={len(x['wash_books'])}"
        )
    print("-" * 64)
    print("  I4 cannot TAKE. I5 blocked. Wave A stays WATCH.")
    print(f"  saved={r.get('saved')}  keep=False")
    print("=" * 64)
    print()
    return r
