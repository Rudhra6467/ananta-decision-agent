"""What can be validated now vs what is still blocked. Not KEEP."""
from __future__ import annotations

from typing import Any, Dict

VERSION = "VALIDATION-NOW-v0"


def print_validation() -> Dict[str, Any]:
    print(f"\nVALIDATION NOW  {VERSION}")
    print("=" * 64)
    print("Validate memory vs live tape. Not KEEP. Not autonomy.")
    print("-" * 64)
    print("READY (exists)")
    print("  warehouse BTC+ETH 1h  2021-08-01 → 2026-08-31")
    print("  agent BTC 5y replay   observation_replay.jsonl  n=11089")
    print("  live watch            observation_log.jsonl     Wave A WATCH")
    print("  live outcomes         +15m/+1h/+4h attaching")
    print("-" * 64)
    print("THIS PACK (run after git pull)")
    print("  lab episodes / lab slice     dual EP-2021-22 + EP-2025-26 on BTC 5y")
    print("  lab memory / lab universe    rebuild on 5y book")
    print("  lab replay ETH/USD           sibling file only")
    print("  then episodes+slice+memory on eth")
    print("-" * 64)
    print("BLOCKED — do not fake")
    print("  4h observation-replay        Ananta NOT_WIRED")
    print("  15m year book                Ananta window ~15.5d")
    print("  EXP-010 lookbacks            dc_entry not honored")
    print("  I5 paper TAKE                SUITABLE=0")
    print("  15m/4h × 10 assets seed      Atlas quota + no 4h path")
    print("-" * 64)
    print("VALIDATION MEANS")
    print("  hist 5y phases → same schema live tape → consult-dq / sitout / hist-vs-live")
    print("  TAKE-eq vs SKIP vs WAIT after cost. Episode disagreement is a finding.")
    print("  Not: enable TREND_UP. Not: replace Wave A. Not: autonomy.")
    print("=" * 64)
    print()
    return {"ok": True, "version": VERSION, "keep": False, "i5": False}
