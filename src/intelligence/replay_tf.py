"""Request Ananta observation-replay at a named timeframe. Sibling file only."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from src.tools.ananta_api import get_observation_replay
from src.tools.lab_replay import print_replay_summary, write_replay_jsonl
from src.tools.observation_log import REPLAY_LOG

VERSION = "REPLAY-TF-v0"


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
    return run("BTC/USD", "4h", smoke=True, stride=4, max_bars=80)
