"""Request Ananta observation-replay at a named timeframe. Sibling file only."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from src.tools.ananta_api import get_lab_coverage, get_observation_replay
from src.tools.lab_replay import print_replay_summary, write_replay_jsonl
from src.tools.observation_log import REPLAY_LOG

VERSION = "REPLAY-TF-v0.1"


def coverage_4h(symbol: str = "BTC/USD") -> Dict[str, Any]:
    got = get_lab_coverage()
    data = (got.get("data") or {}) if got.get("success") else {}
    rows = data.get("symbols") or data.get("coverage") or []
    if isinstance(rows, dict):
        rows = list(rows.values()) if rows else []
    hit = None
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("symbol") or "") == symbol:
            hit = row
            break
    return {
        "ok": bool(got.get("success")),
        "symbol": symbol,
        "bars_1h": (hit or {}).get("bars_1h"),
        "bars_4h": (hit or {}).get("bars_4h"),
        "bars_1d": (hit or {}).get("bars_1d"),
        "span_days": (hit or {}).get("span_days"),
        "from": (hit or {}).get("from"),
        "to": (hit or {}).get("to"),
        "error": None if got.get("success") else (got.get("error") or got.get("status_code")),
    }


def probe(symbol: str = "BTC/USD", timeframe: str = "4h", **kwargs) -> Dict[str, Any]:
    got = get_observation_replay(symbol=symbol, timeframe=timeframe, **kwargs)
    data = got.get("data") if got.get("success") else {}
    if not isinstance(data, dict):
        data = {}
    obs = data.get("observations") or []
    return {
        "http_ok": bool(got.get("success")),
        "status_code": got.get("status_code"),
        "error": (got.get("error") or "")[:400] if not got.get("success") else None,
        "replay_ok": data.get("ok"),
        "sampled": data.get("sampled"),
        "n_obs": len(obs) if isinstance(obs, list) else 0,
        "keys": sorted(list(data.keys()))[:20] if data else [],
        "coverage": data.get("coverage"),
        "timeframe_sent": timeframe,
    }


def diagnose_4h(symbol: str = "BTC/USD") -> Dict[str, Any]:
    cov = coverage_4h(symbol)
    print(f"\nTF DIAGNOSE  {VERSION}")
    print("=" * 64)
    print(f"  coverage {symbol} bars_1h={cov.get('bars_1h')} bars_4h={cov.get('bars_4h')} bars_1d={cov.get('bars_1d')}")
    print(f"  span={cov.get('span_days')}  {cov.get('from')} → {cov.get('to')}")
    probes: List[dict] = []
    for tf in ("4h", "240", "4H"):
        p = probe(symbol, tf, stride=1, include_observations=True, max_bars=80)
        probes.append(p)
        print(
            f"  probe timeframe={tf!r}  http={p['http_ok']} replay_ok={p['replay_ok']} "
            f"n_obs={p['n_obs']} sampled={p['sampled']} err={p.get('error')}"
        )
    wired = any(p.get("n_obs", 0) > 0 for p in probes)
    print("-" * 64)
    if not wired:
        print("  4h observation-replay is NOT_WIRED. Do not invent 4h from 1h.")
        if (cov.get("bars_4h") or 0) > 0:
            print("  Candles exist; the observation-replay path does not emit 4h rows.")
    else:
        print("  At least one timeframe token returned observations.")
    print("=" * 64)
    print()
    return {"ok": True, "coverage": cov, "probes": probes, "wired": wired, "keep": False}


def run(
    symbol: str = "BTC/USD",
    timeframe: str = "4h",
    *,
    smoke: bool = True,
    stride: int = 4,
    max_bars: Optional[int] = 80,
) -> Dict[str, Any]:
    tf = (timeframe or "4h").lower()
    slug = symbol.replace("/", "")
    dest = Path(f"observation_replay_smoke_{tf}.jsonl" if smoke else f"observation_replay_{slug}_{tf}.jsonl")
    if smoke:
        max_bars = max_bars or 80
        stride = max(stride, 4)
    print(f"\nREPLAY TF  {VERSION}")
    print("=" * 64)
    print(f"  symbol={symbol} timeframe={tf} smoke={smoke}")
    print(f"  dest={dest}")
    print(f"  will not touch {REPLAY_LOG} or observation_log.jsonl")
    print("-" * 64)
    got = get_observation_replay(
        symbol=symbol,
        timeframe=tf,
        stride=stride,
        include_observations=True,
        max_bars=max_bars,
    )
    if not got.get("success"):
        print(f"  FAILED: {got.get('error') or got.get('status_code')}")
        print("  Leave NOT_WIRED. Do not invent bars.")
        print("=" * 64)
        return {"ok": False, "reason": got.get("error") or got, "keep": False, "dest": str(dest)}
    data = got.get("data") or {}
    print_replay_summary(data)
    obs = data.get("observations") or []
    if data.get("ok") and obs:
        write_replay_jsonl(obs, dest, append=False)
        print(f"  wrote {len(obs)} → {dest}")
        print(f"  BTC 1h ledger untouched: {REPLAY_LOG}")
    else:
        print("  no observations — dest not written. 4h stays NOT_WIRED.")
    print("=" * 64)
    return {
        "ok": bool(data.get("ok") and obs),
        "n": len(obs),
        "dest": str(dest),
        "keep": False,
        "btc_1h_untouched": True,
        "timeframe": tf,
    }


def run_btc_4h_smoke() -> Dict[str, Any]:
    return run("BTC/USD", "4h", smoke=True, stride=1, max_bars=80)
