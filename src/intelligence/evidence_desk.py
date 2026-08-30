"""One query object from saved T3 artifacts. Does not rescan jsonl.

Needs knowledge_grid.json, excursion_report.json, hist_vs_live.json.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

VERSION = "DESK-v0"
FILES = {
    "grid": Path("knowledge_grid.json"),
    "excursion": Path("excursion_report.json"),
    "hvl": Path("hist_vs_live.json"),
}


def _load(p: Path) -> Optional[dict]:
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def desk() -> Dict[str, Any]:
    grid = _load(FILES["grid"])
    exc = _load(FILES["excursion"])
    hvl = _load(FILES["hvl"])
    missing = [k for k, p in FILES.items() if _load(p) is None]
    exc_ix = {}
    for row in (exc or {}).get("rows") or []:
        exc_ix[(row.get("strategy"), row.get("regime"))] = row.get("books") or {}
    hvl_ix = {row.get("strategy"): row for row in (hvl or {}).get("rows") or []}
    merged = []
    for row in (grid or {}).get("rows") or []:
        key = (row.get("strategy"), row.get("regime"))
        item = {
            "strategy": row.get("strategy"),
            "regime": row.get("regime"),
            "books": row.get("books") or {},
            "excursion": exc_ix.get(key) or {},
            "wave_a_live": hvl_ix.get(row.get("strategy")) if row.get("strategy") in ("hunter", "squeeze", "bollinger-mr") else None,
            "keep": False,
        }
        merged.append(item)
    out = {
        "ok": True,
        "version": VERSION,
        "missing": missing,
        "keep": False,
        "issued": "UNKNOWN",
        "n": len(merged),
        "rows": merged,
        "note": "Merged artifacts. Cite cannot TAKE.",
    }
    Path("evidence_desk.json").write_text(json.dumps(out, indent=2, default=str))
    out["saved"] = "evidence_desk.json"
    return out


def print_desk() -> Dict[str, Any]:
    r = desk()
    print(f"\nEVIDENCE DESK  {r['version']}")
    print("=" * 72)
    print("grid + excursion + hist-vs-live. Queryable. Not KEEP.")
    if r.get("missing"):
        print(f"  missing artifacts: {r['missing']}")
    print("-" * 72)
    for row in r.get("rows") or []:
        print(f"  {row.get('strategy')} × {row.get('regime')}")
        for bk, c in (row.get("books") or {}).items():
            ex = (row.get("excursion") or {}).get(bk) or {}
            print(
                f"    {bk:<4} take={c.get('n_take')} {c.get('vs_sitout'):<24} "
                f"+1h={c.get('+1h_TAKE')}  MFE={ex.get('mean_mfe')} MAE={ex.get('mean_mae')}"
            )
        live = row.get("wave_a_live")
        if live:
            lv = live.get("live") or {}
            print(
                f"    live setups={lv.get('n')} take={lv.get('n_take')} "
                f"+1h_SKIP={lv.get('+1h_SKIP')}  (WATCH if take=0)"
            )
        print()
    print("-" * 72)
    print(f"  saved={r.get('saved')}  issued={r.get('issued')}  keep=False")
    print("=" * 72)
    print()
    return r
