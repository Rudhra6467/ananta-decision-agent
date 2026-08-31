"""Donchian parameter truth from Ananta declarative_defs. Not KEEP."""
from __future__ import annotations

from typing import Any, Dict

VERSION = "DONCHIAN-KEYS-v0"

# From Ananta backend/strategy/declarative_defs.py — donchian-breakout
STOCK = {
    "family": "donchian-breakout",
    "dc_entry": 20,
    "dc_exit": 10,
    "config_id": "donchian-dc20-dc10-v1",
}

BUDGET_DC_ENTRY = (20, 30, 40, 55, 80)

LAW = (
    "Ananta lab.optimize grid keys are set: and prof: (risk + exit profiles). "
    "Declarative knobs (dc_entry, dc_exit) are ParamSpec engine_backed=False. "
    "POST walk_forward with a fake lookback key would not honor parameters. "
    "Do not POST EXP-010 until Ananta accepts decl:donchian-breakout:dc_entry."
)


def print_keys() -> Dict[str, Any]:
    out = {
        "ok": True,
        "version": VERSION,
        "stock": STOCK,
        "budget_dc_entry": list(BUDGET_DC_ENTRY),
        "optimize_can_sweep_dc_entry": False,
        "observation_replay_honors_lookback": False,
        "exp010_post": False,
        "parameter_honored_for_stock_defaults": True,
        "parameter_honored_for_lb_variants": False,
        "keep": False,
        "law": LAW,
    }
    print(f"\nDONCHIAN KEYS  {VERSION}")
    print("=" * 64)
    print(LAW)
    print("-" * 64)
    print(f"  stock dc_entry={STOCK['dc_entry']} dc_exit={STOCK['dc_exit']} "
          f"id={STOCK['config_id']}")
    print(f"  budget dc_entry={BUDGET_DC_ENTRY}")
    print("  optimize sweep dc_entry: False")
    print("  EXP-010 POST: blocked")
    print("  health_sweep cards = stock config only")
    print("=" * 64)
    print()
    return out
