"""Findings card. What the desk already knows. Not KEEP. Not a rewrite."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

VERSION = "FINDINGS-v0.1"
DESK = Path("evidence_desk.json")


def findings() -> Dict[str, Any]:
    if not DESK.exists():
        return {"ok": False, "reason": "NO_DESK", "keep": False}
    data = json.loads(DESK.read_text())
    hurt: List[dict] = []
    wash: List[dict] = []
    no_take: List[dict] = []
    for row in data.get("rows") or []:
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
        "wash_adequate_or_labeled": wash,
        "no_take": no_take,
        "headline": [
            "Donchian × TREND_UP × AVAX 1h is TAKE_HURT / UNSUITABLE on this version.",
            "Hunter × TREND_UP is NO_TAKE on BTC ETH SOL AVAX. Not a TREND_UP enable.",
            "Bollinger × COMPRESSION is WASH where ADEQUATE. Not KEEP.",
            "BTC 15m smoke n=80 span=15.5d usable_1y=False. All cells UNKNOWN. Pipe works. Not a book.",
            "SUITABLE=0. I5 still blocked.",
        ],
        "do_not": [
            "rewrite Donchian because AVAX hurt",
            "enable TREND_UP",
            "add LINK today",
            "KEEP bollinger",
            "KEEP from 15m smoke",
            "run 15m max_bars=all this session",
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
    print("From evidence_desk.json + 15m smoke lock. Not KEEP.")
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
