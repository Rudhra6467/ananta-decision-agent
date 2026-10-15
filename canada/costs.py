"""Estimated trading costs (labelled ESTIMATE everywhere; decision 4, Oct 14; revised after independent review).

Spread: the Corwin-Schultz (2012) two-day high-low estimator on CAPITAL-ADJUSTED highs and lows, with the
authors' overnight adjustment, negative values set to zero, two-day windows containing a capital event
skipped by the caller. For a fill on day f the window is the 21 daily estimates ending on f-5, so a dip's
own wide ranges never inflate its cost. One-way cost = max(0.05%, half the window mean) + 0.05% slippage.
Commission C$0. The 2x stress rule doubles the full one-way cost, floor and slippage included.
"""
from __future__ import annotations

import math

LABEL = "ESTIMATE"
FLOOR = 0.0005
SLIPPAGE = 0.0005
WINDOW = 21
LAG = 5
_K = 3 - 2 * math.sqrt(2)


def corwin_schultz(h0: float, l0: float, h1: float, l1: float, c0: float | None = None) -> float:
    """Spread estimate (fraction of price) from two consecutive days; never negative.
    c0 = day 1's close: when day 2's range sits wholly above or below it, day 2 is shifted by the gap."""
    if min(h0, l0, h1, l1) <= 0 or h0 < l0 or h1 < l1:
        raise ValueError("bad high/low")
    if c0 is not None:
        if l1 > c0:
            h1, l1 = h1 - (l1 - c0), c0
        elif h1 < c0:
            h1, l1 = c0, l1 + (c0 - h1)
    beta = math.log(h0 / l0) ** 2 + math.log(h1 / l1) ** 2
    gamma = math.log(max(h0, h1) / min(l0, l1)) ** 2
    alpha = (math.sqrt(2 * beta) - math.sqrt(beta)) / _K - math.sqrt(gamma / _K)
    s = 2 * (math.exp(alpha) - 1) / (1 + math.exp(alpha))
    return max(0.0, s)


def fill_window(estimates: list[float], f: int) -> list[float]:
    """The 21 daily estimates ending on day index f-5 (inclusive), for a fill on day index f."""
    end = f - LAG
    if end - WINDOW + 1 < 0:
        raise ValueError("not enough history before the fill")
    return estimates[end - WINDOW + 1:end + 1]


def one_way_cost(window: list[float], stress: float = 1.0) -> float:
    """From the fill window (fill_window). stress=2.0 for the 2x rule doubles the whole cost."""
    if not window:
        raise ValueError("no spread estimates")
    return stress * (max(FLOOR, 0.5 * sum(window) / len(window)) + SLIPPAGE)
