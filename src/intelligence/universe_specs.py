"""Strategy Research Universe v1 — specifications, not bots.

Thesis (DNA) ≠ router ≠ Wave A policy ≠ observation coverage.
A spec is a capability card. It does not enable, KEEP, or enter live watch.
"""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

# Replay we actually have today (Donchian after Ananta I2 shadow + lab replay).
COVERED_STRATEGIES = ("hunter", "squeeze", "bollinger-mr", "continuation", "donchian-breakout")
COVERED_ASSETS = ("BTC/USD",)
COVERED_TIMEFRAMES = ("1h",)

# Ananta StrategySchema.version where known. Missing = DATA_GAP, never invented.
STRATEGY_VERSIONS = {
    "hunter": "1.0.0",
    "squeeze": "1.0.0",
    "continuation": "1.0.0",
    "bollinger-mr": "1.0.0",
}

EVALUATORS = {
    "hunter": "ananta.primary_layer.evaluate_primary",
    "squeeze": "ananta.squeeze.evaluate_squeeze",
    "bollinger-mr": "ananta.declarative_engine.evaluate(DECLARATIVE['bollinger-mr'])",
    "continuation": "ananta.continuation.evaluate_continuation",
    "donchian-breakout": "ananta.declarative_engine.evaluate(DECLARATIVE['donchian-breakout'])",
}

REGIME_CLASSIFIER = "ananta.regime.classify_regime"
REGIME_VERSION = None  # DATA_GAP until Ananta stamps a classifier version


ASSETS = ("BTC/USD", "ETH/USD")
TIMEFRAMES = ("1h", "15m")
REGIMES = (
    "REVERSAL",
    "COMPRESSION",
    "RANGE",
    "TREND_UP",
    "TREND_DOWN",
    "NEUTRAL",
)

# Wave A allow-list (locked). Do not expand here.
WAVE_A_REGIMES = {
    "hunter": frozenset({"REVERSAL"}),
    "squeeze": frozenset({"COMPRESSION"}),
    "bollinger-mr": frozenset({"RANGE", "COMPRESSION"}),
}

# Ananta router._REGIME_MAP (implementation-authoritative for live routing).
ROUTER_REGIMES = {
    "hunter": frozenset({"REVERSAL"}),
    "squeeze": frozenset({"COMPRESSION"}),
    "continuation": frozenset({"TREND_UP"}),
    "bollinger-mr": frozenset(),  # router RANGE=[] — Wave A re-test, not a core executor
}


def catalog() -> List[Dict[str, Any]]:
    """Built-in capability cards. Generated matrix, not 200 hand-maintained bots."""
    return [
        _spec("hunter", "reversal", "Buy fear at structural support",
              dna=("REVERSAL",), wave_a=True, covered=True),
        _spec("squeeze", "compression", "Expansion out of a volatility coil",
              dna=("COMPRESSION",), wave_a=True, covered=True),
        _spec("bollinger-mr", "mean_reversion", "Fade range / compression extremes",
              dna=("RANGE", "COMPRESSION"), wave_a=True, covered=True),
        _spec("continuation", "trend", "Buy shallow dips in a confirmed uptrend",
              dna=("TREND_UP",), wave_a=False, covered=True),
        _spec("donchian-breakout", "breakout", "Channel breakout continuation",
              dna=("TREND_UP",), wave_a=False, covered=True),
        _spec("atr-breakout", "breakout", "Volatility breakout",
              dna=("TREND_UP",), wave_a=False, covered=False),
        _spec("keltner-breakout", "breakout", "Keltner expansion",
              dna=("TREND_UP", "COMPRESSION"), wave_a=False, covered=False),
        _spec("ema-cross", "trend", "EMA cross trend following",
              dna=("TREND_UP",), wave_a=False, covered=False),
        _spec("supertrend", "trend", "Supertrend regime follow",
              dna=("TREND_UP",), wave_a=False, covered=False),
        _spec("macd-trend", "trend", "MACD trend confirmation",
              dna=("TREND_UP",), wave_a=False, covered=False),
        _spec("rsi-momentum", "momentum", "RSI momentum continuation",
              dna=("TREND_UP",), wave_a=False, covered=False),
        _spec("stochastic-momentum", "momentum", "Stochastic momentum",
              dna=("TREND_UP", "RANGE"), wave_a=False, covered=False),
        _spec("time-series-momentum", "momentum", "Time-series momentum",
              dna=("TREND_UP",), wave_a=False, covered=False),
        _spec("turtle", "breakout", "Turtle-style channel breakout",
              dna=("TREND_UP",), wave_a=False, covered=False),
        _spec("vwap-mr", "mean_reversion", "VWAP mean reversion",
              dna=("RANGE",), wave_a=False, covered=False),
    ]


def _spec(
    key: str,
    family: str,
    thesis: str,
    *,
    dna: Tuple[str, ...],
    wave_a: bool,
    covered: bool,
) -> Dict[str, Any]:
    return {
        "key": key,
        "family": family,
        "thesis": thesis,
        "version": STRATEGY_VERSIONS.get(key),  # None = DATA_GAP
        "evaluator": EVALUATORS.get(key),
        "dna_regimes": list(dna),
        "wave_a": wave_a,
        "wave_a_regimes": sorted(WAVE_A_REGIMES.get(key, frozenset())),
        "router_regimes": sorted(ROUTER_REGIMES.get(key, frozenset())),
        "observation_v0_coverage": covered,
        "live_watch": False,
        "keep": False,
        "laws": {
            "thesis_not_implementation": True,
            "dna_confidence_is_not_evidence": True,
        },
    }


def generate_cells() -> List[Dict[str, Any]]:
    cells: List[Dict[str, Any]] = []
    for spec in catalog():
        for asset in ASSETS:
            for tf in TIMEFRAMES:
                for regime in REGIMES:
                    covered = (
                        spec["observation_v0_coverage"]
                        and asset in COVERED_ASSETS
                        and tf in COVERED_TIMEFRAMES
                    )
                    policy = _policy(spec, regime)
                    cells.append(
                        {
                            "id": f"{spec['key']}|{asset}|{tf}|{regime}",
                            "strategy": spec["key"],
                            "family": spec["family"],
                            "asset": asset,
                            "timeframe": tf,
                            "regime": regime,
                            "wave_a": spec["wave_a"],
                            "policy": policy,
                            "coverage": "historical_lab" if covered else "NONE",
                            "live_watch": False,
                        }
                    )
    return cells


def _policy(spec: Dict[str, Any], regime: str) -> str:
    """ALLOWED = Wave A or router currently permits. Not a KEEP."""
    if spec.get("wave_a") and regime in WAVE_A_REGIMES.get(spec["key"], frozenset()):
        return "ALLOWED"
    if regime in ROUTER_REGIMES.get(spec["key"], frozenset()):
        return "ROUTER_ONLY"
    if regime in spec.get("dna_regimes") or []:
        return "THESIS_ONLY"
    return "UNMAPPED"


def dna_trend_gate(strategy: str) -> str | None:
    """Thesis TREND_UP/DOWN if DNA names it. Not a live router enable."""
    key = (strategy or "").lower()
    for spec in catalog():
        if spec["key"] == key:
            dna = set(spec.get("dna_regimes") or [])
            if "TREND_UP" in dna:
                return "TREND_UP"
            if "TREND_DOWN" in dna:
                return "TREND_DOWN"
            return None
    return None
