"""Tag 5y BTC/ETH books into both stress episodes. Not KEEP."""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.intelligence.books import ledger_path
from src.tools.observation_log import _read_jsonl

VERSION = "EPISODE-TAG-v1"

# Inclusive UTC dates. 5y book starts 2021-08-01.
PHASES = (
    ("EP21_PRE", "2021-08-01", "2021-09-09"),
    ("EP21_LEAD", "2021-09-10", "2021-11-09"),
    ("EP21_PEAK", "2021-11-10", "2021-11-24"),
    ("EP21_CRASH", "2021-11-25", "2022-11-21"),
    ("EP21_AFTER", "2022-11-22", "2023-01-31"),
    ("BETWEEN", "2023-02-01", "2025-06-27"),
    ("PRE_LEAD", "2025-06-28", "2025-08-05"),
    ("LEAD_IN", "2025-08-06", "2025-10-05"),
    ("PEAK_BAND", "2025-10-06", "2025-10-20"),
    ("DRAWDOWN", "2025-10-21", "2026-12-31"),
)


def _day(ts: str) -> Optional[str]:
    if not ts:
        return None
    raw = str(ts).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw).astimezone(timezone.utc).date().isoformat()
    except ValueError:
        return str(ts)[:10] if len(str(ts)) >= 10 else None


def phase_for(ts: str) -> str:
    d = _day(ts)
    if not d:
        return "UNPARSED"
    for name, a, b in PHASES:
        if a <= d <= b:
            return name
    if d < "2021-08-01":
        return "BEFORE_BOOK"
    return "AFTER_WINDOW"


def print_episodes(source: str = "replay") -> Dict[str, Any]:
    path = ledger_path(source)
    exists = Path(path).exists()
    rows = _read_jsonl(path) if exists else []
    counts: Counter = Counter()
    for obs in rows:
        st = obs.get("system_truth") or {}
        ts = str(obs.get("ts") or st.get("ts") or "")
        counts[phase_for(ts)] += 1
    print(f"\nEPISODE TAG  {VERSION}  book={source}")
    print("=" * 64)
    print("5y book: EP-2021-22 + BETWEEN + EP-2025-26. Not KEEP.")
    print(f"  book={path}  exists={exists}  obs={len(rows)}  keep=False")
    print("-" * 64)
    order = [p[0] for p in PHASES] + ["BEFORE_BOOK", "AFTER_WINDOW", "UNPARSED"]
    for name in order:
        n = counts.get(name, 0)
        if n or name in {p[0] for p in PHASES}:
            print(f"  {name:<14} n={n}")
    print("-" * 64)
    print("  Tag ≠ SUITABLE. Dual-crash mix is the point of the 5y book.")
    print("=" * 64)
    print()
    dest = Path("episode_tag.json" if source in ("replay", "btc") else f"episode_tag_{source}.json")
    out = {
        "ok": True,
        "version": VERSION,
        "book": str(path),
        "exists": exists,
        "n_obs": len(rows),
        "counts": dict(counts),
        "keep": False,
    }
    dest.write_text(json.dumps(out, indent=2))
    return out
