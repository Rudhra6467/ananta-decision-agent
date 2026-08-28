"""Strategy definition cards — I2-lite.

Name the classifiers. Do not rewrite them to remove a clash.
Donchian is the first I2 family: hist shadow after Ananta replay, not live.

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
            "status": "HIST_SCORED",
            "live_watch": False,
            "keep": False,
            "rewrite": False,
            "observation_v0": True,
            "evaluator": "ananta.declarative_engine.evaluate(DECLARATIVE['donchian-breakout'])",
            "thesis": "Channel breakout continuation",
            "family": "breakout",
            "classifiers": {
                "ananta_regime": {
                    "name": "TREND_UP (thesis)",
                    "basis": "Breakout DNA — not routed live",
                    "role": "thesis / research gate",
                },
                "setup_rule": {
                    "name": "Donchian high/low channel",
                    "basis": "Close > 20-bar Donchian high (dc_entry=20). Ananta declarative_engine.",
                    "role": "setup detector",
                },
                "market_truth_trend": {
                    "name": "SMA-20 independent trend_flag",
                    "basis": "Same Market Truth as continuation",
                    "role": "external tape",
                },
            },
            "known_clash": None,
            "blocked_by": None,
            "alignment": {
                "kind": "THESIS_TREND_UP_VS_INDEPENDENT_UP",
                "hist_setups": 126,
                "tape": {"UP": 126},
                "take_n": 28,
                "depth": "THIN",
                "plus_1h": "INSUFFICIENT_EVIDENCE",
                "note": "Unlike continuation, Donchian setups sit on SMA-20 UP. Not KEEP.",
            },
            "cell_finding": {
                "kind": "TREND_DOWN_CELL_VS_INDEPENDENT_UP",
                "n": 15,
                "note": "15 setups when Ananta said TREND_DOWN and tape was UP; research-filtered. Finding, not a rewrite.",
            },
            "note": "I2 hist scored. TAKE-eq 28 on TREND_UP. THIN. Not Wave A. Not live. Not KEEP.",
        },
        {
            "strategy": "atr-breakout",
            "phase": "I2",
            "status": "HIST_SCORED",
            "live_watch": False,
            "keep": False,
            "rewrite": False,
            "observation_v0": True,
            "evaluator": "ananta.declarative_engine.evaluate(DECLARATIVE['atr-breakout'])",
            "thesis": "Volatility breakout",
            "family": "breakout",
            "classifiers": {
                "ananta_regime": {
                    "name": "TREND_UP (thesis)",
                    "basis": "Breakout DNA — not routed live",
                    "role": "thesis / research gate",
                },
                "setup_rule": {
                    "name": "ATR channel breakout",
                    "basis": "Ananta declarative_engine DECLARATIVE['atr-breakout']",
                    "role": "setup detector",
                },
                "market_truth_trend": {
                    "name": "SMA-20 independent trend_flag",
                    "basis": "Same Market Truth as Donchian",
                    "role": "external tape when replay exists",
                },
            },
            "known_clash": None,
            "blocked_by": None,
            "alignment": {
                "kind": "THESIS_TREND_UP_TAKE_EQ",
                "hist_setups": 46,
                "take_n": 9,
                "depth": "ANECDOTE",
                "plus_1h": "INSUFFICIENT_EVIDENCE",
                "note": "TAKE-eq only in TREND_UP (9). Tape alignment after fingerprints. Not KEEP.",
            },
            "note": "I2 hist scored. TAKE-eq 9. ANECDOTE. Not Wave A. Not live. Not KEEP.",
        },
        {
            "strategy": "keltner-breakout",
            "phase": "I2",
            "status": "HIST_SCORED",
            "live_watch": False,
            "keep": False,
            "rewrite": False,
            "observation_v0": True,
            "evaluator": "ananta.declarative_engine.evaluate(DECLARATIVE['keltner-breakout'])",
            "thesis": "Keltner expansion",
            "family": "breakout",
            "classifiers": {
                "ananta_regime": {
                    "name": "TREND_UP (thesis)",
                    "basis": "DNA also lists COMPRESSION — named fact, not the research gate",
                    "role": "thesis / research gate",
                },
                "setup_rule": {
                    "name": "Keltner channel",
                    "basis": "Ananta declarative_engine DECLARATIVE['keltner-breakout']",
                    "role": "setup detector",
                },
                "market_truth_trend": {
                    "name": "SMA-20 independent trend_flag",
                    "basis": "Same Market Truth as Donchian",
                    "role": "external tape when replay exists",
                },
            },
            "known_clash": None,
            "blocked_by": None,
            "alignment": {
                "kind": "THESIS_TREND_UP_TAKE_EQ",
                "hist_setups": 49,
                "take_n": 17,
                "depth": "THIN",
                "plus_1h": "INSUFFICIENT_EVIDENCE",
                "note": "TAKE-eq only in TREND_UP (17). COMPRESSION DNA ≠ gate. Not KEEP.",
            },
            "note": "I2 hist scored. TAKE-eq 17. THIN. Not Wave A. Not live. Not KEEP.",
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
        elif c.get("alignment"):
            a = c["alignment"]
            print(
                f"      aligned={a.get('kind')}  "
                f"tape={a.get('tape')}  take_n={a.get('take_n')}  "
                f"+1h={a.get('plus_1h')}"
            )
        elif c.get("blocked_by"):
            print(f"      blocked={c['blocked_by']}  evaluator={c.get('evaluator')}")
