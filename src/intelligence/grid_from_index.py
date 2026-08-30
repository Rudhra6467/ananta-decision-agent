"""Build the knowledge grid from saved memory indices. Fast."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.intelligence.decision_quality import NOISE_PCT, evidence_depth, score_horizon

VERSION = "GRID-INDEX-v0"
CELLS: List[Tuple[str, str]] = [
    ("donchian-breakout", "TREND_UP"),
    ("atr-breakout", "TREND_UP"),
    ("keltner-breakout", "TREND_UP"),
    ("bollinger-mr", "COMPRESSION"),
    ("hunter", "TREND_UP"),
]
BOOKS = [
    ("BTC", Path("setup_memory_index.json")),
    ("ETH", Path("setup_memory_index_eth.json")),
    ("SOL", Path("setup_memory_index_sol.json")),
    ("AVAX", Path("setup_memory_index_avax.json")),
    ("LINK", Path("setup_memory_index_link.json")),
    ("XRP", Path("setup_memory_index_xrp.json")),
    ("AAVE", Path("setup_memory_index_aave.json")),
]


def _load(p: Path) -> dict:
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def _cell(mem: dict, strategy: str, regime: str) -> dict:
    for c in (mem.get("by_cell") or {}).values():
        if c.get("strategy") == strategy and str(c.get("regime") or "").upper() == regime:
            return c
    return {"n": 0, "n_take": 0, "mean_1h_take": None, "mean_1h_skip_setup": None}


def vs_sitout(take_n: int, take_mean: Optional[float], skip_mean: Optional[float]) -> str:
    if take_n <= 0:
        return "NO_TAKE"
    take_call = score_horizon(role="TAKE", n=take_n, mean=take_mean, clock="+1h")
    verdict = take_call.get("verdict") or "INSUFFICIENT_EVIDENCE"
    if verdict in ("INSUFFICIENT_EVIDENCE", "NO_SAMPLE"):
        return verdict
    if take_mean is None:
        return "NO_SAMPLE"
    if skip_mean is None:
        return verdict
    delta = float(take_mean) - float(skip_mean)
    if abs(delta) < NOISE_PCT:
        return "WASH"
    if delta > 0:
        return "TAKE_GT_SITOUT"
    return "TAKE_HURT" if take_mean < 0 else "TAKE_LE_SITOUT"


def grid_from_index() -> Dict[str, Any]:
    mems = [(name, _load(p)) for name, p in BOOKS]
    rows = []
    for strategy, regime in CELLS:
        entry = {"strategy": strategy, "regime": regime, "books": {}, "keep": False}
        for name, mem in mems:
            c = _cell(mem, strategy, regime)
            n_take = int(c.get("n_take") or 0)
            take_m = c.get("mean_1h_take")
            vs = vs_sitout(n_take, take_m, c.get("mean_1h_skip_setup"))
            entry["books"][name] = {
                "n": c.get("n") or 0,
                "n_take": n_take,
                "depth": evidence_depth(n_take, role="TAKE"),
                "+1h_TAKE": take_m,
                "vs_sitout": vs,
                "missing": not bool(mem),
            }
        rows.append(entry)
    out = {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "suitable": 0,
        "rows": rows,
        "note": "From memory indices. No jsonl rescan.",
    }
    Path("knowledge_grid.json").write_text(json.dumps(out, indent=2, default=str))
    out["saved"] = "knowledge_grid.json"
    return out


def print_grid_index() -> Dict[str, Any]:
    r = grid_from_index()
    print(f"\nKNOWLEDGE GRID  {r['version']}")
    print("=" * 88)
    print("7 books from indices. Fast. SUITABLE is not KEEP.")
    print("-" * 88)
    for row in r["rows"]:
        label = f"{row['strategy']} × {row['regime']}"
        first = True
        for bk, c in (row.get("books") or {}).items():
            miss = " MISSING" if c.get("missing") else ""
            print(
                f"  {(label if first else ''):<32} {bk:<5} take={c['n_take']:<4} "
                f"{c['vs_sitout']}{miss}"
            )
            first = False
        print()
    print(f"  saved={r['saved']}  keep=False")
    print("=" * 88)
    print()
    return r
