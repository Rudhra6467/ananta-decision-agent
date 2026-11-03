"""U4 guard: when any timeframe is stale the Explorer places no new entries (open trades are still managed).

Added for GATE-REDATE (ops_stale), 2026-11-03: stale() existed but the skip had no direct test.
"""
from src.intelligence import explorer_engine as xe

T = 1_800_000_000
TFS = ("15m", "30m", "1h", "4h", "1d")


class _TF:
    def __init__(self, t):
        self.close_t = t


def test_stale_timeframe_skips_new_entries_but_still_rings_bells():
    eng = xe.CoinEngine("BTC")
    calls = {"bells": 0}
    eng.ready = lambda: True
    eng.stale = lambda t: ["1h", "4h"]
    eng.state = lambda t: {}
    eng._tags = lambda st: {}

    def bells(t, st):
        calls["bells"] += 1

    def no_setups(*a, **k):
        raise AssertionError("setups() must not run while a timeframe is stale")

    eng._bells = bells
    eng.setups = no_setups
    eng.trade_from_t = 0
    rec = eng.scan(T)
    assert rec["skip"] == "STALE:1h,4h"
    assert calls["bells"] == 1          # open trades are still managed
    assert not eng.orders


def test_stale_means_more_than_two_bars_old():
    eng = xe.CoinEngine("BTC")
    eng.tf = {k: _TF(T - xe.TF_S[k]) for k in TFS}
    assert eng.stale(T) == []
    eng.tf["1h"] = _TF(T - 2 * xe.TF_S["1h"])        # exactly two bars: still fresh
    assert eng.stale(T) == []
    eng.tf["1h"] = _TF(T - 2 * xe.TF_S["1h"] - 1)    # one second past: stale
    assert eng.stale(T) == ["1h"]
