"""vwap_session from the observation only. Do not fetch VWAP now onto an old bar."""
from __future__ import annotations

from typing import Any, Dict, Optional

from src.intelligence.fv_interface import estimate as iface_estimate
from src.tools.observation_log import OBSERVATION_LOG, _read_jsonl

VERSION = "FV-VWAP-v0"
VWAP_KEYS = ("vwap", "vwap_session", "session_vwap", "vwap_ref")


def _slot(mt: dict, asset: str) -> dict:
    assets = (mt or {}).get("assets") or {}
    if isinstance(assets, dict) and assets.get(asset):
        return assets.get(asset) or {}
    if "ETH" in asset:
        return (mt or {}).get("eth") or {}
    return (mt or {}).get("btc") or {}


def _vwap(slot: dict) -> Optional[float]:
    for k in VWAP_KEYS:
        v = slot.get(k)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def from_observation(obs: Optional[dict], *, asset: str = "BTC/USD") -> Dict[str, Any]:
    base = iface_estimate(asset=asset, method="vwap_session")
    if not obs:
        base["reason"] = "NO_OBSERVATION"
        return base
    mt = obs.get("market_truth") or {}
    slot = _slot(mt, asset)
    price = slot.get("price")
    vwap = _vwap(slot)
    ts = obs.get("ts") or (obs.get("system_truth") or {}).get("ts")
    if vwap is None:
        base["reason"] = "NO_VWAP_ON_OBSERVATION"
        base["observed_price"] = price
        base["asof"] = ts
        base["hint"] = "Market Truth does not store session VWAP yet. Leave PENDING."
        return base
    try:
        px = float(price)
        est = float(vwap)
        dist = round((px / est - 1.0) * 100.0, 4) if est else None
    except (TypeError, ValueError):
        return {"ok": False, "reason": "BAD_NUMBERS", "execute": False, "keep": False}
    return {
        "ok": True,
        "version": VERSION,
        "method": "vwap_session",
        "asset": asset,
        "asof": ts,
        "observed_price": px,
        "estimate": est,
        "distance_pct": dist,
        "execute": False,
        "keep": False,
        "not_a_trade": True,
    }


def from_latest_live(*, asset: str = "BTC/USD") -> Dict[str, Any]:
    rows = _read_jsonl(OBSERVATION_LOG)
    return from_observation(rows[-1] if rows else None, asset=asset)


def print_fv_vwap(asset: str = "BTC/USD") -> Dict[str, Any]:
    r = from_latest_live(asset=asset)
    print(f"\nFV VWAP  {VERSION}")
    print("=" * 64)
    print("PIT VWAP on latest live observation only. execute=False.")
    print(f"  ok={r.get('ok')}  reason={r.get('reason') or r.get('method')}")
    print(f"  price={r.get('observed_price')}  vwap={r.get('estimate')}  dist%={r.get('distance_pct')}")
    if r.get("hint"):
        print(f"  {r['hint']}")
    print("-" * 64)
    print("  PENDING is correct if Market Truth has no VWAP field.")
    print("=" * 64)
    print()
    return r
