"""Intelligence phases I1–I6. Tape-independent lock.

I2 hist is LOCKED. I3–I6 are named interfaces. None of them KEEP.
CLI: lab phases
"""
from __future__ import annotations

from typing import Any, Dict, List

CURRENT = "I2_LOCKED"

PHASES: List[Dict[str, str]] = [
    {
        "id": "I1",
        "name": "EVIDENCE_LAB",
        "status": "DONE",
        "means": "Wave A watch, replay, DQ, Universe, memory, fingerprints, consult",
    },
    {
        "id": "I2",
        "name": "RESEARCH_EXPANSION",
        "status": "LOCKED",
        "means": "Donchian/ATR/Keltner hist shadow. SUITABLE=0. No turtle/ema.",
    },
    {
        "id": "I3",
        "name": "OPPORTUNITY_INTELLIGENCE",
        "status": "INTERFACE",
        "means": "Scanner + fair-value + catalysts. Refuse live scan/execute.",
    },
    {
        "id": "I4",
        "name": "DECISION_INTELLIGENCE",
        "status": "INTERFACE",
        "means": "Rank for a tape flag from memory. Issued WAIT/UNKNOWN only.",
    },
    {
        "id": "I5",
        "name": "FORWARD_PAPER",
        "status": "BLOCKED",
        "means": "Human-gated paper TAKE. Needs SUITABLE cell + vs_sitout edge.",
    },
    {
        "id": "I6",
        "name": "EARNED_AUTONOMY",
        "status": "BLOCKED",
        "means": "SAFE/MODERATE/AGGRESSIVE are parameters, not authority.",
    },
]


def snapshot() -> Dict[str, Any]:
    return {
        "ok": True,
        "current": CURRENT,
        "keep": False,
        "authority_earned": False,
        "wave_a": "WATCH",
        "i2_locked": True,
        "phases": list(PHASES),
        "data_dependent_remaining": [
            "More live tape for sparse keys (n>=5) and live TAKE samples (still WATCH).",
            "Re-open I2 only if a cell is SUITABLE or live DQ contradicts hist WASH.",
            "I5 paper TAKE only after SUITABLE + TAKE_GT_SITOUT + human confirm.",
            "I6 autonomy only after I5 DQ beats sit-out forward.",
        ],
        "data_independent_now": [
            "I3/I4/I5/I6 contracts (this package).",
            "Research rank from existing memory.",
            "Consult-DQ key slices on existing consult_log.",
        ],
        "laws": {
            "take_is_not_keep": True,
            "coverage_is_not_intelligence": True,
            "i2_hist_baseline_locked": True,
            "scanner_is_not_live_enable": True,
            "rank_cannot_take": True,
            "paper_take_is_human_gated": True,
            "autonomy_is_earned": True,
        },
    }


def print_phases() -> Dict[str, Any]:
    report = snapshot()
    print(f"\nINTELLIGENCE PHASES  current={report['current']}")
    print("=" * 64)
    print("Tape-independent lock. Wave A watch continues. Not KEEP.")
    for p in report["phases"]:
        mark = {"DONE": "done", "LOCKED": "LOCK", "INTERFACE": "ifce", "BLOCKED": "wait"}[p["status"]]
        print(f"  {p['id']:<4} {mark:<4}  {p['name']:<28} {p['means']}")
    print("-" * 64)
    print("  Remaining that NEED more tape: sparse-key n, live TAKE (WATCH), I5/I6.")
    print("  I3 scan / fair-value execute / turtle / TREND_UP / KEEP = still no.")
    print("=" * 64)
    return report
