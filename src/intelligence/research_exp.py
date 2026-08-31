"""Scientific research history (EXP-nnn). Separate from S5-H* live experiments.

Raw warehouse rolls on Ananta. Intelligence is versioned here. Not KEEP.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

VERSION = "EXP-REG-v0.4"
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
    {
        "id": "EXP-006",
        "question": "Does Ananta daily health_sweep score the same families as Agent observation books?",
        "data": "lab run ef32846f-1937-457d-9043-d4520ad205a9",
        "period": "3m daily BTC/ETH/SOL",
        "strategy_version": "Lab stock health_sweep",
        "method": "list strategies[] keys on latest DONE health_sweep",
        "result": "ROSTER_MISMATCH",
        "detail": "Sweep roster ≠ observation_v0 roster. Do not ingest as CFG.",
        "decision": "Do not ingest sweep as CFG evidence.",
        "promote": False,
        "keep": False,
    },
    {
        "id": "EXP-007",
        "question": "Does the HAVE window contain lead-in + peak + drawdown phase mix?",
        "data": "observation_replay.jsonl BTC 1h stride=4",
        "period": "2025-06-28 → 2026-08-30",
        "strategy_version": "n/a — date buckets only",
        "method": "EPISODE-TAG-v0 cuts vs obs.ts",
        "result": "YES_BUT_DRAWDOWN_HEAVY",
        "detail": "PRE_LEAD=180 LEAD_IN=366 PEAK_BAND=90 DRAWDOWN=1878 / 2514.",
        "decision": "Research on HAVE only. Do not invent 2021 candles.",
        "promote": False,
        "keep": False,
    },
    {
        "id": "EXP-008",
        "question": "On BTC 1h HAVE window, do TAKE-eq setups beat SKIP_SETUP inside each EP-2025-26 phase?",
        "data": "observation_replay.jsonl setups only",
        "period": "2025-06-28 → 2026-08-30",
        "strategy_version": "stock observation_v0 evaluators",
        "method": "EPISODE-SLICE-v0 +1h TAKE vs SKIP by phase",
        "result": "DRAWDOWN_DOMINATED_NO_PROMOTE",
        "detail": "Bollinger DRAWDOWN TAKE n=39 +1h=-0.0704 vs SKIP +0.0651. Donchian DRAWDOWN TAKE ≤ SKIP. PEAK TAKEs empty.",
        "decision": "Do not promote. Do not rewrite from DRAWDOWN-heavy BTC.",
        "promote": False,
        "keep": False,
    },
    {
        "id": "EXP-009",
        "question": "Same phase slice on ETH 1h — does BTC ranking survive?",
        "data": "observation_replay_ETHUSD.jsonl setups only",
        "period": "2025-06-28 → 2026-08-30",
        "strategy_version": "stock observation_v0 evaluators",
        "method": "EPISODE-SLICE-v0 +1h TAKE vs SKIP by phase",
        "result": "ASSET_X_PHASE_DISAGREES",
        "detail": (
            "Bollinger DRAWDOWN ETH TAKE n=31 +1h=+0.1907 vs SKIP -0.0476 (opposite BTC). "
            "Donchian DRAWDOWN ETH TAKE n=23 +1h=-0.1674 vs SKIP +0.048 (TAKE hurts). "
            "ATR DRAWDOWN TAKE n=8 +1h=-0.357 vs SKIP +0.104. Hunter TAKEs still anecdotes."
        ),
        "decision": "Do not KEEP Bollinger from ETH DRAWDOWN alone. Do not kill Donchian from ETH DRAWDOWN alone. Conditional boards only.",
        "promote": False,
        "keep": False,
    },
]

LAYERS = {
    "A_RAW": "Ananta rolling PIT warehouse. Append daily. Target 2021-09-10 when candles exist.",
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
        "next_id": "EXP-011",
        "next_candidates": [
            "EXP-011 SOL 1h strategy × EP-2025-26 phase (print_slice('sol'))",
            "EXP-010 reserved — Donchian dc_entry after Lab honors parameter",
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
