"""Findings card. Prefer knowledge_grid.json. Not KEEP."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

VERSION = "FINDINGS-v0.7"
GRID = Path("knowledge_grid.json")


def findings() -> Dict[str, Any]:
    if not GRID.exists():
        return {"ok": False, "reason": "NO_GRID", "keep": False}
    rows = json.loads(GRID.read_text()).get("rows") or []
    hurt: List[dict] = []
    for row in rows:
        for bk, c in (row.get("books") or {}).items():
            if c.get("missing"):
                continue
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
            "1h coverage set complete: 10 books.",
            "Donchian UP hurt on AVAX LINK ARB RENDER. WASH on ETH SOL XRP AAVE PAXG. Thin BTC.",
            "ATR UP hurt on AAVE and RENDER. Hunter UP NO_TAKE on all 10.",
            "Bollinger COMPRESSION WASH wherever ADEQUATE.",
            "4h observation-replay NOT_WIRED. Do not invent 4h from 1h.",
            "15m replay window = 15.5d (2026-08-14→30). year_pass n=161 = slice, not a year.",
            "usable_1y=False on 15m. max_bars=all will not invent 1.17y of 15m bars.",
            "3-4y candles NOT on Ananta (1.17y). SUITABLE=0. I5 blocked.",
        ],
        "do_not": [
            "rewrite Donchian or ATR",
            "enable TREND_UP",
            "KEEP any cell",
            "synthesize 4h from 1h",
            "treat 15m year_pass as a year book",
            "run 15m max_bars=all expecting 1.17y",
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
    print("10 × 1h + TF lock. 15m is a window, not a year. Not KEEP.")
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
