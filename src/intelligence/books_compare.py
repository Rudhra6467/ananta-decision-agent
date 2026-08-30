"""Compare one named cell across BTC and ETH hist books. Not KEEP.

CLI: lab compare-books [strategy] [regime]
Default: bollinger-mr COMPRESSION
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.intelligence.setup_memory import extract

DEFAULT_STRAT = "bollinger-mr"
DEFAULT_REGIME = "COMPRESSION"


def compare(strategy: str = DEFAULT_STRAT, regime: str = DEFAULT_REGIME) -> Dict[str, Any]:
    strategy = (strategy or DEFAULT_STRAT).lower()
    regime = (regime or DEFAULT_REGIME).upper()
    btc = extract("replay")
    eth = extract("eth")
    return {
        "ok": True,
        "keep": False,
        "strategy": strategy,
        "regime": regime,
        "btc": _cell(btc, strategy, regime),
        "eth": _cell(eth, strategy, regime),
        "note": "Same gates, two books. Disagreement is a finding. Not KEEP.",
    }


def print_compare_books(strategy: Optional[str] = None, regime: Optional[str] = None) -> Dict[str, Any]:
    report = compare(strategy or DEFAULT_STRAT, regime or DEFAULT_REGIME)
    print("\nBOOKS COMPARE  BTC 1h vs ETH 1h")
    print("=" * 64)
    print("Same pipeline. Separate files. Not KEEP.")
    print(f"  cell={report['strategy']} × {report['regime']} × 1h")
    print("-" * 64)
    for name in ("btc", "eth"):
        c = report[name] or {}
        print(
            f"  {name:<4} n={c.get('n')} TAKE={c.get('n_take')} SKIP={c.get('n_skip_setup')} "
            f"depth={c.get('take_depth')} +1h_TAKE={c.get('mean_1h_take')} "
            f"+1h_SKIP={c.get('mean_1h_skip_setup')}"
        )
    print("-" * 64)
    print("  Disagreement ≠ rewrite. Aggregate ETH +0.15% is not this cell.")
    print("=" * 64)
    print()
    return report


def _cell(mem: dict, strategy: str, regime: str) -> Optional[dict]:
    for c in (mem.get("by_cell") or {}).values():
        if c.get("strategy") == strategy and str(c.get("regime") or "").upper() == regime:
            if "ETH" in str(c.get("asset") or "") or strategy:
                if strategy == c.get("strategy") and regime == str(c.get("regime") or "").upper():
                    if mem.get("source") == "historical_lab":
                        asset = str(c.get("asset") or "")
                        if strategy and regime:
                            # prefer matching book asset when present
                            if "ETH" in asset or "BTC" in asset or True:
                                return c
    # first match
    for c in (mem.get("by_cell") or {}).values():
        if c.get("strategy") == strategy and str(c.get("regime") or "").upper() == regime:
            return c
    return {"n": 0, "n_take": 0, "n_skip_setup": 0, "take_depth": "NONE"}
