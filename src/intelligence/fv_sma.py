"""sma20_close from the observation's own Market Truth.

Uses sma_ref already stored at capture time. Does not fetch Kraken now
and attach it to an old bar. Hist replay without sma_ref stays PENDING.
execute=False. Not KEEP.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.intelligence.fv_interface import estimate as iface_estimate
from src.tools.observation_log import OBSERVATION_LOG, _read_jsonl

VERSION = "FV-SMA-v0"


def _slot(mt: dict, asset: str) -> dict:
    assets = (mt or {}).get("assets") or {}
    if isinstance(assets, dict) and assets.get(asset):
        return assets.get(asset) or {}
    if "ETH" in asset:
        return (mt or {}).get("eth") or {}
    return (mt or {}).get("btc") or {}


def from_observation(obs: Optional[dict], *, asset: str = "BTC/USD") -> Dict[str, Any]:
    if not obs:
        return iface_estimate(asset=asset, method="sma20_close")
    mt = obs.get("market_truth") or {}
    slot = _slot(mt, asset)
    price = slot.get("price")
    sma = slot.get("sma_ref")
    ts = obs.get("ts") or (obs.get("system_truth") or {}).get("ts")
    if price is None or sma is None:
        out = iface_estimate(asset=asset, method="sma20_close", observed_price=price, asof=str(ts) if ts else None)
        out["reason"] = "NO_SMA_REF_ON_OBSERVATION"
        out["hint"] = "Live Market Truth has sma_ref. Hist replay often does not."
        return out
    try:
        px = float(price)
        est = float(sma)
        dist = round((px / est - 1.0) * 100.0, 4) if est else None
    except (TypeError, ValueError):
        return {"ok": False, "reason": "BAD_NUMBERS", "execute": False, "keep": False}
    return {
        "ok": True,
        "version": VERSION,
        "method": "sma20_close",
        "asset": asset,
        "asof": ts,
        "observed_price": px,
        "estimate": est,
        "distance_pct": dist,
        "uncertainty": "sma20 vs last close; not a valuation model",
        "inputs_asof": ["market_truth.sma_ref", "market_truth.price"],
        "execute": False,
        "keep": False,
        "not_a_trade": True,
        "note": "Distance from SMA-20 already on this observation. Not BUY.",
    }


def from_latest_live(*, asset: str = "BTC/USD") -> Dict[str, Any]:
    rows = _read_jsonl(OBSERVATION_LOG)
    return from_observation(rows[-1] if rows else None, asset=asset)


def print_fv_sma(asset: str = "BTC/USD") -> Dict[str, Any]:
    r = from_latest_live(asset=asset)
    print(f"\nFV SMA20  {VERSION}")
    print("=" * 64)
    print("PIT sma_ref on the latest live observation. execute=False.")
    print(f"  ok={r.get('ok')}  method={r.get('method')}  reason={r.get('reason') or r.get('note')}")
    print(f"  asset={r.get('asset')}  asof={str(r.get('asof') or '')[:19]}")
    print(f"  price={r.get('observed_price')}  sma20={r.get('estimate')}  dist%={r.get('distance_pct')}")
    print("-" * 64)
    print("  Distance ≠ mispricing edge. execute=False. Not KEEP.")
    print("=" * 64)
    print()
    return r
