"""I4 research rank — given this tape, order capabilities from memory.

Not similarity. Not KEEP. Issued action is WAIT or UNKNOWN. Never TAKE.
Uses existing lookup + boards + consult. Independent of new tape.

CLI: lab rank-state [UP|DOWN|live]
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from src.intelligence.boards import boards
from src.intelligence.consult import consult
from src.intelligence.lookup import lookup

VERSION = "RANK-v0"
OUT = Path("state_rank.json")


def rank_state(flag: Optional[str] = None, *, source: str = "live") -> Dict[str, Any]:
    c = consult(source=source, write_snapshot=False, skip_log=True)
    tape = str(flag or c.get("flag") or "UNKNOWN").upper()
    if tape in ("LIVE", "NOW", ""):
        tape = str(c.get("flag") or "UNKNOWN")
    hist = lookup(tape, "replay") if tape not in ("UNKNOWN", "NONE", "") else {"rows": []}
    b = boards()
    board_of = {}
    for name, rows in (b.get("boards") or {}).items():
        for r in rows or []:
            board_of[str(r.get("strategy"))] = name
    ranked = []
    for r in hist.get("rows") or []:
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
    # Prefer evidence depth, never promote TAKE_GT_SITOUT to issued TAKE.
    depth_rank = {"SOLID": 0, "ADEQUATE": 1, "THIN": 2, "ANECDOTE": 3, "NONE": 4}
    ranked.sort(key=lambda x: (depth_rank.get(str(x.get("depth")), 9), -int(x.get("n") or 0), x["strategy"]))
    k_action = c.get("knowledge_action") or "UNKNOWN"
    if k_action not in ("WAIT", "UNKNOWN"):
        k_action = "WAIT"
    report = {
        "ok": True,
        "version": VERSION,
        "phase": "I4_INTERFACE",
        "flag": tape,
        "match": c.get("match"),
        "n_key": c.get("n_key"),
        "knowledge_action": k_action,
        "issued_action": k_action,
        "rows": ranked,
        "keep": False,
        "take": False,
        "live_enable": False,
        "laws": {
            "rank_cannot_take": True,
            "rank_cannot_keep": True,
            "rank_is_not_similarity": True,
            "consult_cannot_override_issued": True,
            "i4_is_interface": True,
        },
        "note": "Research order for this tape. Issued WAIT/UNKNOWN. Rank ≠ trade.",
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
    print("Memory order for this tape. Issued WAIT/UNKNOWN. Rank ≠ TAKE. Not KEEP.")
    print(
        f"  tape={report.get('flag')}  match={report.get('match')}  "
        f"issued={report.get('issued_action')}  keep=False"
    )
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
    print("-" * 64)
    print("  I4 cannot TAKE. I5 paper TAKE is still blocked. Wave A stays WATCH.")
    if report.get("saved"):
        print(f"  saved: {report['saved']}")
    print("=" * 64)
    return report
