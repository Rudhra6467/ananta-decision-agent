"""Cost model v1 and tax model v1 for the India paper lab and every study.

Rates are Zerodha's published charges page as read on 18 Oct 2026 (brokerage, STT, NSE transaction charges, SEBI fee, stamp duty, DP charge,
GST). They are the CURRENT rates; history used different STT and exchange charges, so a study that spans years passes `year` and gets the
rate table in force then where known (STT changes below), otherwise today's rate, and says so in its report. Spread and slippage are
ESTIMATES (labelled), not observed: no free source holds historical bid-ask for Indian stocks or options.

cost(...) returns rupees for one leg. round_trip(...) returns the total for buy then sell. Tax model: listed equity delivery sold after
23 Jul 2024: short-term (held under 12 months) 20%, long-term 12.5% above Rs 1.25 lakh of gains a year; before that date 15% and 10% above
Rs 1 lakh. Intraday equity (speculative) and futures/options (non-speculative) are business income taxed at the slab rate: the lab reports
them pre-tax and applies SLAB_RATE only when asked. All tax rates are for Madhav's accountant to confirm; nothing here is tax advice.
"""
from __future__ import annotations

import datetime as dt

GST = 0.18
SEBI = 10 / 1e7  # Rs 10 per crore
STAMP = {"delivery": 0.00015, "intraday": 0.00003, "futures": 0.00002, "options": 0.00003}  # buy side
TXN = {"delivery": 0.0000307, "intraday": 0.0000307, "futures": 0.0000183, "options": 0.0003553}
DP_CHARGE = 15.34  # per scrip per day on a delivery sell
SLAB_RATE = 0.30  # placeholder for business income; set by the accountant
# half-spread in basis points by turnover rank (ESTIMATE), one-way; slippage adds half again on entries and stops
HALF_SPREAD_BPS = [(50, 2.0), (100, 3.5), (250, 6.0), (500, 10.0), (10**9, 25.0)]
OPTION_HALF_SPREAD_RS = {"NIFTY": 0.5, "BANKNIFTY": 1.0, "default": 1.0}


def stt_rate(kind: str, side: str, year: int) -> float:
    """STT as a fraction of turnover. Delivery 0.1% both sides always. Intraday 0.025% sell. Futures sell: 0.0125% to Sep 2024, 0.02% to Mar 2026,
    0.05% from Apr 2026 as the page shows today. Options sell on premium: 0.0625% to Sep 2024, 0.1% to Mar 2026, 0.15% from Apr 2026."""
    if kind == "delivery":
        return 0.001
    if side != "sell":
        return 0.0
    if kind == "intraday":
        return 0.00025
    if kind == "futures":
        return 0.000125 if year < 2024 or (year == 2024) else (0.0002 if year == 2025 else 0.0005)
    if kind == "options":
        return 0.000625 if year < 2024 or year == 2024 else (0.001 if year == 2025 else 0.0015)
    raise ValueError(kind)


def half_spread_bps(turnover_rank: int | None) -> float:
    r = turnover_rank or 10**9
    for cap, bps in HALF_SPREAD_BPS:
        if r <= cap:
            return bps
    return HALF_SPREAD_BPS[-1][1]


def cost(kind: str, side: str, value: float, year: int = 2026, orders: int = 1) -> float:
    """Statutory plus brokerage cost of one leg, rupees. kind: delivery, intraday, futures, options. value = traded value in rupees."""
    if kind == "delivery":
        brokerage = 0.0
    elif kind == "options":
        brokerage = 20.0 * orders
    else:
        brokerage = min(20.0, 0.0003 * value) * orders
    txn = TXN[kind] * value
    sebi = SEBI * value
    gst = GST * (brokerage + txn + sebi)
    stamp = STAMP[kind] * value if side == "buy" else 0.0
    stt = stt_rate(kind, side, year) * value
    dp = DP_CHARGE if (kind == "delivery" and side == "sell") else 0.0
    return brokerage + txn + sebi + gst + stamp + stt + dp


def round_trip(kind: str, buy_value: float, sell_value: float, year: int = 2026, turnover_rank: int | None = None, extra_slippage_bps: float = 0.0) -> dict:
    """Costs of buy then sell, with the spread estimate: each leg gives up the half-spread plus any extra slippage, in rupees on its value."""
    hs = (half_spread_bps(turnover_rank) + extra_slippage_bps) / 1e4
    fees = cost(kind, "buy", buy_value, year) + cost(kind, "sell", sell_value, year)
    spread = hs * (buy_value + sell_value)
    return {"fees": fees, "spread_estimate": spread, "total": fees + spread}


def tax_on_equity_gain(gain: float, held_days: int, sold: dt.date, yearly_ltcg_so_far: float = 0.0) -> float:
    """Tax on one realised gain from listed equity delivery. Losses return 0 (set-off is a portfolio matter, handled in the paper ledger)."""
    if gain <= 0:
        return 0.0
    new = sold >= dt.date(2024, 7, 23)
    if held_days < 365:
        return gain * (0.20 if new else 0.15)
    exempt_total = 125_000 if new else 100_000
    taxable = max(0.0, yearly_ltcg_so_far + gain - exempt_total) - max(0.0, yearly_ltcg_so_far - exempt_total)
    return taxable * (0.125 if new else 0.10)


if __name__ == "__main__":
    v = 100_000
    print("delivery round trip on 1 lakh:", round(round_trip("delivery", v, v * 1.02, 2026, 80)["total"], 2))
    print("nifty option lot ~Rs 7,500 premium buy+sell:", round(round_trip("options", 7500, 9000, 2026)["fees"], 2))
    print("stcg on 10,000 gain held 100d:", tax_on_equity_gain(10_000, 100, dt.date(2026, 10, 1)))
