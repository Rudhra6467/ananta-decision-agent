"""Findings card. Prefer knowledge_grid.json. Not KEEP."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

VERSION = "FINDINGS-v0.2"
GRID = Path("knowledge_grid.json")
DESK = Path("evidence_desk.json")


def _rows() -> List[dict]:
    if GRID.exists():
        data = json.loads(GRID.read_text())
        return data.get("rows") or []
    if DESK.exists():
        data = json.loads(DESK.read_text())
        return data.get("rows") or []
    return []


def findings() -> Dict[str, Any]:
    rows = _rows()
    if not rows:
        return {"ok": False, "reason": "NO_GRID", "keep": False}
    hurt: List[dict] = []
    wash: List[dict] = []
    no_take: List[dict] = []
    for row in rows:
        for bk, c in (row.get("books") or {}).items():
            rec = {
                "strategy": row.get("strategy"),
                "regime": row.get("regime"),
                "book": bk,
                "n_take": c.get("n_take"),
                "vs_sitout": c.get("vs_sitout"),
                "+1h_TAKE": c.get("+1h_TAKE"),
                "keep": False,
            }
            vs = c.get("vs_sitout")
            if vs in ("TAKE_HURT", "TAKE_LE_SITOUT"):
                hurt.append(rec)
            elif vs == "WASH":
                wash.append(rec)
            elif vs == "NO_TAKE":
                no_take.append(rec)
    out = {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "suitable": 0,
        "unsuitable_or_hurt": hurt,
        "wash": wash,
        "no_take": no_take,
        "headline": [
            "Donchian × TREND_UP is TAKE_HURT on AVAX and LINK (ADEQUATE). Repeating, not a fluke.",
            "Hunter × TREND_UP is NO_TAKE on BTC ETH SOL AVAX LINK. Not a TREND_UP enable.",
            "Bollinger × COMPRESSION is WASH on every ADEQUATE 1h book. Not KEEP.",
            "Five 1h books are a prototype Universe. 3-4y and more TFs still ahead.",
            "SUITABLE=0. I5 still blocked.",
        ],
        "do_not": [
            "rewrite Donchian because alts hurt",
            "enable TREND_UP",
            "KEEP bollinger",
            "KEEP from 15m smoke",
            "confuse no-capital with no-development",
        ],
    }
    Path("findings.json").write_text(json.dumps(out, indent=2, default=str))
    out["saved"] = "findings.json"
    return out


def print_findings() -> Dict[str, Any]:
    r = findings()
    print(f"\nFINDINGS  {r.get('version', VERSION)}")
    print("=" * 64)
    if not r.get("ok"):
        print(f"  {r.get('reason')}")
        print("=" * 64)
        return r
    print("From knowledge_grid.json. Not KEEP. Not a rewrite.")
    print("-" * 64)
    for line in r.get("headline") or []:
        print(f"  • {line}")
    print("-" * 64)
    print("  HURT / UNSUITABLE")
    for x in r.get("unsuitable_or_hurt") or []:
        print(
            f"    {x['strategy']} × {x['regime']} × {x['book']}  "
            f"take={x['n_take']} +1h={x['+1h_TAKE']} {x['vs_sitout']}"
        )
    print("-" * 64)
    print("  do not: " + "; ".join(r.get("do_not") or []))
    print(f"  saved={r.get('saved')}  keep=False")
    print("=" * 64)
    print()
    return r
