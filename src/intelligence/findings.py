"""Findings card. Prefer knowledge_grid.json. Not KEEP."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

VERSION = "FINDINGS-v0.4"
GRID = Path("knowledge_grid.json")


def findings() -> Dict[str, Any]:
    if not GRID.exists():
        return {"ok": False, "reason": "NO_GRID", "keep": False}
    rows = json.loads(GRID.read_text()).get("rows") or []
    hurt: List[dict] = []
    for row in rows:
        for bk, c in (row.get("books") or {}).items():
            if c.get("vs_sitout") in ("TAKE_HURT", "TAKE_LE_SITOUT"):
                hurt.append({
                    "strategy": row.get("strategy"),
                    "regime": row.get("regime"),
                    "book": bk,
                    "n_take": c.get("n_take"),
                    "vs_sitout": c.get("vs_sitout"),
                    "+1h_TAKE": c.get("+1h_TAKE"),
                    "keep": False,
                })
    out = {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "suitable": 0,
        "unsuitable_or_hurt": hurt,
        "headline": [
            "Donchian × TREND_UP: TAKE_HURT AVAX/LINK; WASH ETH/SOL/XRP/AAVE; thin BTC.",
            "ATR × TREND_UP: TAKE_HURT AAVE ADEQUATE. First ATR unsuitable cell.",
            "Hunter × TREND_UP: NO_TAKE on all 7 books. Not a TREND_UP enable.",
            "Bollinger × COMPRESSION: WASH on every ADEQUATE 1h book.",
            "7 × 1h books = still a prototype. Next PAXG. Then 4h / years.",
            "SUITABLE=0. I5 blocked.",
        ],
        "do_not": [
            "rewrite Donchian or ATR",
            "enable TREND_UP",
            "KEEP any Wave A or I2 shadow",
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
    print("From knowledge_grid.json. Asset-conditional. Not KEEP.")
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
