"""Estimated trading costs (labelled ESTIMATE everywhere; decision 4, Oct 14).

Spread: the Corwin-Schultz high-low estimator per stock per day from two consecutive days' highs and lows,
negative values set to zero, averaged over the prior 21 trading days. One-way cost = max(0.05%, half the
average spread) + 0.05% slippage allowance. Commission C$0. Every pass criterion must also hold at 2x.
"""
from __future__ import annotations

import math

LABEL = "ESTIMATE"
FLOOR = 0.0005
SLIPPAGE = 0.0005
WINDOW = 21
_K = 3 - 2 * math.sqrt(2)


def corwin_schultz(h0: float, l0: float, h1: float, l1: float) -> float:
    """Spread estimate (fraction of price) from two consecutive days; never negative."""
    if min(h0, l0, h1, l1) <= 0 or h0 < l0 or h1 < l1:
        raise ValueError("bad high/low")
    beta = math.log(h0 / l0) ** 2 + math.log(h1 / l1) ** 2
    gamma = math.log(max(h0, h1) / min(l0, l1)) ** 2
    alpha = (math.sqrt(2 * beta) - math.sqrt(beta)) / _K - math.sqrt(gamma / _K)
    s = 2 * (math.exp(alpha) - 1) / (1 + math.exp(alpha))
    return max(0.0, s)


def one_way_cost(spreads: list[float], stress: float = 1.0) -> float:
    """From the prior 21 daily estimates (point-in-time). stress=2.0 for the 2x rule."""
    if not spreads:
        raise ValueError("no spread estimates")
    w = spreads[-WINDOW:]
    return stress * (max(FLOOR, 0.5 * sum(w) / len(w)) + SLIPPAGE)
