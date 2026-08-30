"""Cite knowledge_grid.json for a regime or strategy. Consult cannot TAKE."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

GRID = Path("knowledge_grid.json")
VERSION = "CITE-v0"


def cite(strategy: Optional[str] = None, regime: Optional[str] = None) -> Dict[str, Any]:
    if not GRID.exists():
        return {"ok": False, "reason": "NO_GRID", "keep": False, "issued": "UNKNOWN"}
    try:
        data = json.loads(GRID.read_text())
    except Exception as e:
        return {"ok": False, "reason": str(e), "keep": False, "issued": "UNKNOWN"}
    want_s = (strategy or "").lower().strip() or None
    want_r = (regime or "").upper().strip() or None
    hits = []
    for row in data.get("rows") or []:
        if want_s and row.get("strategy") != want_s:
            continue
        if want_r and row.get("regime") != want_r:
            continue
        hits.append(row)
    return {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "issued": "UNKNOWN",
        "n": len(hits),
        "rows": hits,
        "note": "Cite only. Does not change Wave A issued action.",
    }


def print_cite(strategy: Optional[str] = None, regime: Optional[str] = None) -> Dict[str, Any]:
    report = cite(strategy, regime)
    print(f"\nGRID CITE  {report.get('version', VERSION)}")
    print("=" * 64)
    print("Memory citation. Issued stays UNKNOWN/WAIT. Not KEEP.")
    if not report.get("ok"):
        print(f"  {report.get('reason')}")
        print("  run print_grid() first")
        print("=" * 64)
        return report
    print(f"  filter strategy={strategy or '—'} regime={regime or '—'} n={report.get('n')}")
    print("-" * 64)
    for row in report.get("rows") or []:
        print(f"  {row.get('strategy')} × {row.get('regime')}")
        for bk, c in (row.get("books") or {}).items():
            print(
                f"    {bk:<4} n={c.get('n')} take={c.get('n_take')} "
                f"depth={c.get('depth')} +1h={c.get('+1h_TAKE')} {c.get('vs_sitout')}"
            )
    print("-" * 64)
    print("  Cite ≠ TAKE. Wave A stays WATCH.")
    print("=" * 64)
    print()
    return report
