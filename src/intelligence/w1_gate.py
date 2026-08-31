"""W1 gate. Seed must prove coverage. HAVE is not 4y. Not KEEP."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

VERSION = "W1-GATE-v0"
WANT_FROM = datetime(2021, 9, 10, tzinfo=timezone.utc)
HAVE_FROM = datetime(2025, 6, 28, tzinfo=timezone.utc)
PROOF_ASSETS = ("BTC/USD", "ETH/USD")
PROOF_TF = "1h"


def _parse_iso(s: Any) -> Optional[datetime]:
    if not s:
        return None
    text = str(s).replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def judge_coverage(report: Dict[str, Any] | None) -> Dict[str, Any]:
    """Pass only if from_iso <= 2021-09-10 on a real coverage_report dict."""
    report = report or {}
    from_iso = report.get("from_iso") or report.get("from") or report.get("start")
    to_iso = report.get("to_iso") or report.get("to") or report.get("end")
    bars = report.get("bars") or report.get("n") or report.get("count")
    start = _parse_iso(from_iso)
    ok = bool(start and start <= WANT_FROM and bars)
    years = None
    end = _parse_iso(to_iso)
    if start and end:
        years = round((end - start).days / 365.25, 2)
    return {
        "ok": ok,
        "from_iso": from_iso,
        "to_iso": to_iso,
        "bars": bars,
        "years": years,
        "gate": "PASS" if ok else "FAIL",
        "reason": (
            "from_iso <= 2021-09-10"
            if ok
            else "SEED_NOT_PROVEN — still HAVE window or no coverage dict"
        ),
    }


def print_w1(btc: Dict[str, Any] | None = None, eth: Dict[str, Any] | None = None) -> Dict[str, Any]:
    b = judge_coverage(btc)
    e = judge_coverage(eth)
    proven = b["ok"] and e["ok"]
    print(f"\nW1 GATE  {VERSION}")
    print("=" * 64)
    print("Ananta warehouse seed. Not Agent download. Not 4y until PASS.")
    print("-" * 64)
    print(f"  WANT  {WANT_FROM.date()} → now   1h BTC+ETH first")
    print(f"  HAVE  {HAVE_FROM.date()} → 2026-08-30   1.17y CCXT cap")
    print(f"  seed run in this chat: NO (zsh ate the python; backend stopped)")
    print("-" * 64)
    print(f"  BTC/USD 1h  {b['gate']}  from={b['from_iso']}  bars={b['bars']}  years={b['years']}")
    print(f"  ETH/USD 1h  {e['gate']}  from={e['from_iso']}  bars={e['bars']}  years={e['years']}")
    print("-" * 64)
    if not proven:
        print("  STATUS = BLOCKED")
        print("  Do not replay 2021. Do not tag EP-2021-22. Do not claim 4y.")
        print("  Run seed in Ananta backend venv, then paste coverage_report.")
    else:
        print("  STATUS = PASS")
        print("  Next: lab replay BTC/USD and ETH/USD 1h onto NEW books only.")
        print("  Do not overwrite observation_replay.jsonl until smoke is sane.")
    print("-" * 64)
    print("  KEEP=False  I5 blocked  Wave A WATCH")
    print("=" * 64)
    print()
    return {
        "ok": proven,
        "version": VERSION,
        "btc": b,
        "eth": e,
        "keep": False,
        "ep_2021": False,
    }
