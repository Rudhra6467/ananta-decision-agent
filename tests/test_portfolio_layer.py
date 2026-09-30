"""Portfolio manager layer: ratings, SUGGEST vs AUTO, approvals, expiry, and parity with the review #4 simulator."""
import tempfile
from pathlib import Path

from src.intelligence import explorer_engine as xe
from src.intelligence import portfolio_layer as pl

D = 86400
T0 = 1_600_000_000 - (1_600_000_000 % D)


def _view(close, e20, e50, slope=0.01, atr=1.0, ret30=0.1, t=T0):
    return {"day_close_t": t, "close": close, "ema20": e20, "ema50": e50, "ema20_slope5": slope, "atr": atr, "ret30": ret30, "rsi": 55}


def test_ratings():
    r, on, why = pl.rate("ETH", _view(110, 100, 90), btc_on=False, mom_rank=0.9)
    assert r == "OUT" and not on and "market gate off" in why[0]
    assert pl.rate("ETH", _view(110, 100, 90, atr=5), True, 0.9)[0] == "STRONG"
    assert pl.rate("ETH", _view(100.2, 100, 90), True, 0.9)[0] == "WEAK"          # within 0.5 ATR of the 20-day
    assert pl.rate("ETH", _view(99, 100, 90), True, 0.9)[0] == "OUT"              # below the 20-day: fast exit


def test_suggest_waits_for_approval_auto_acts_and_shadow_always_acts():
    base = Path(tempfile.mkdtemp())
    L = pl.PortfolioLayer(base)
    views = {"BTC": _view(110, 100, 90), "ETH": _view(55, 50, 45), "SOL": _view(9, 10, 11)}
    px = {"BTC": 110.0, "ETH": 55.0, "SOL": 9.0}
    d = L.decide(views, px, T0 + 300)
    assert L.mode == "SUGGEST" and {p["action"] for p in d["proposals"]} == {"ENTER"} and len(d["proposals"]) == 2
    st = L.status(px)
    assert st["books"]["MAIN"]["holdings"] == {} and set(st["books"]["SHADOW"]["holdings"]) == {"BTC", "ETH"}
    try:
        L.approve("all", px, T0 + 600, by=" ")
    except ValueError:
        pass
    else:
        raise AssertionError("approval must record who approved")
    fills = L.approve("all", px, T0 + 600, by="Vamsi")
    assert {f["coin"] for f in fills} == {"BTC", "ETH"} and not L.pending()
    st = L.status(px)
    assert abs(st["books"]["MAIN"]["holdings"]["BTC"] - 2000 / 3) < 1 and st["books"]["MAIN"]["costs"] > 0
    # next day ETH breaks its 20-day: SUGGEST proposes EXIT; an unapproved proposal expires the day after
    views2 = {k: {**v, "day_close_t": T0 + D} for k, v in views.items()}
    views2["ETH"] = _view(49, 50, 45, t=T0 + D)
    d2 = L.decide(views2, px, T0 + D + 300)
    assert [p["action"] for p in d2["proposals"]] == ["EXIT"]
    views3 = {k: {**v, "day_close_t": T0 + 2 * D} for k, v in views2.items()}
    L.decide(views3, px, T0 + 2 * D + 300)
    import sqlite3
    st3 = dict(sqlite3.connect(base / "portfolio_book.sqlite").execute("SELECT id, status FROM proposals").fetchall())
    assert "EXPIRED" in st3.values()
    # AUTO acts at once
    L.set_mode("auto", by="Vamsi")
    views4 = {k: {**v, "day_close_t": T0 + 3 * D} for k, v in views3.items()}
    d4 = L.decide(views4, px, T0 + 3 * D + 300)
    assert not d4["proposals"] and any(f["book"] == "MAIN" and f["coin"] == "ETH" and f["side"] == "SELL" for f in d4["fills"])


def test_parity_with_review4_simulator():
    try:
        import numpy as np
        import pandas as pd

        from src.research import portfolio_trend as pt
    except ImportError:
        return
    n = 260
    days = pd.date_range("2021-01-04", periods=n, freq="D")
    rng = np.random.default_rng(5)
    data = {}
    for k in ("BTC", "ETH", "SOL"):
        c = 100 * np.exp(np.cumsum(rng.normal(0.001, 0.03, n)))
        o = np.r_[c[0], c[:-1]] * (1 + rng.normal(0, 0.002, n))
        data[k] = pd.DataFrame({"o": o, "c": c}, index=days)
    sig = pt.signals(data, days)
    sim = pt.simulate(data, days, sig["T3"], sig["_avail"])
    base = Path(tempfile.mkdtemp())
    L = pl.PortfolioLayer(base)
    tfs = {k: xe.TfState("1d") for k in data}
    for d in range(n - 1):
        for k, df in data.items():
            ts = int(days[d].timestamp())
            tfs[k].add(ts, df["o"].iloc[d], max(df["o"].iloc[d], df["c"].iloc[d]), min(df["o"].iloc[d], df["c"].iloc[d]), df["c"].iloc[d], 1.0)
        views = {k: pl.daily_view(tfs[k]) for k in data}
        if views["BTC"] is None:
            continue
        px = {k: float(df["o"].iloc[d + 1]) for k, df in data.items()}
        L.decide(views, px, int(days[d + 1].timestamp()), weekly=days[d + 1].weekday() == 0)
    last_px = {k: float(df["c"].iloc[n - 2]) for k, df in data.items()}
    ours = L.status(last_px)["books"]["SHADOW"]["equity"] / pl.START
    theirs = sim["equity"].iloc[n - 2] / sim["equity"].iloc[49]
    assert abs(ours / theirs - 1) < 0.01, (ours, theirs)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
