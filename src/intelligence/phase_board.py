"""Queryable DRAWDOWN board from closed EXP-008/009/011. Not KEEP."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

VERSION = "PHASE-BOARD-v0"
# Measured +1h TAKE vs SKIP on setups. Source = episode_slice pastes, not a new run.
ROWS: List[Dict[str, Any]] = [
    {"strategy": "bollinger-mr", "phase": "DRAWDOWN",
     "btc": {"take": 39, "t": -0.0704, "s": 0.0651, "exp": "EXP-008"},
     "eth": {"take": 31, "t": 0.1907, "s": -0.0476, "exp": "EXP-009"},
     "sol": {"take": 44, "t": -0.1199, "s": 0.0559, "exp": "EXP-011"}},
    {"strategy": "donchian-breakout", "phase": "DRAWDOWN",
     "btc": {"take": 18, "t": 0.0053, "s": 0.0302, "exp": "EXP-008"},
     "eth": {"take": 23, "t": -0.1674, "s": 0.0480, "exp": "EXP-009"},
     "sol": {"take": 18, "t": -0.0937, "s": 0.1237, "exp": "EXP-011"}},
    {"strategy": "atr-breakout", "phase": "DRAWDOWN",
     "btc": {"take": 5, "t": -0.0653, "s": -0.0368, "exp": "EXP-008"},
     "eth": {"take": 8, "t": -0.3570, "s": 0.1040, "exp": "EXP-009"},
     "sol": {"take": 9, "t": -0.3992, "s": 0.1470, "exp": "EXP-011"}},
    {"strategy": "hunter", "phase": "DRAWDOWN",
     "btc": {"take": 2, "t": -0.2302, "s": 0.0314, "exp": "EXP-008"},
     "eth": {"take": 1, "t": 0.2706, "s": -0.0217, "exp": "EXP-009"},
     "sol": {"take": 0, "t": None, "s": -0.0162, "exp": "EXP-011"}},
]


def _beat(cell: dict) -> str:
    t, s, n = cell.get("t"), cell.get("s"), cell.get("take") or 0
    if n == 0 or t is None:
        return "NO_TAKE"
    if n < 13:
        return "THIN"
    if t > s:
        return "TAKE_GT_SKIP"
    if t < s:
        return "TAKE_LT_SKIP"
    return "WASH"


def print_board() -> Dict[str, Any]:
    print(f"\nPHASE BOARD  {VERSION}  EP-2025-26 DRAWDOWN")
    print("=" * 72)
    print("Closed experiments. Not KEEP. ETH Bollinger ≠ BTC/SOL Bollinger.")
    print("-" * 72)
    for row in ROWS:
        print(f"  {row['strategy']:<20} DRAWDOWN")
        for bk in ("btc", "eth", "sol"):
            c = row[bk]
            flag = _beat(c)
            t = "—" if c["t"] is None else c["t"]
            print(
                f"    {bk.upper():<4} take={c['take']:<3} +1h_T={t:<8} +1h_S={c['s']:<8} "
                f"{flag}  {c['exp']}"
            )
    print("-" * 72)
    print("  TAKE_GT_SKIP ≠ KEEP. THIN ≠ rewrite. Hunter NO_TAKE ≠ TREND_UP enable.")
    print("=" * 72)
    print()
    out = {"ok": True, "version": VERSION, "rows": ROWS, "keep": False, "suitable": 0}
    Path("phase_board.json").write_text(json.dumps(out, indent=2))
    return out
