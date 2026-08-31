"""Request Ananta observation-replay at 15m. Sibling file only."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from src.tools.ananta_api import get_observation_replay
from src.tools.lab_replay import print_replay_summary, write_replay_jsonl
from src.tools.observation_log import REPLAY_LOG

VERSION = "REPLAY-15M-v0.2"
DEST_YEAR = Path("observation_replay_BTCUSD_15m.jsonl")
DEST_SLICE = Path("observation_replay_BTCUSD_15m_slice.jsonl")


def run_btc_15m(
    *,
    smoke: bool = True,
    slice_bars: Optional[int] = None,
    year_pass: bool = False,
    stride: int = 12,
    max_bars: Optional[int] = 80,
) -> Dict[str, Any]:
    if year_pass:
        dest = DEST_YEAR
        max_bars = int(max_bars or 800)
        stride = max(int(stride or 8), 8)
        smoke = False
    elif slice_bars:
        dest = DEST_SLICE
        max_bars = int(slice_bars)
        stride = max(stride, 8)
        smoke = False
    elif smoke:
        dest = Path("observation_replay_smoke_15m.jsonl")
        max_bars = max_bars or 80
        stride = max(stride, 12)
    else:
        dest = DEST_YEAR
        stride = stride or 8
    print(f"\nREPLAY 15M  {VERSION}")
    print("=" * 64)
    print(f"  symbol=BTC/USD timeframe=15m year_pass={year_pass} smoke={smoke}")
    print(f"  dest={dest} max_bars={max_bars} stride={stride}")
    print(f"  will not touch {REPLAY_LOG} or observation_log.jsonl")
    print("-" * 64)
    got = get_observation_replay(
        symbol="BTC/USD",
        timeframe="15m",
        stride=stride,
        include_observations=True,
        max_bars=max_bars,
    )
    if not got.get("success"):
        print(f"  FAILED: {got.get('error') or got.get('status_code')}")
        print("=" * 64)
        return {"ok": False, "reason": got.get("error") or got, "keep": False, "dest": str(dest)}
    data = got.get("data") or {}
    print_replay_summary(data)
    obs = data.get("observations") or []
    if data.get("ok") and obs:
        write_replay_jsonl(obs, dest, append=False)
        print(f"  wrote {len(obs)} → {dest}")
        print(f"  BTC 1h ledger untouched: {REPLAY_LOG}")
        print("  This pass is not a finished 1.17y 15m book unless span says so.")
    else:
        print("  no observations — dest not written.")
    print("=" * 64)
    return {
        "ok": bool(data.get("ok") and obs),
        "n": len(obs),
        "dest": str(dest),
        "keep": False,
        "btc_1h_untouched": True,
        "year_complete": False,
    }


def run_btc_15m_slice(bars: int = 400) -> Dict[str, Any]:
    return run_btc_15m(slice_bars=bars, stride=8)


def run_btc_15m_year_pass(bars: int = 800) -> Dict[str, Any]:
    return run_btc_15m(year_pass=True, max_bars=bars, stride=8)
