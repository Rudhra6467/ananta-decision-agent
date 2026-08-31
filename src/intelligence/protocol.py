"""How Agent Ananta development is run. Not KEEP. Not a strategy."""
from __future__ import annotations

from typing import Any, Dict

VERSION = "PROTOCOL-v1"

LAW = (
    "Aggressive discovery. Conservative capital. Continuous learning. "
    "Explicit uncertainty. Batch engineering. Stop only at a real gate."
)

LANES = {
    "A_AUTONOMOUS_ENGINEERING": (
        "Inspect, implement, test on existing books, write artifacts, "
        "compare, document. Batch in one work package."
    ),
    "B_MACHINE_VERIFICATION": (
        "Live watcher, live ledgers, process health, env-only behaviour. "
        "One batched command list. Wait."
    ),
    "C_HUMAN_AUTHORITY": (
        "TAKE enable, KEEP, capital, autonomy, override evidence gates."
    ),
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
    "WP-T2-15M-YEAR — budgeted BTC 15m 1y sibling book when a session can run it",
    "WP-T2-4H-WIRE — only after Ananta observation-replay emits 4h rows",
    "WP-T2-YEARS — Ananta PIT history beyond 1.17y; Agent does not invent bars",
    "WP-T3-STATE — richer state on existing books (no new coin)",
    "WP-T4-SCAN-CANDIDATE — offline candidate objects from fingerprints + desk",
    "WP-T4-FV-NAMED — more PIT methods only if fields exist",
    "WP-I4-RANK-LIVE — rank uses 10-book desk; issued still WAIT/UNKNOWN",
    "WP-I5 — blocked until SUITABLE + forward vs-sit-out edge",
]


def spec() -> Dict[str, Any]:
    return {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "law": LAW,
        "lanes": LANES,
        "report": REPORT_SECTIONS,
        "next_packages": NEXT_PACKAGES,
        "stop_only_when": [
            "need live Mac state",
            "need human authority",
            "Ananta API cannot serve the slice",
        ],
    }


def print_protocol() -> Dict[str, Any]:
    r = spec()
    print(f"\nDEV PROTOCOL  {r['version']}")
    print("=" * 64)
    print(r["law"])
    print("-" * 64)
    for k, v in r["lanes"].items():
        print(f"  {k}")
        print(f"    {v}")
    print("-" * 64)
    print("  Next packages:")
    for p in r["next_packages"]:
        print(f"    • {p}")
    print("=" * 64)
    print()
    return r
