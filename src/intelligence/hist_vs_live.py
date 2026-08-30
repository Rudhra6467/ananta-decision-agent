"""Wave A hist books vs live watch. Not KEEP. Live TAKE=0 is WATCH."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.intelligence.setup_memory import extract

VERSION = "HVL-v0"
WAVE = ("hunter", "squeeze", "bollinger-mr")


def _cell(mem: dict, strategy: str) -> dict:
    n = n_take = n_skip = 0
    take_sum = skip_sum = 0.0
    n_tm = n_sm = 0
    for rec in mem.get("records") or []:
        if rec.get("strategy") != strategy:
            continue
        n += 1
        ret = (rec.get("outcomes") or {}).get("+1h")
        role = rec.get("population_role")
        if role == "TAKE":
            n_take += 1
            if isinstance(ret, (int, float)):
                take_sum += float(ret)
                n_tm += 1
        elif role == "SKIP_SETUP":
            n_skip += 1
            if isinstance(ret, (int, float)):
                skip_sum += float(ret)
                n_sm += 1
    return {
        "n": n,
        "n_take": n_take,
        "n_skip": n_skip,
        "+1h_TAKE": round(take_sum / n_tm, 4) if n_tm else None,
        "+1h_SKIP": round(skip_sum / n_sm, 4) if n_sm else None,
    }


def report() -> Dict[str, Any]:
    live = extract("live")
    btc = extract("replay")
    rows = []
    for s in WAVE:
        rows.append({
            "strategy": s,
            "live": _cell(live, s),
            "hist_btc": _cell(btc, s),
            "keep": False,
        })
    out = {
        "ok": True,
        "version": VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "live_take_zero_means": "WAVE_A_WATCH",
        "keep": False,
        "rows": rows,
    }
    Path("hist_vs_live.json").write_text(json.dumps(out, indent=2, default=str))
    out["saved"] = "hist_vs_live.json"
    return out


def print_hvl() -> Dict[str, Any]:
    r = report()
    print(f"\nHIST VS LIVE  {r['version']}")
    print("=" * 72)
    print("Wave A only. Live TAKE=0 is WATCH. Not KEEP.")
    print("-" * 72)
    print(f"  {'strategy':<14} {'src':<8} {'n':>5} {'take':>5} {'+1h TAKE':>10} {'+1h SKIP':>10}")
    print("-" * 72)
    for row in r["rows"]:
        first = True
        for src, key in (("live", "live"), ("histBTC", "hist_btc")):
            c = row[key]
            print(
                f"  {(row['strategy'] if first else ''):<14} {src:<8} "
                f"{c['n']:>5} {c['n_take']:>5} "
                f"{str(c['+1h_TAKE'] if c['+1h_TAKE'] is not None else '—'):>10} "
                f"{str(c['+1h_SKIP'] if c['+1h_SKIP'] is not None else '—'):>10}"
            )
            first = False
        print()
    print("-" * 72)
    print(f"  saved={r['saved']}  keep=False")
    print("=" * 72)
    print()
    return r
