"""Cross-book knowledge grid. Agent reads this instead of three jsonl files.

CLI: python -c "from src.intelligence.knowledge_grid import print_grid; print_grid()"
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.intelligence.decision_quality import NOISE_PCT, evidence_depth, score_horizon
from src.intelligence.setup_memory import extract

VERSION = "GRID-v0"
BOOKS = ("replay", "eth", "sol")
BOOK_LABEL = {"replay": "BTC", "eth": "ETH", "sol": "SOL"}

CELLS: List[Tuple[str, str]] = [
    ("donchian-breakout", "TREND_UP"),
    ("keltner-breakout", "TREND_UP"),
    ("atr-breakout", "TREND_UP"),
    ("bollinger-mr", "COMPRESSION"),
    ("bollinger-mr", "RANGE"),
    ("continuation", "TREND_UP"),
    ("hunter", "REVERSAL"),
    ("hunter", "TREND_UP"),
    ("squeeze", "COMPRESSION"),
]


def _cell(mem: dict, strategy: str, regime: str) -> dict:
    for c in (mem.get("by_cell") or {}).values():
        if c.get("strategy") == strategy and str(c.get("regime") or "").upper() == regime:
            return c
    return {
        "n": 0, "n_take": 0, "n_skip_setup": 0,
        "mean_1h_take": None, "mean_1h_skip_setup": None, "take_depth": "NONE",
    }


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
    return "TAKE_LE_SITOUT"


def grid() -> Dict[str, Any]:
    mems = {b: extract(b) for b in BOOKS}
    rows = []
    for strategy, regime in CELLS:
        entry = {"strategy": strategy, "regime": regime, "timeframe": "1h", "keep": False, "books": {}}
        for b in BOOKS:
            c = _cell(mems[b], strategy, regime)
            n_take = int(c.get("n_take") or 0)
            take_m = c.get("mean_1h_take")
            skip_m = c.get("mean_1h_skip_setup")
            entry["books"][BOOK_LABEL[b]] = {
                "n": c.get("n") or 0,
                "n_take": n_take,
                "n_skip": c.get("n_skip_setup") or 0,
                "depth": evidence_depth(n_take, role="TAKE"),
                "+1h_TAKE": take_m,
                "+1h_SKIP": skip_m,
                "vs_sitout": vs_sitout(n_take, take_m, skip_m),
            }
        rows.append(entry)
    report = {
        "ok": True,
        "version": VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "keep": False,
        "suitable": 0,
        "rows": rows,
        "note": "Queryable memory. WASH/UNKNOWN first-class. Not a ranker.",
    }
    Path("knowledge_grid.json").write_text(json.dumps(report, indent=2, default=str))
    report["saved"] = "knowledge_grid.json"
    return report


def print_grid() -> Dict[str, Any]:
    report = grid()
    print(f"\nKNOWLEDGE GRID  {report['version']}")
    print("=" * 88)
    print("cell × BTC/ETH/SOL. Queryable. SUITABLE is not KEEP.")
    print("-" * 88)
    print(f"  {'cell':<32} {'bk':<4} {'n':>4} {'take':>4} {'depth':<10} {'+1h TAKE':>10} {'vs sit-out'}")
    print("-" * 88)
    for row in report["rows"]:
        label = f"{row['strategy']} × {row['regime']}"
        first = True
        for bk in ("BTC", "ETH", "SOL"):
            c = row["books"][bk]
            print(
                f"  {(label if first else ''):<32} {bk:<4} {c['n']:>4} {c['n_take']:>4} "
                f"{str(c['depth']):<10} {str(c['+1h_TAKE'] if c['+1h_TAKE'] is not None else '—'):>10} "
                f"{c['vs_sitout']}"
            )
            first = False
        print()
    print("-" * 88)
    print(f"  SUITABLE={report['suitable']}  saved={report['saved']}  keep=False")
    print("=" * 88)
    print()
    return report
