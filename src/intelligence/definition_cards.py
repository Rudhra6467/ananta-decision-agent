"""Strategy definition cards — I2-lite.

Name the classifiers. Do not rewrite them to remove a clash.
Donchian is the first I2 family: spec only, no observation_v0, not live.

CLI surfaces these on `lab universe`.
"""
from __future__ import annotations

from typing import Any, Dict, List

VERSION = "DEF-v0"
I2_FAMILY = "donchian-breakout"

LAWS = {
    "definition_is_not_evidence": True,
    "clash_is_not_a_rewrite": True,
    "i2_family_is_not_live": True,
    "keep_forbidden": True,
    "coverage_is_not_intelligence": True,
}


def cards() -> List[Dict[str, Any]]:
    return [
        {
            "strategy": "continuation",
            "phase": "I2-lite",
            "status": "NAMED",
            "live_watch": False,
            "keep": False,
            "rewrite": False,
            "thesis": "Buy shallow dips in a confirmed uptrend",
            "classifiers": {
                "ananta_regime": {
                    "name": "TREND_UP",
                    "basis": "Ananta continuation / 50-EMA established uptrend",
                    "role": "router gate (hypothesis)",
                },
                "market_truth_trend": {
                    "name": "SMA-20 independent trend_flag",
                    "basis": "Market Truth fingerprint trend_flag UP/DOWN/FLAT",
                    "role": "external tape",
                },
            },
            "known_clash": {
                "kind": "TREND_UP_GATE_VS_INDEPENDENT_DOWN",
                "hist_setups": 40,
                "tape": {"DOWN": 21, "FLAT": 13, "UP": 6},
                "take_n": 7,
                "take_tape": {"FLAT": 4, "DOWN": 2, "UP": 1},
                "note": "50-EMA TREND_UP ≠ SMA-20 UP. Finding, not a rewrite.",
            },
        },
        {
            "strategy": "donchian-breakout",
            "phase": "I2",
            "status": "SPEC_ONLY",
            "live_watch": False,
            "keep": False,
            "rewrite": False,
            "observation_v0": False,
            "evaluator": None,
            "thesis": "Channel breakout continuation",
            "family": "breakout",
            "classifiers": {
                "ananta_regime": {
                    "name": "TREND_UP (thesis)",
                    "basis": "Breakout DNA — not routed live",
                    "role": "thesis only",
                },
                "setup_rule": {
                    "name": "Donchian high/low channel",
                    "basis": "Close breaks N-bar high (long) / low (short). N unspecified until Ananta evaluator exists.",
                    "role": "setup detector — DATA_GAP",
                },
                "market_truth_trend": {
                    "name": "SMA-20 independent trend_flag",
                    "basis": "Same Market Truth as continuation",
                    "role": "external tape when replay exists",
                },
            },
            "known_clash": None,
            "blocked_by": "NO_OBSERVATION_REPLAY",
            "note": "First I2 family. Catalogued. Not running. Not Wave A.",
        },
    ]


def card_for(strategy: str) -> Dict[str, Any] | None:
    key = (strategy or "").lower()
    for c in cards():
        if c["strategy"] == key:
            return c
    return None


def print_definitions() -> None:
    print("  DEFINITION CARDS  (classifiers named. Not KEEP. Not a rewrite.)")
    for c in cards():
        clash = c.get("known_clash") or {}
        print(
            f"    {c['strategy']:<22} phase={c['phase']:<8} status={c['status']:<10} "
            f"live={c['live_watch']} keep={c['keep']}"
        )
        if clash:
            print(
                f"      clash={clash.get('kind')}  "
                f"tape={clash.get('tape')}  take_n={clash.get('take_n')}"
            )
        elif c.get("blocked_by"):
            print(f"      blocked={c['blocked_by']}  evaluator={c.get('evaluator')}")
