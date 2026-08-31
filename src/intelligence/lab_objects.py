"""Four permanent research objects. Not KEEP. Not a score dump."""
from __future__ import annotations

from typing import Any, Dict

VERSION = "LAB-OBJECTS-v0"

LAW = (
    "We are a strategy research laboratory that produces evidence for Agent Ananta. "
    "Not a bot that knows 20 strategies. Search budget is recorded. Held-out never tunes. "
    "Win after cost is primary; MAE/expectancy/n/vs-sit-out travel with it. "
    "Lab recommendation ≠ TAKE. Health sweep ≠ CFG row."
)

OBJECTS = {
    "STRATEGY_REGISTRY": "universe_specs.catalog — families exist; live_watch=False",
    "CONFIG_REGISTRY": "cfg_catalog — named config_id; PENDING until parameter_honored",
    "EXPERIMENT_LEDGER": "research_exp EXP-nnn — question, data, method, result, promote",
    "EVIDENCE_LIBRARY": "knowledge_grid + evidence_desk — queryable; SUITABLE=0",
}

NOT_NOW = (
    "market episodes",
    "evidence decay",
    "50 more strategies",
    "LLM price",
    "live scanner execute",
    "autonomy",
    "India/US/Canada ingest",
)

CHAIN = "config → EXP → IS → LOCK → OOS → cost → metrics → library → consult"

BLOCKED = (
    "EXP-010 Donchian lookbacks: Ananta does not honor dc_entry on observation-replay; "
    "health_sweep has no Donchian and no CFG must-have fields."
)


def print_objects() -> Dict[str, Any]:
    print(f"\nLAB OBJECTS  {VERSION}")
    print("=" * 64)
    print(LAW)
    print("-" * 64)
    for k, v in OBJECTS.items():
        print(f"  {k}")
        print(f"    {v}")
    print("-" * 64)
    print(f"  chain: {CHAIN}")
    print(f"  blocked: {BLOCKED}")
    print(f"  not now: {', '.join(NOT_NOW)}")
    print("  KEEP=False  I5 blocked  Wave A WATCH")
    print("=" * 64)
    print()
    return {"ok": True, "version": VERSION, "keep": False, "blocked": BLOCKED}
