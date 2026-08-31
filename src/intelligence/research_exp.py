"""Scientific research history (EXP-nnn). Separate from S5-H* live experiments.

Raw warehouse rolls on Ananta. Intelligence is versioned here. Not KEEP.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

VERSION = "EXP-REG-v0"
OUT = Path("research_experiments.json")

EXPERIMENTS: List[Dict[str, Any]] = [
    {
        "id": "EXP-001",
        "question": "Does Donchian × TREND_UP outperform sit-out on 1h?",
        "data": "10 symbols × 1h ~1.17y",
        "period": "2025-06-28 → 2026-08-30",
        "strategy_version": "donchian-breakout / I2 hist shadow",
        "method": "observation_v0 stride=4 +1h vs sit-out",
        "result": "ASSET_CONDITIONAL",
        "detail": "HURT AVAX/LINK/ARB/RENDER; WASH ETH/SOL/XRP/AAVE/PAXG; thin BTC",
        "decision": "Do not promote. Do not rewrite because alts hurt.",
        "promote": False,
        "keep": False,
    },
    {
        "id": "EXP-002",
        "question": "Does Bollinger × COMPRESSION outperform sit-out on 1h?",
        "data": "same 10 × 1h books",
        "period": "2025-06-28 → 2026-08-30",
        "strategy_version": "bollinger-mr declarative",
        "method": "observation_v0 +1h vs sit-out",
        "result": "WASH_WHERE_ADEQUATE",
        "detail": "ADEQUATE books WASH. Live TAKE=0.",
        "decision": "Do not promote. Shadow only.",
        "promote": False,
        "keep": False,
    },
    {
        "id": "EXP-003",
        "question": "Does Hunter × TREND_UP produce TAKEs under Wave A?",
        "data": "10 × 1h + live watch",
        "period": "hist 1.17y + live",
        "strategy_version": "hunter primary; Wave A REVERSAL only",
        "method": "TAKE-eq count",
        "result": "NO_TAKE",
        "detail": "TAKE=0 on all 10 hist books and live.",
        "decision": "Do not enable TREND_UP. Do not rewrite Hunter.",
        "promote": False,
        "keep": False,
    },
    {
        "id": "EXP-004",
        "question": "Is BTC 15m observation-replay a year-scale book?",
        "data": "observation_replay_BTCUSD_15m.jsonl",
        "period": "2026-08-14 → 2026-08-30",
        "strategy_version": "same evaluators",
        "method": "timeframe=15m max_bars=800 stride=8",
        "result": "NOT_A_YEAR",
        "detail": "span=15.5d n=161 usable_1y=False.",
        "decision": "Do not treat as year book.",
        "promote": False,
        "keep": False,
    },
    {
        "id": "EXP-005",
        "question": "Does ATR × TREND_UP outperform sit-out on 1h?",
        "data": "same 10 × 1h books",
        "period": "2025-06-28 → 2026-08-30",
        "strategy_version": "atr-breakout I2 hist shadow",
        "method": "+1h vs sit-out",
        "result": "ASSET_CONDITIONAL",
        "detail": "TAKE_HURT AAVE and RENDER. Others thin.",
        "decision": "Do not kill family. Do not promote.",
        "promote": False,
        "keep": False,
    },
]

LAYERS = {
    "A_RAW": "Ananta rolling PIT warehouse. Append daily. Target 3-4y when candles exist.",
    "B_RESEARCH": "Versioned replay + Experiment ID. Not daily full-market re-score.",
    "C_KNOWLEDGE": "Compact query objects. Agent does not rescan millions of candles.",
}


def registry() -> Dict[str, Any]:
    out = {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "law": "Raw rolls. Intelligence is versioned. No daily full re-analysis.",
        "layers": LAYERS,
        "experiments": EXPERIMENTS,
        "closed_no_promote": [e["id"] for e in EXPERIMENTS],
        "next_id": "EXP-006",
        "next_candidates": [
            "EXP-006 live WAIT vs COSTLY by fingerprint (consult-dq, not TAKE)",
            "EXP-007 4h replay once Ananta wires observation-replay",
            "EXP-008 any ADEQUATE cell beat sit-out on >=2 books?",
        ],
        "note": "S5-H* live experiment catalog stays in experiments.py. Do not merge.",
    }
    OUT.write_text(json.dumps(out, indent=2, default=str))
    out["saved"] = str(OUT)
    return out


def print_research() -> Dict[str, Any]:
    r = registry()
    print(f"\nRESEARCH EXP  {r['version']}")
    print("=" * 64)
    print(r["law"])
    print("-" * 64)
    for e in r["experiments"]:
        print(f"  {e['id']}  {e['question']}")
        print(f"    result={e['result']}  promote={e['promote']}")
        print(f"    {e['detail']}")
        print(f"    → {e['decision']}")
    print("-" * 64)
    print("  next candidates:")
    for c in r["next_candidates"]:
        print(f"    • {c}")
    print(f"  saved={r.get('saved')}  keep=False")
    print("=" * 64)
    print()
    return r
