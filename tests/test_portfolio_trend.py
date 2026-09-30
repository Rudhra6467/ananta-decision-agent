"""Review #4 simulator: buy-and-hold arithmetic, cash when gated, no lookahead in signals."""
try:
    import numpy as np
    import pandas as pd

    from src.research import portfolio_trend as pt
except ImportError:
    pt = None


def _data(n=200, crash_at=None):
    days = pd.date_range("2020-01-01", periods=n, freq="D")
    out = {}
    for k, g in (("BTC", 0.01), ("ETH", 0.005)):
        c = 100 * np.exp(g * np.arange(n))
        if crash_at is not None:
            c[crash_at:] = c[crash_at] * np.exp(-0.02 * np.arange(n - crash_at))
        out[k] = pd.DataFrame({"o": np.r_[c[0], c[:-1]], "c": c}, index=days)
    return out, days


def test_buy_and_hold_tracks_prices_minus_costs():
    if pt is None:
        return
    data, days = _data()
    sig = pt.signals(data, days)
    sim = pt.simulate(data, days, sig["BH"], sig["_avail"])
    eq = sim["equity"]
    assert eq.iloc[49] == 1.0 and eq.iloc[-1] > 1.5 and sim["costs"] > 0


def test_gate_moves_to_cash_in_a_crash():
    if pt is None:
        return
    data, days = _data(crash_at=120)
    sig = pt.signals(data, days)
    t4 = pt.simulate(data, days, sig["T4"], sig["_avail"])
    bh = pt.simulate(data, days, sig["BH"], sig["_avail"])
    assert t4["exposure"].iloc[-1] == 0.0 and t4["equity"].iloc[-1] > bh["equity"].iloc[-1]


def test_signals_do_not_look_ahead():
    if pt is None:
        return
    data, days = _data()
    a = pt.signals(data, days)["T3"]
    for k in data:
        data[k].loc[days[150]:, ["o", "c"]] *= 0.5
    b = pt.signals(data, days)["T3"]
    assert a.iloc[:150].equals(b.iloc[:150])


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
