"""Scientific research history (EXP-nnn). Separate from S5-H* live experiments."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

VERSION = "EXP-REG-v0.5"
OUT = Path("research_experiments.json")

EXPERIMENTS: List[Dict[str, Any]] = [
    {
        "id": "EXP-001",
        "question": "Does Donchian × TREND_UP outperform sit-out on 1h?",
        "data": "10 symbols × 1h ~1.17y",
        "period": "2025-06-28 → 2026-08-30",
        "result": "ASSET_CONDITIONAL",
        "detail": "HURT AVAX/LINK/ARB/RENDER; WASH ETH/SOL/XRP/AAVE/PAXG; thin BTC",
        "decision": "Do not promote.",
        "promote": False,
        "keep": False,
    },
    {
        "id": "EXP-002",
        "question": "Does Bollinger × COMPRESSION outperform sit-out on 1h?",
        "data": "10 × 1h",
        "period": "2025-06-28 → 2026-08-30",
        "result": "WASH_WHERE_ADEQUATE",
        "detail": "ADEQUATE books WASH. Live TAKE=0.",
        "decision": "Do not promote.",
        "promote": False,
        "keep": False,
    },
    {
        "id": "EXP-003",
        "question": "Does Hunter × TREND_UP produce TAKEs under Wave A?",
        "data": "10 × 1h + live",
        "period": "hist + live",
        "result": "NO_TAKE",
        "detail": "TAKE=0 on hist books and live.",
        "decision": "Do not enable TREND_UP.",
        "promote": False,
        "keep": False,
    },
    {
        "id": "EXP-004",
        "question": "Is BTC 15m observation-replay a year-scale book?",
        "data": "observation_replay_BTCUSD_15m.jsonl",
        "period": "2026-08-14 → 2026-08-30",
        "result": "NOT_A_YEAR",
        "detail": "span=15.5d n=161.",
        "decision": "Do not treat as year book.",
        "promote": False,
        "keep": False,
    },
    {
        "id": "EXP-005",
        "question": "Does ATR × TREND_UP outperform sit-out on 1h?",
        "data": "10 × 1h",
        "period": "2025-06-28 → 2026-08-30",
        "result": "ASSET_CONDITIONAL",
        "detail": "TAKE_HURT AAVE and RENDER.",
        "decision": "Do not kill family. Do not promote.",
        "promote": False,
        "keep": False,
    },
    {
        "id": "EXP-006",
        "question": "Does health_sweep match observation_v0 families?",
        "data": "lab run ef32846f",
        "period": "3m daily",
        "result": "ROSTER_MISMATCH",
        "detail": "Sweep roster ≠ Agent books.",
        "decision": "Do not ingest as CFG.",
        "promote": False,
        "keep": False,
    },
    {
        "id": "EXP-007",
        "question": "HAVE window phase mix?",
        "data": "BTC 1h replay",
        "period": "2025-06-28 → 2026-08-30",
        "result": "YES_BUT_DRAWDOWN_HEAVY",
        "detail": "PRE_LEAD=180 LEAD_IN=366 PEAK_BAND=90 DRAWDOWN=1878/2514.",
        "decision": "No fake 2021 candles.",
        "promote": False,
        "keep": False,
    },
    {
        "id": "EXP-008",
        "question": "BTC 1h TAKE vs SKIP by EP-2025-26 phase?",
        "data": "observation_replay.jsonl setups",
        "period": "HAVE",
        "result": "DRAWDOWN_DOMINATED_NO_PROMOTE",
        "detail": "Bollinger DRAWDOWN TAKE -0.07 vs SKIP +0.07. PEAK TAKEs empty.",
        "decision": "Do not promote.",
        "promote": False,
        "keep": False,
    },
    {
        "id": "EXP-009",
        "question": "ETH 1h same slice — does BTC ranking survive?",
        "data": "observation_replay_ETHUSD.jsonl",
        "period": "HAVE",
        "result": "ASSET_X_PHASE_DISAGREES",
        "detail": "Bollinger DRAWDOWN ETH TAKE +0.19 vs SKIP -0.05. Donchian DRAWDOWN TAKE hurts.",
        "decision": "Conditional boards only.",
        "promote": False,
        "keep": False,
    },
    {
        "id": "EXP-011",
        "question": "SOL 1h same slice — third major?",
        "data": "observation_replay_SOLUSD.jsonl",
        "period": "HAVE",
        "result": "BREAKOUTS_HURT_IN_DRAWDOWN",
        "detail": (
            "Donchian DRAWDOWN TAKE n=18 +1h=-0.09 vs SKIP +0.12. "
            "Donchian LEAD_IN TAKE n=12 +1h=-0.35 vs SKIP +0.34. "
            "Bollinger DRAWDOWN TAKE n=44 +1h=-0.12 vs SKIP +0.06 (agrees BTC, disagrees ETH). "
            "Hunter DRAWDOWN TAKE=0. Hunter PEAK n=1 +1h=-5.50."
        ),
        "decision": "Stop more 1h coins on this slice. Majors circuit is enough. EXP-010 still reserved.",
        "promote": False,
        "keep": False,
    },
]


def registry() -> Dict[str, Any]:
    out = {
        "ok": True,
        "version": VERSION,
        "keep": False,
        "law": "Raw rolls. Intelligence is versioned. No daily full re-analysis.",
        "experiments": EXPERIMENTS,
        "closed_no_promote": [e["id"] for e in EXPERIMENTS],
        "next_id": "EXP-012",
        "next_candidates": [
            "Leave T1 watch running",
            "Ananta PIT warehouse → 2021-09-10 (external)",
            "EXP-010 Donchian dc_entry when Lab honors the key",
            "Do not add AVAX/LINK/ARB episode slices on 1h",
        ],
        "note": "EXP-010 reserved for config bridge. Not used.",
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
        print(f"  {e['id']}  {e['result']}  promote={e['promote']}")
        print(f"    {e['question']}")
        print(f"    {e['detail']}")
    print("-" * 64)
    for c in r["next_candidates"]:
        print(f"  • {c}")
    print(f"  saved={r.get('saved')}  keep=False")
    print("=" * 64)
    print()
    return r
