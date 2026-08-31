"""Probe whether Ananta observation-replay honors config params."""
from __future__ import annotations

from typing import Any, Dict

from src.tools.ananta_api import _auth_headers, _owner_token, BASE_URL
import requests

VERSION = "CFG-REPLAY-v0"
CONFIG = "donchian-lb20-v1"
LOOKBACK = 20


def probe(*, symbol: str = "BTC/USD", max_bars: int = 80, stride: int = 12) -> Dict[str, Any]:
    got = _owner_token()
    if not got.get("success"):
        return {
            "ok": False,
            "version": VERSION,
            "config_id": CONFIG,
            "reason": "LOGIN_FAILED",
            "error": got.get("error"),
            "keep": False,
            "scores": None,
        }
    params = {
        "symbol": symbol,
        "timeframe": "1h",
        "stride": stride,
        "include_observations": "false",
        "max_bars": max_bars,
        "strategy": "donchian-breakout",
        "lookback": LOOKBACK,
        "config_id": CONFIG,
    }
    try:
        r = requests.get(
            f"{BASE_URL}/api/lab/observation-replay",
            params=params,
            headers=_auth_headers(got["token"]),
            timeout=120,
        )
    except Exception as e:
        return {
            "ok": False,
            "version": VERSION,
            "config_id": CONFIG,
            "reason": "HTTP_ERROR",
            "error": str(e),
            "keep": False,
        }
    body = {}
    try:
        body = r.json() if r.text else {}
    except Exception:
        body = {"raw": (r.text or "")[:500]}
    summary = body.get("summary") or {}
    ev = (summary.get("strategy_evidence") or {}).get("donchian-breakout") or {}
    impl = body.get("implementations") or {}
    honored = bool(
        impl.get("donchian_lookback") == LOOKBACK
        or impl.get("lookback") == LOOKBACK
        or (body.get("params") or {}).get("lookback") == LOOKBACK
    )
    return {
        "ok": r.status_code == 200 and bool(body.get("ok")),
        "version": VERSION,
        "config_id": CONFIG,
        "http": r.status_code,
        "replay_ok": body.get("ok"),
        "sampled": summary.get("bars_sampled"),
        "donchian_evidence": {
            "setups": ev.get("setups"),
            "take_equivalent": ev.get("take_equivalent"),
        },
        "implementations_keys": list(impl.keys())[:20],
        "param_honored": honored,
        "reason": "PARAM_HONORED" if honored else "STOCK_DONCHIAN_OR_IGNORED",
        "win_rate_after_cost": None,
        "promote": False,
        "keep": False,
        "stage": "RESEARCH",
    }


def print_probe() -> Dict[str, Any]:
    r = probe()
    print(f"\nCFG REPLAY PROBE  {VERSION}  {CONFIG}")
    print("=" * 64)
    print("Does Ananta honor lookback=20? Scores stay empty if not.")
    print(f"  http={r.get('http')} replay_ok={r.get('replay_ok')} sampled={r.get('sampled')}")
    print(f"  donchian={r.get('donchian_evidence')}")
    print(f"  param_honored={r.get('param_honored')}  reason={r.get('reason')}")
    print(f"  impl_keys={r.get('implementations_keys')}")
    print("-" * 64)
    print("  win_rate_after_cost=None  promote=False  Wave A untouched")
    print("=" * 64)
    print()
    return r
