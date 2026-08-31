"""Deliberate stress-and-regime window. Not calendar years. Not KEEP.

Ananta must serve PIT candles. Do not invent 2021 bars.
"""
from __future__ import annotations

from typing import Any, Dict

VERSION = "STRESS-WINDOW-v0"

# Verified public cycle marks (approx). Used as window anchors, not prices to trade.
EPISODES = {
    "EP-2021-22-BEAR": {
        "peak": "2021-11-10",
        "peak_note": "BTC ATH ~$69k",
        "trough": "2022-11-21",
        "trough_note": "BTC ~$15.5k after LUNA/3AC/FTX",
        "lead_in": "2021-09-10",  # two months before peak
        "aftermath": "2023-01-31",
        "on_ananta_now": False,
    },
    "EP-2025-26-DRAWDOWN": {
        "peak": "2025-10-06",
        "peak_note": "BTC ATH ~$123k–$126k",
        "trough": "OPEN",
        "trough_note": "~50% drawdown into mid-2026; floor not declared",
        "lead_in": "2025-08-06",
        "aftermath": "NOW",
        "on_ananta_now": "PARTIAL",  # coverage from 2025-06-28
    },
}

WANT = {
    "start": "2021-09-10",
    "end": "NOW",
    "why": "lead-in + collapse + aftermath of 2021-22 AND 2025-26, plus range/bull in between",
}

HAVE = {
    "start": "2025-06-28",
    "end": "2026-08-30",
    "years": 1.17,
    "covers": "most of EP-2025-26 including ~3 months before Oct-2025 peak",
    "missing": "EP-2021-22 entire lead-in/crash/aftermath",
}

LAW = (
    "Objective is regime diversity and major stress, not 'four years'. "
    "PIT only. No invented older candles. Live tape validates; hist discovers. "
    "Shadow scan ≠ capital. Config budget still applies."
)


def print_window() -> Dict[str, Any]:
    print(f"\nSTRESS WINDOW  {VERSION}")
    print("=" * 64)
    print(LAW)
    print("-" * 64)
    print(f"  WANT  {WANT['start']} → {WANT['end']}")
    print(f"        {WANT['why']}")
    print(f"  HAVE  {HAVE['start']} → {HAVE['end']}  ({HAVE['years']}y)")
    print(f"        covers: {HAVE['covers']}")
    print(f"        missing: {HAVE['missing']}")
    print("-" * 64)
    for k, e in EPISODES.items():
        print(f"  {k}  peak={e['peak']} trough={e['trough']} lead_in={e['lead_in']} ananta={e['on_ananta_now']}")
    print("-" * 64)
    print("  NEXT: Ananta extends PIT warehouse to 2021-09-10.")
    print("        Until then: research ONLY on HAVE window. Tag EP-2025-26. Do not dump fake 4y.")
    print("  KEEP=False  I5 blocked  Wave A WATCH")
    print("=" * 64)
    print()
    return {"ok": True, "version": VERSION, "want": WANT, "have": HAVE, "keep": False}
