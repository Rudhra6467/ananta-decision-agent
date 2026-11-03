"""The NDAX cost table, in one place.

Research audit, Oct 15 (the data-costs doubt): ten files each carried their own copy of the same ten half-spreads. They are the median of
5 NDAX order-book snapshots taken on 2026-09-29 (docs/research/CANDIDATE_V3.md, Costs; the raw readings were not kept), applied to 2017-2026
and to every paper book since. The numbers are
unchanged; they live here now, with the date and the sample count beside them, so nobody mistakes them for a long measurement.
(tests/test_ndax_costs.py checks that no second copy of the table exists and that every old name still gives these numbers.)

What is measured, and where:
  - These ten (the lab coins): the median of 5 snapshots, 2026-09-29. Every other coin is an assumption: jarvis/service/registry.cost() charges
    the fee plus max(3 x the coin's Binance half-spread, its tier's floor); DEFAULT_HS below is the fallback of the research code.
  - The worker Mac's minute-by-minute NDAX bid and ask (jarvis/service/ndax_spreads.py; 77 NDAX coins on Oct 14, whole days from
    Oct 12): evidence only. It sets no cost yet. Stage S2 (after 14 clean days, about Oct 25) reruns the $500 backtest with each
    coin's 75th-percentile half-spread; Madhav decides any change to the coin list. Until then nothing here changes by itself.
"""
from __future__ import annotations

SNAPSHOT = {"taken": "2026-09-29", "what": "median of 5 NDAX order-book snapshots per lab coin (raw readings not kept)", "samples": 5,
            "fee_checked": "2026-09-29 (NDAX flat 0.20%, see paper_exit.py)",
            "applied_to": "every backtest since 2017 and every paper book since 2026-09-29",
            "next": "worker stage S2, about 2026-10-26 (jarvis/service/ndax_spreads.py)",
            "replaced": "2026-11-03 by the measured table below (REFRESHES); the 29 Sep values stay as HALF_SPREAD_2026_09_29"}

NDAX_FEE = 0.0020
# The table as it stood from 2026-09-29 to 2026-11-03 (the median of 5 order-book snapshots); kept so every earlier result can be traced.
HALF_SPREAD_2026_09_29 = {"BTC": 0.00178, "ETH": 0.00084, "SOL": 0.00289, "ADA": 0.00273, "DOGE": 0.00307,
                          "AVAX": 0.00370, "BCH": 0.00400, "LINK": 0.00341, "LTC": 0.00334, "XRP": 0.00251}
# 2026-11-03 SPREAD-REFRESH (Madhav, 26 Oct, on #108: "yes. Keep the coin list unchanged; take the measured spreads into the cost table at
# SPREAD-REFRESH"; applied with his "yes to 5", 3 Nov): each coin's 75th-percentile half-spread, the S2 measure, over the worker Mac's 14
# full days 2026-10-20..2026-11-02 (about 20,120 one-minute quotes a coin, jarvis/service/ndax_spreads.table). BCH has no NDAX quote in
# the feed: it keeps the 29 Sep value. ETH was the big gap (0.084% in the table, 0.240% measured).
HALF_SPREAD = {"BTC": 0.00228, "ETH": 0.00240, "SOL": 0.00304, "ADA": 0.00282, "DOGE": 0.00331,
               "AVAX": 0.00414, "BCH": 0.00400, "LINK": 0.00377, "LTC": 0.00404, "XRP": 0.00268}
REFRESHES = [{"date": "2026-11-03", "approved": "Madhav, 2026-10-26 on #108 (applied with 'yes to 5', 2026-11-03)", "measure": "p75 half-spread",
              "window": "2026-10-20..2026-11-02, 14 full days", "not_measured": ["BCH"]}]
DEFAULT_HS = 0.0040          # any coin not in the table, in the research code: the pessimistic default
EXPENSIVE_HS = 0.0030
