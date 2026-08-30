"""Compare one cell across BTC ETH SOL AVAX. Not KEEP."""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.intelligence.setup_memory import extract

DEFAULT_STRAT = "donchian-breakout"
DEFAULT_REGIME = "TREND_UP"
BOOKS = ("replay", "eth", "sol", "avax")
LABEL = {"replay": "BTC", "eth": "ETH", "sol": "SOL", "avax": "AVAX"}


def compare(strategy: str = DEFAULT_STRAT, regime: str = DEFAULT_REGIME) -> Dict[str, Any]:
    strategy = (strategy or DEFAULT_STRAT).lower()
    regime = (regime or DEFAULT_REGIME).upper()
    books = {}
    for b in BOOKS:
        books[LABEL[b]] = _cell(extract(b), strategy, regime)
    return {
        "ok": True,
        "keep": False,
        "strategy": strategy,
        "regime": regime,
        "books": books,
        "note": "Same gates, four books. Disagreement is a finding. Not KEEP.",
    }


def print_compare_books(strategy: Optional[str] = None, regime: Optional[str] = None) -> Dict[str, Any]:
    report = compare(strategy or DEFAULT_STRAT, regime or DEFAULT_REGIME)
    print("\nBOOKS COMPARE  BTC ETH SOL AVAX")
    print("=" * 64)
    print(f"  cell={report['strategy']} × {report['regime']} × 1h")
    print("-" * 64)
    for name in ("BTC", "ETH", "SOL", "AVAX"):
        c = report["books"].get(name) or {}
        print(
            f"  {name:<4} n={c.get('n')} TAKE={c.get('n_take')} "
            f"depth={c.get('take_depth')} +1h_TAKE={c.get('mean_1h_take')}"
        )
    print("-" * 64)
    print("  AVAX Donchian UP hurt ≠ rewrite. Aggregate ≠ cell.")
    print("=" * 64)
    print()
    return report


def _cell(mem: dict, strategy: str, regime: str) -> dict:
    for c in (mem.get("by_cell") or {}).values():
        if c.get("strategy") == strategy and str(c.get("regime") or "").upper() == regime:
            return c
    return {"n": 0, "n_take": 0, "n_skip_setup": 0, "take_depth": "NONE", "mean_1h_take": None}
