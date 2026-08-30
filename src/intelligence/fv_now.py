"""Current Market Truth SMA + session VWAP. Not a trade. Not hist backfill."""
from __future__ import annotations

from typing import Any, Dict

from src.tools.market_truth import capture_market_truth

VERSION = "FV-NOW-v0"


def snapshot(asset: str = "BTC/USD") -> Dict[str, Any]:
    mt = capture_market_truth()
    assets = (mt or {}).get("assets") or {}
    slot = assets.get(asset) or {}
    if asset == "BTC/USD" and not slot:
        slot = (mt or {}).get("btc") or {}
    price = slot.get("price")
    sma = slot.get("sma_ref")
    vwap = slot.get("session_vwap") or slot.get("vwap")

    def dist(est):
        try:
            if price is None or est is None or float(est) == 0:
                return None
            return round((float(price) / float(est) - 1.0) * 100.0, 4)
        except (TypeError, ValueError):
            return None

    return {
        "ok": bool(price),
        "version": VERSION,
        "asset": asset,
        "ts": (mt or {}).get("ts"),
        "observed_price": price,
        "sma20": sma,
        "sma_dist_pct": dist(sma),
        "session_vwap": vwap,
        "vwap_dist_pct": dist(vwap),
        "execute": False,
        "keep": False,
        "not_a_trade": True,
        "note": "NOW snapshot. Does not rewrite old observation_log rows.",
    }


def print_fv_now(asset: str = "BTC/USD") -> Dict[str, Any]:
    r = snapshot(asset)
    print(f"\nFV NOW  {VERSION}")
    print("=" * 64)
    print("Live capture. execute=False. Not KEEP.")
    print(f"  {r.get('asset')}  asof={str(r.get('ts') or '')[:19]}")
    print(f"  price={r.get('observed_price')}")
    print(f"  sma20={r.get('sma20')}  dist%={r.get('sma_dist_pct')}")
    print(f"  vwap ={r.get('session_vwap')}  dist%={r.get('vwap_dist_pct')}")
    print("-" * 64)
    print("  Distance ≠ edge. Old log rows unchanged.")
    print("=" * 64)
    print()
    return r
