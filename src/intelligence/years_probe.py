"""Can Ananta serve more than ~1.2y PIT candles? Report only."""
from __future__ import annotations

from typing import Any, Dict, List

from src.tools.coverage_client import get_lab_coverage_long

VERSION = "YEARS-PROBE-v0"
TARGET_YEARS = 3.5


def probe() -> Dict[str, Any]:
    got = get_lab_coverage_long()
    data = got.get("data") or {}
    if not got.get("success"):
        return {
            "ok": False,
            "reason": got.get("error") or got.get("status_code") or "COVERAGE_FAIL",
            "keep": False,
        }
    rows = data.get("symbols") or []
    books: List[dict] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        span = row.get("span_days")
        try:
            years = round(float(span) / 365.25, 2) if span is not None else None
        except (TypeError, ValueError):
            years = None
        books.append({
            "symbol": row.get("symbol"),
            "bars_1h": row.get("bars_1h"),
            "bars_4h": row.get("bars_4h"),
            "span_days": span,
            "years": years,
            "from": row.get("from"),
            "to": row.get("to"),
            "usable_1y": row.get("usable_1y"),
            "short_of_target": True if years is None else years < TARGET_YEARS,
        })
    return {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "target_years": TARGET_YEARS,
        "n": len(books),
        "books": books,
        "can_dump_3_4y": False,
        "note": "~1.2y usable. 3-4y stays on the map until Ananta extends PIT history.",
    }


def print_years() -> Dict[str, Any]:
    r = probe()
    print(f"\nYEARS PROBE  {r.get('version', VERSION)}")
    print("=" * 64)
    if not r.get("ok"):
        print(f"  {r.get('reason')}")
        print("=" * 64)
        return r
    print(f"  target={r['target_years']}y  books={r['n']}  dump_3_4y={r['can_dump_3_4y']}")
    print("-" * 64)
    for b in r.get("books") or []:
        print(
            f"  {str(b.get('symbol') or ''):<12} 1h={b.get('bars_1h')}  "
            f"4h={b.get('bars_4h')}  years={b.get('years')}  "
            f"1y={b.get('usable_1y')}  short={b.get('short_of_target')}"
        )
    print("-" * 64)
    print(f"  {r.get('note')}")
    print("  Do not invent older bars.")
    print("=" * 64)
    print()
    return r
