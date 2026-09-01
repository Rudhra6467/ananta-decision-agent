"""Deliberate stress-and-regime window. Not KEEP."""
from __future__ import annotations

from typing import Any, Dict

VERSION = "STRESS-WINDOW-v1"

EPISODES = {
    "EP-2021-22-BEAR": {
        "peak": "2021-11-10",
        "trough": "2022-11-21",
        "lead_in": "2021-09-10",
        "aftermath": "2023-01-31",
        "on_ananta_now": True,
    },
    "EP-2025-26-DRAWDOWN": {
        "peak": "2025-10-06",
        "trough": "OPEN",
        "lead_in": "2025-08-06",
        "aftermath": "NOW",
        "on_ananta_now": True,
    },
}

WANT = {
    "start": "2021-08-01",
    "end": "NOW",
    "why": "lead-in + collapse + aftermath of 2021-22 AND 2025-26, plus BETWEEN",
}

HAVE = {
    "start": "2021-08-01",
    "end": "2026-08-31",
    "years": 5.08,
    "btc_eth_1h": True,
    "agent_btc_replay": True,
    "agent_eth_replay": False,
}


def print_window() -> Dict[str, Any]:
    print(f"\nSTRESS WINDOW  {VERSION}")
    print("=" * 64)
    print("PIT only. Live validates. Hist discovers. Not KEEP.")
    print("-" * 64)
    print(f"  WANT  {WANT['start']} → {WANT['end']}")
    print(f"        {WANT['why']}")
    print(f"  HAVE  {HAVE['start']} → {HAVE['end']}  ({HAVE['years']}y) BTC+ETH 1h warehouse")
    print(f"        agent BTC 5y replay=yes  ETH 5y replay=no")
    print("-" * 64)
    for k, e in EPISODES.items():
        print(f"  {k}  peak={e['peak']} trough={e['trough']} ananta={e['on_ananta_now']}")
    print("-" * 64)
    print("  NEXT: lab replay ETH/USD sibling file. Tag both episodes. Do not seed 15m yet.")
    print("  KEEP=False  I5 blocked  Wave A WATCH")
    print("=" * 64)
    print()
    return {"ok": True, "version": VERSION, "want": WANT, "have": HAVE, "keep": False}
