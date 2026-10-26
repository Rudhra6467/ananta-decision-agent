"""The technicals panel (india/technicals.py; Madhav, 26 Oct: "moving-average crossovers, like the 50-day crossing the 200-day ... RSI, MACD,
support and resistance, and volume ... it can't say whether a crossover has actually happened"): the maths on toy series with known answers,
the as-of date, the read-model section, and the firewall staying green."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from india import technicals as tx


def _df(close, start="2025-01-01", volume=None):
    d = pd.bdate_range(start, periods=len(close))
    c = pd.Series(close, dtype=float)
    return pd.DataFrame({"date": d, "open": c, "high": c * 1.01, "low": c * 0.99, "close": c,
                         "volume": volume if volume is not None else np.full(len(c), 1000.0)})


def test_last_cross_on_a_hand_series():
    dates = pd.Series(pd.bdate_range("2026-01-05", periods=8))
    a = pd.Series([np.nan, 1, 1, 3, 3, 0.5, 0.5, 2.5])
    b = pd.Series([np.nan, 2, 2, 2, 2, 2, 2, 2.0])
    x = tx.last_cross(a, b, dates)
    assert x == {"state": "above", "last_cross": "2026-01-14", "direction": "up", "sessions_ago": 0, "searched_from": "2026-01-06"}
    y = tx.last_cross(a.iloc[:7], b.iloc[:7], dates.iloc[:7])
    assert y["state"] == "below" and y["last_cross"] == "2026-01-12" and y["direction"] == "down" and y["sessions_ago"] == 1
    z = tx.last_cross(pd.Series([1.0, 1, 1]), pd.Series([2.0, 2, 2]), dates.iloc[:3])
    assert z["state"] == "below" and z["last_cross"] is None and z["searched_from"] == "2026-01-05"


def test_known_golden_cross_on_real_moving_averages():
    """220 sessions drifting down, then 60 climbing: the 50-day must cross above the 200-day once, on the first day it is above."""
    close = np.r_[np.linspace(120, 100, 220), np.linspace(101, 160, 60)]
    df = _df(close)
    s50, s200 = df["close"].rolling(50).mean(), df["close"].rolling(200).mean()
    k = int(np.flatnonzero((s50 > s200).values & (s50.shift(1) <= s200.shift(1)).values)[-1])
    p = tx.panel("TOY", df, "stock")
    x = p["cross_50_200"]
    assert x["state"] == "above" and x["direction"] == "up" and x["name"].startswith("golden cross")
    assert x["last_cross"] == str(df["date"].iloc[k].date()) and x["sessions_ago"] == len(df) - 1 - k
    assert x["searched_from"] == str(df["date"].iloc[199].date()), "the search starts where the 200-day average first exists"
    assert "golden cross" in p["words"] and "crossed above" in p["words"]


def test_wilder_rsi_by_hand_and_at_the_extremes():
    r = tx.rsi_wilder(pd.Series([1.0, 2, 1, 2]), n=2)
    assert np.isnan(r.iloc[1]) and r.iloc[2] == pytest.approx(50.0) and r.iloc[3] == pytest.approx(75.0)
    assert tx.rsi_wilder(pd.Series(np.arange(1, 40, dtype=float))).iloc[-1] == 100.0
    assert tx.rsi_wilder(pd.Series(np.arange(40, 1, -1, dtype=float))).iloc[-1] == pytest.approx(0.0)
    zig = tx.rsi_wilder(pd.Series([10.0, 11] * 30))
    assert 40 < zig.iloc[-1] < 60 and np.isnan(zig.iloc[13]) and not np.isnan(zig.iloc[14])
    assert tx._rsi_zone(75) == "overbought, over 70" and tx._rsi_zone(25) == "oversold, under 30" and tx._rsi_zone(42) == "neutral, leaning weak"


def test_macd_warmup_and_signal_cross():
    c = pd.Series(np.r_[np.linspace(100, 80, 60), np.linspace(80, 100, 40)])
    line, sig, hist = tx.macd(c)
    assert line.iloc[:25].isna().all() and not np.isnan(line.iloc[25])
    assert sig.iloc[:33].isna().all() and not np.isnan(sig.iloc[33])
    assert (hist.dropna() == (line - sig).dropna()).all()
    p = tx.panel("TOY", _df(c.values), "stock")
    assert p["macd"]["state"] == "above" and p["macd"]["cross_direction"] == "up" and p["macd"]["last_signal_cross"] is not None


def test_swings_support_resistance_and_round_levels():
    close = np.r_[np.full(20, 100.0), [100, 101, 103, 106, 110, 106, 103, 101, 100], np.full(5, 100.0), [99, 97, 94, 90, 94, 97, 99], np.full(19, 100.0)]
    h, l = pd.Series(close), pd.Series(close)
    hi, lo = tx.swings(h, l, k=5, window=60)
    assert (24, 110.0) in hi and (37, 90.0) in lo
    assert tx.round_step(22600) == 500 and tx.round_step(348) == 50 and tx.round_step(9.2) == 1
    df = _df(close)
    df["high"], df["low"] = df["close"], df["close"]
    p = tx.panel("TOY", df, "stock")
    assert p["resistance"]["swing_high"] == 110.0 and p["support"]["swing_low"] == 90.0
    assert p["resistance"]["round"] == 110.0 and p["support"]["round"] == 100.0, "a close on a round level: the next step up is resistance"


def test_panel_as_of_volume_and_short_history():
    vol = np.r_[np.full(59, 1000.0), 3000.0]
    p = tx.panel("TOY", _df(np.linspace(100, 110, 60), start="2026-07-01", volume=vol), "stock")
    assert p["status"] == "ok" and p["as_of"] == str(pd.bdate_range("2026-07-01", periods=60)[-1].date())
    assert p["volume"] == {"last": 3000, "avg20": 1000, "ratio": 3.0}
    assert p["sma"]["200"] is None and p["cross_50_200"]["state"] is None, "no 200-day average on 60 sessions"
    i = tx.panel("IDX", _df(np.linspace(100, 110, 60)), "index")
    assert "not available" in i["volume"]["note"]
    assert tx.panel("TOY", _df(np.linspace(1, 2, 20)), "stock")["status"] == "too_short"


def test_section_and_knowledge_shapes(tmp_path, monkeypatch):
    monkeypatch.setattr(tx.paths, "manifest_dir", lambda: tmp_path)
    assert tx.section(refresh=False)["status"] == "missing"
    (tmp_path / "technicals.json").write_text('{"rules": "r", "built_at": "2099-01-01T00:00:00+00:00", "as_of": "2026-10-23", "basis": "b", '
                                              '"indices": {"NIFTY 50": {"close": 1}}, "stocks": {}, "errors": [], "picks_day": null}')
    s = tx.section(refresh=False)
    assert s["status"] == "ok" and s["as_of"] == "2026-10-23" and "NIFTY 50" in s["indices"]
    k = tx.knowledge()
    assert k["status"] in ("ok", "unavailable")
    if k["status"] == "ok":
        fams = k["families"]
        assert {"moving averages and crossovers", "RSI and stochastic", "MACD", "volume", "support and resistance"} <= set(fams)
        macd = fams["MACD"]       # untested until study XO1 (26 Oct) is in the ledger; then its verdicts and headline are shown
        assert macd["not_tested"] or (macd["headline"] and any(t["study"] == "XO1" for t in macd["tested"]))
        assert all("words" in v for v in fams.values())


def test_firewall_stays_green_and_the_panel_uses_only_the_logged_purposes():
    import ast
    from pathlib import Path

    from india import leakcheck
    ok, msg = leakcheck.check_sealed_files()
    assert ok, msg
    tree = ast.parse(Path(tx.__file__).read_text())
    calls = [(n.func.attr, n.args[0].value if n.args and isinstance(n.args[0], ast.Constant) else None) for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name) and n.func.value.id == "sealed"]
    assert calls and set(calls) == {("read_index", "paper_context")}, calls      # stocks come through paper.load_adjusted (paper_lookback)
    assert "load_adjusted" in Path(tx.__file__).read_text()
