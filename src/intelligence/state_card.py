"""Richer state from fields already on the observation. Not similarity. Not KEEP."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.intelligence.scan_candidates import _fp_from_obs
from src.tools.observation_log import OBSERVATION_LOG, _read_jsonl

VERSION = "STATE-CARD-v0"
OUT = Path("state_card.json")


def _slot(obs: dict, asset: str = "BTC/USD") -> dict:
    mt = obs.get("market_truth") or {}
    if isinstance(mt.get("btc"), dict) and asset.startswith("BTC"):
        return mt["btc"]
    assets = mt.get("assets") if isinstance(mt.get("assets"), dict) else {}
    return assets.get(asset) or {}


def card(obs: Optional[dict] = None, asset: str = "BTC/USD") -> Dict[str, Any]:
    if obs is None:
        rows = _read_jsonl(OBSERVATION_LOG) if OBSERVATION_LOG.exists() else []
        obs = rows[-1] if rows else {}
    sl = _slot(obs, asset)
    dec = obs.get("decision") or {}
    keys_present = sorted([k for k, v in sl.items() if v is not None]) if sl else []
    missing = [
        name for name in ("vwap", "funding", "oi", "spread", "volume_z")
        if sl.get(name) is None and sl.get(name.replace("_z", "")) is None
    ]
    return {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "asset": asset,
        "obs_id": obs.get("id"),
        "ts": obs.get("ts") or obs.get("timestamp"),
        "fingerprint": _fp_from_obs(obs) if obs else "UNKNOWN|UNKNOWN|UNKNOWN|UNCLEAR",
        "price": sl.get("price") or sl.get("close"),
        "sma20": sl.get("sma20") or sl.get("sma_20") or sl.get("sma_ref"),
        "vwap": sl.get("vwap") or sl.get("session_vwap"),
        "trend_flag": sl.get("trend_flag"),
        "compression_flag": sl.get("compression_flag"),
        "ret_1h_pct": sl.get("ret_1h_pct"),
        "regime": (obs.get("regime") or sl.get("regime")),
        "decision": dec.get("action") or obs.get("action"),
        "fields_present": keys_present[:40],
        "fields_missing_for_richer_state": missing,
        "note": "Only PIT fields on this observation. Missing stays missing.",
    }


def print_state() -> Dict[str, Any]:
    r = card()
    OUT.write_text(json.dumps(r, indent=2, default=str))
    r["saved"] = str(OUT)
    print(f"\nSTATE CARD  {r['version']}")
    print("=" * 64)
    print("PIT fields only. Not similarity. Not KEEP.")
    print(f"  fp={r.get('fingerprint')}  decision={r.get('decision')}")
    print(f"  price={r.get('price')} sma20={r.get('sma20')} vwap={r.get('vwap')}")
    print(f"  trend={r.get('trend_flag')} comp={r.get('compression_flag')} ret1h={r.get('ret_1h_pct')}")
    print(f"  missing={r.get('fields_missing_for_richer_state')}")
    print("-" * 64)
    print(f"  saved={r.get('saved')}  keep=False")
    print("=" * 64)
    print()
    return r
