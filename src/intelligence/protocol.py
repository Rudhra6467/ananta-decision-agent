"""How Agent Ananta development is run. Not KEEP. Not a strategy."""
from __future__ import annotations

from typing import Any, Dict

VERSION = "PROTOCOL-v1.1"

LAW = (
    "Aggressive discovery. Conservative capital. "
    "Raw data rolls on Ananta. Intelligence is versioned and selectively recomputed. "
    "No daily full-market re-analysis. Experiment IDs required. "
    "Batch engineering. Stop only at a real gate."
)

LANES = {
    "A_AUTONOMOUS_ENGINEERING": (
        "Inspect, implement, test on existing books, write artifacts. Batch one package."
    ),
    "B_MACHINE_VERIFICATION": (
        "Live watcher, live ledgers, process health. One batched command list."
    ),
    "C_HUMAN_AUTHORITY": (
        "TAKE enable, KEEP, capital, autonomy, override evidence gates."
    ),
}

LAYERS = {
    "A_RAW": "Ananta rolling PIT warehouse. Append daily. 3-4y when candles exist.",
    "B_RESEARCH": "Versioned replay of selected windows. EXP-nnn. Not daily rescore-all.",
    "C_KNOWLEDGE": "Compact objects the agent queries. Not millions of candles.",
}

REPORT_SECTIONS = [
    "A. Objective",
    "B. Work completed",
    "C. Evidence discovered",
    "D. Files/components changed",
    "E. Validation",
    "F. What I need from Travis",
    "G. Decision/Gate",
    "H. What is NOT being changed",
    "I. Next work package",
    "J. STOP/CONTINUE",
]

NEXT_PACKAGES = [
    "WP-EXP-006 — live WAIT vs COSTLY by fingerprint (consult-dq). Not TAKE.",
    "WP-1-RAW — Ananta daily append + coverage truth (warehouse, not Agent jsonl).",
    "WP-T2-4H-WIRE — only after Ananta observation-replay emits 4h rows",
    "WP-T2-YEARS — Ananta PIT beyond 1.17y; Agent does not invent bars",
    "WP-I5 — blocked until SUITABLE + forward vs-sit-out edge",
]


def spec() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "law": LAW,
        "layers": LAYERS,
        "lanes": LANES,
        "report": REPORT_SECTIONS,
        "next_packages": NEXT_PACKAGES,
        "experiments_module": "src.intelligence.research_exp",
        "s5_module": "src.intelligence.experiments",
    }


def print_protocol() -> Dict[str, Any]:
    r = spec()
    print(f"\nDEV PROTOCOL  {r['version']}")
    print("=" * 64)
    print(r["law"])
    print("-" * 64)
    for k, v in r["layers"].items():
        print(f"  {k}: {v}")
    print("-" * 64)
    print("  Next packages:")
    for p in r["next_packages"]:
        print(f"    • {p}")
    print("=" * 64)
    print()
    return r
