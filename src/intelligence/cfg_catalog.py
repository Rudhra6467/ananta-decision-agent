"""Named configuration budget. PENDING until replay can take config_id."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.intelligence.cfg_spec import COST, GENERATION

VERSION = "CFG-CAT-v0"
OUT = Path("cfg_catalog.json")
FAMILY = "donchian-breakout"
EXP_ID = "EXP-010"


def catalog() -> List[Dict[str, Any]]:
    rows = []
    for lb in GENERATION["donchian_v1_budget"]:
        n = int(lb.replace("lb", ""))
        rows.append({
            "exp_id": EXP_ID,
            "family": FAMILY,
            "config_id": f"donchian-{lb}-v1",
            "params": {"lookback": n},
            "split": "IN_SAMPLE",
            "status": "PENDING_REPLAY",
            "stage": "RESEARCH",
            "n_take_eq": None,
            "win_rate_after_cost": None,
            "expectancy_after_cost": None,
            "vs_sitout": "PENDING",
            "cost_version": COST["version"],
            "round_trip_pct": COST["default_round_trip_pct"],
            "promote": False,
            "keep": False,
            "blocked": "NO_PARAM_REPLAY — Ananta observation-replay uses stock Donchian",
        })
    return rows


def print_catalog() -> Dict[str, Any]:
    rows = catalog()
    out = {
        "ok": True,
        "version": VERSION,
        "exp_id": EXP_ID,
        "family": FAMILY,
        "budget": GENERATION["donchian_v1_budget"],
        "held_out_touches_search": False,
        "rows": rows,
        "keep": False,
        "next": "Wire Ananta replay params OR local PIT Donchian. Do not invent win rates.",
    }
    OUT.write_text(json.dumps(out, indent=2, default=str))
    out["saved"] = str(OUT)
    print(f"\nCFG CATALOG  {out['version']}  {EXP_ID}")
    print("=" * 64)
    print("Budgeted Donchian lookbacks. Held-out locked out of search.")
    print("-" * 64)
    for r in rows:
        print(f"  {r['config_id']:<22} lookback={r['params']['lookback']:<4} "
              f"{r['status']}  stage={r['stage']}")
    print("-" * 64)
    print("  No scores. Stock Donchian on the 10 books remains EXP-001.")
    print(f"  saved={out['saved']}  keep=False")
    print("=" * 64)
    print()
    return out
