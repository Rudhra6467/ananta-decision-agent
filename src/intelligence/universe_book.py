"""Universe cells scored on a named hist book. Default remains BTC.

lab universe          → BTC observation_replay.jsonl
python print_universe_book('eth') → ETH sibling file
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.intelligence.books import artifact, book, ledger_path
from src.intelligence.decision_quality import evidence_depth, score_horizon
from src.intelligence.setup_memory import extract
from src.intelligence.universe import fit_from_take

VERSION = "UNIVERSE-BOOK-v0"


def research_book(source: str = "replay") -> Dict[str, Any]:
    mem = extract(source)
    cells = []
    fits = Counter()
    for c in (mem.get("by_cell") or {}).values():
        n_take = int(c.get("n_take") or 0)
        mean = c.get("mean_1h_take")
        take_1h = score_horizon(role="TAKE", n=n_take, mean=mean, clock="+1h")
        fit, why = fit_from_take(take_1h)
        entry = {
            "strategy": c.get("strategy"),
            "asset": c.get("asset"),
            "regime": c.get("regime"),
            "n": c.get("n"),
            "n_take": n_take,
            "depth": evidence_depth(n_take, role="TAKE"),
            "+1h_TAKE": mean,
            "verdict": take_1h.get("verdict"),
            "fit": fit,
            "why": why,
            "keep": False,
        }
        fits[fit] += 1
        cells.append(entry)
    report = {
        "ok": True,
        "version": VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "book": str(ledger_path(source)),
        "book_name": book(source),
        "n_obs": mem.get("n_obs"),
        "n_cells": len(cells),
        "fit_counts": dict(fits),
        "keep": False,
        "cells": sorted(cells, key=lambda x: (x["strategy"] or "", x["regime"] or "")),
        "note": "Book score. SUITABLE is not KEEP. Default universe CLI still BTC.",
    }
    dest = artifact("universe_knowledge", source)
    try:
        dest.write_text(json.dumps(report, indent=2, default=str))
        report["saved"] = str(dest)
    except Exception:
        report["saved"] = None
    return report


def print_universe_book(source: str = "replay") -> Dict[str, Any]:
    report = research_book(source)
    print(f"\nSTRATEGY RESEARCH UNIVERSE  {report.get('version')}  book={report.get('book_name')}")
    print("=" * 64)
    print(f"  file={report.get('book')}  keep=False")
    print(f"  obs={report.get('n_obs')}  cells={report.get('n_cells')}  fit={report.get('fit_counts')}")
    print("-" * 64)
    for c in report.get("cells") or []:
        if not c.get("n_take") and not c.get("n"):
            continue
        print(
            f"    {c['strategy']:<18} {str(c.get('asset') or '').split('/')[0]:<4} {c['regime']:<12} "
            f"n={c['n']:<4} take={c['n_take']:<4} depth={c['depth']:<10} "
            f"+1h={c.get('+1h_TAKE')}  {c.get('verdict')}  fit={c.get('fit')}"
        )
    print("-" * 64)
    print("  SUITABLE is not KEEP. ETH file does not replace BTC universe_knowledge.json.")
    print(f"  saved: {report.get('saved')}")
    print("=" * 64)
    print()
    return report
