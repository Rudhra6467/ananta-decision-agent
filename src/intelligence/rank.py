"""I4 research rank v0.1 — key first, then trend. Never TAKE.

Explicit flag (lab rank-state DOWN) = trend research.
No flag / live = exact fingerprint key, same honesty as consult.

CLI: lab rank-state [UP|DOWN|live]
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.intelligence.boards import boards
from src.intelligence.consult import consult
from src.intelligence.lookup import lookup

VERSION = "RANK-v0.1"
OUT = Path("state_rank.json")
BOARD_PRI = {"SUITABLE": 0, "WASH": 1, "TESTED_UNKNOWN": 2, "UNTESTED": 3, "UNSUITABLE": 4}
DEPTH_PRI = {"SOLID": 0, "ADEQUATE": 1, "THIN": 2, "ANECDOTE": 3, "NONE": 4}


def rank_state(flag: Optional[str] = None, *, source: str = "live") -> Dict[str, Any]:
    c = consult(source=source, write_snapshot=False, skip_log=True)
    explicit = bool(flag) and str(flag).upper() not in ("LIVE", "NOW")
    parent: List[dict] = []
    if explicit:
        tape = str(flag).upper()
        match = "TREND"
        n_key = None
        hist_rows = (lookup(tape, "replay").get("rows") or []) if tape not in ("UNKNOWN", "NONE", "") else []
        issued = "WAIT" if hist_rows else "UNKNOWN"
        why = "EXPLICIT_TREND_RESEARCH"
    else:
        tape = str(c.get("flag") or "UNKNOWN")
        match = str(c.get("match") or "NONE")
        n_key = c.get("n_key")
        hist_rows = list(c.get("rows") or [])
        parent = list(c.get("parent_trend_rows") or [])
        issued = c.get("knowledge_action") or "UNKNOWN"
        why = c.get("why") or "CONSULT"
    if issued not in ("WAIT", "UNKNOWN"):
        issued = "WAIT"

    board_of = _best_board()
    ranked = []
    for r in hist_rows:
        ranked.append({
            "strategy": r.get("strategy"),
            "n": r.get("n"),
            "TAKE": r.get("TAKE"),
            "depth": r.get("depth"),
            "vs_sitout": r.get("vs_sitout"),
            "mean_1h_take": r.get("mean_1h_take"),
            "mean_1h_skip": r.get("mean_1h_skip"),
            "board": board_of.get(str(r.get("strategy")), "UNTESTED"),
            "keep": False,
        })
    ranked.sort(key=lambda x: (
        DEPTH_PRI.get(str(x.get("depth")), 9),
        BOARD_PRI.get(str(x.get("board")), 9),
        -int(x.get("n") or 0),
        x["strategy"],
    ))
    report = {
        "ok": True,
        "version": VERSION,
        "phase": "I4_INTERFACE",
        "flag": tape,
        "fp": (c.get("fingerprint") or {}).get("key") if not explicit else None,
        "match": match,
        "n_key": n_key,
        "why": why,
        "knowledge_action": issued,
        "issued_action": issued,
        "rows": ranked,
        "parent_trend_rows": parent if match == "SPARSE_KEY" else [],
        "keep": False,
        "take": False,
        "live_enable": False,
        "laws": {
            "rank_cannot_take": True,
            "rank_cannot_keep": True,
            "rank_is_not_similarity": True,
            "sparse_key_does_not_inherit_parent": True,
            "consult_cannot_override_issued": True,
            "i4_is_interface": True,
        },
        "note": "Key-first rank. Sparse ≠ parent WASH. Issued WAIT/UNKNOWN. Rank ≠ trade.",
    }
    try:
        OUT.write_text(json.dumps(report, indent=2, default=str))
        report["saved"] = str(OUT)
    except Exception:
        report["saved"] = None
    return report


def print_rank(flag: Optional[str] = None) -> Dict[str, Any]:
    report = rank_state(flag)
    print(f"\nSTATE RANK  {report.get('version')}  (I4 interface)")
    print("=" * 64)
    print("Key first. Sparse ≠ parent WASH. Issued WAIT/UNKNOWN. Rank ≠ TAKE.")
    print(
        f"  tape={report.get('flag')}  match={report.get('match')}  "
        f"issued={report.get('issued_action')}  keep=False"
    )
    print(f"  why={report.get('why')}  fp={report.get('fp') or '—'}")
    print("-" * 64)
    rows = report.get("rows") or []
    if not rows:
        print("  (no hist rows — UNKNOWN is valid)")
    for r in rows:
        print(
            f"  {r.get('strategy'):<18} board={r.get('board'):<16} "
            f"n={r.get('n')} TAKE={r.get('TAKE')} depth={r.get('depth')}  "
            f"vs_sitout={r.get('vs_sitout')}"
        )
    parent = report.get("parent_trend_rows") or []
    if parent:
        print("  parent TREND (context only — not inherited)")
        for r in parent:
            print(f"    {r.get('strategy'):<16} TAKE={r.get('TAKE')} vs_sitout={r.get('vs_sitout')}")
    print("-" * 64)
    print("  I4 cannot TAKE. I5 paper TAKE is still blocked. Wave A stays WATCH.")
    if report.get("saved"):
        print(f"  saved: {report['saved']}")
    print("=" * 64)
    return report


def _best_board() -> Dict[str, str]:
    """Prefer WASH/SUITABLE over a later TESTED_UNKNOWN cell for the same strategy."""
    b = boards()
    best: Dict[str, str] = {}
    for name, rows in (b.get("boards") or {}).items():
        pri = BOARD_PRI.get(name, 9)
        for r in rows or []:
            key = str(r.get("strategy") or "")
            if not key:
                continue
            cur = best.get(key)
            if cur is None or pri < BOARD_PRI.get(cur, 9):
                best[key] = name
    return best
