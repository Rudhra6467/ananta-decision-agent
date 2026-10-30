"""india/bookstats.py: closed and open counted apart (flag 44), expectancy with its "too few" flag, the Sharpe-like ratio that waits for 20 sessions,
the holdings correlation, SP1 slippage; and the morning view's freshness fixes (26 Oct)."""
from __future__ import annotations

import json

import pandas as pd

from india import bookstats as bs


def _t(camp, status, ret=None, risk=0.05, policy="hold_20d", book="exec", entry=100.0, last=None):
    t = {"book": book, "policy": policy, "campaign": camp, "status": status, "risk_frac": risk, "notional": 50000.0}
    if status == "open":
        t.update(entry_adj=entry, last_close_adj=last if last is not None else entry * (1 + ret))
    else:
        t["net_ret"] = ret
    return t


STATE = {"trades": {f"c{i}": _t("PULL", "closed", -0.08) for i in range(3)} | {"c9": _t("REV", "closed", 0.04)} |
         {"o1": _t("PULL", "open", 0.02), "o2": _t("PULL", "open", -0.04), "o3": _t("REV", "open", -0.01)} |
         {"x1": _t("PULL", "open", 0.5, policy="hold_5d"), "x2": _t("PULL", "closed", 0.5, book="baseline")}}


def test_split_counts_closed_and_open_apart_and_only_the_reference_exec_book():
    rows = bs.trade_rows(STATE)
    assert len(rows) == 7                                                       # other exits and the baseline book are left out
    s = bs.split(rows)
    assert s["total"]["closed"]["n"] == 4 and s["total"]["closed"]["winners"] == 1
    assert s["total"]["open"]["n"] == 3 and s["total"]["open"]["winners"] == 1
    assert round(s["total"]["closed"]["avg"], 4) == -0.05 and round(s["total"]["open"]["avg"], 4) == -0.01
    assert s["by_family"]["PULL"]["closed"]["winners"] == 0 and s["by_family"]["REV"]["open"]["n"] == 1
    assert s["words"] == "win rate counts closed trades only: 1 of 4 closed won (avg -5.0%); of 3 open, 1 are up (avg -1.0%)"


def test_real_book_shape_zero_of_29_closed_and_10_of_72_open():
    tr = {f"c{i}": _t("PULL", "closed", -0.0776) for i in range(29)} | {f"o{i}": _t("REV", "open", 0.03 if i < 10 else -0.04) for i in range(72)}
    s = bs.split(bs.trade_rows({"trades": tr}))
    assert s["total"]["closed"]["winners"] == 0 and s["total"]["closed"]["n"] == 29
    assert s["total"]["open"]["winners"] == 10 and s["total"]["open"]["n"] == 72
    assert s["words"].startswith("win rate counts closed trades only: 0 of 29 closed won (avg -7.8%); of 72 open, 10 are up (avg -3.0%)")


def test_expectancy_flags_small_counts_and_reports_R():
    e = bs.expectancy(bs.trade_rows(STATE))
    c = e["overall"]["closed"]
    assert c["n"] == 4 and c["too_few"] and "too few trades (n<30)" in c["flag"]
    assert round(c["avg_R"], 2) == -1.0                                          # -5% on a 5% stop distance
    assert e["overall"]["closed_and_open"]["n"] == 7
    assert "too few trades (n<30)" in e["words"]
    big = {"trades": {f"c{i}": _t("PULL", "closed", 0.01) for i in range(30)}}
    assert not bs.expectancy(bs.trade_rows(big))["overall"]["closed"]["too_few"]


def test_sharpe_waits_for_twenty_sessions():
    marks = [{"at": f"2026-10-{d:02d}T22:00:00+00:00", "book": "exec", "policy": "hold_20d", "campaign": "PULL", "open": 10, "closed": 0,
              "realised_inr": 0, "open_unrealised_inr": 100.0 * d} for d in range(1, 8)]
    ser = bs.daily_book_returns(marks)
    assert len(ser) == 6
    s = bs.sharpe_like(ser)
    assert s["value"] is None and s["words"] == "only 6 sessions: not computed (needs 20)"
    long = [(f"d{i}", 0.001 * (1 if i % 2 else -0.5)) for i in range(25)]
    s2 = bs.sharpe_like(long)
    assert s2["sessions"] == 25 and s2["value"] is not None and "Sharpe-like ratio" in s2["words"]


def test_holdings_correlation_and_share_below_the_50_day():
    import numpy as np
    rng = np.random.default_rng(1)
    dates = pd.bdate_range("2026-06-01", periods=100)
    base = rng.normal(0, 0.01, 100)
    rows = []
    for sym, tilt in (("AAA", 0.0), ("BBB", 0.0), ("CCC", 0.0)):
        r = base + rng.normal(0, 0.0005, 100) if sym != "CCC" else rng.normal(0, 0.01, 100)
        px = 100 * np.cumprod(1 + r)
        for d, p in zip(dates, px):
            rows.append({"symbol": sym, "date": d, "adj_close": p})
    for d, p in zip(dates, np.linspace(100, 60, 100)):           # always falling: below its 50-day
        rows.append({"symbol": "DDD", "date": d, "adj_close": p})
    h = bs.holdings_risk(pd.DataFrame(rows), ["AAA", "BBB", "CCC", "DDD"])
    assert h["status"] == "ok" and h["symbols_used"] == 4 and -1 <= h["avg_pairwise_corr"] <= 1
    assert "DDD" in h["below_50d"] and h["below_50d_of"] == 4 and "50-day average" in h["words"]
    assert bs.holdings_risk(pd.DataFrame(columns=["symbol", "date", "adj_close"]), ["AAA"])["status"] == "missing"


def test_slippage_says_not_enough_with_one_trade():
    book = {"by_index": {"NIFTY": {"trades": 0, "option_1lot_rs_study_fill": 0, "option_1lot_rs_realistic_fill": 0},
                         "BANKNIFTY": {"trades": 1, "option_1lot_rs_study_fill": 2018.0, "option_1lot_rs_realistic_fill": 1078.0}}}
    s = bs.slippage(book)
    assert s["trades"] == 1 and s["avg_rs_per_lot"] == 940 and not s["enough"] and "not enough to trust" in s["words"]
    assert bs.slippage({"by_index": {}})["words"] == "slippage: not enough scored trades yet"
    assert bs.slippage(None)["trades"] == 0


def test_build_reads_the_lake_and_survives_missing_pieces(tmp_path, monkeypatch):
    data = tmp_path / "india"
    (data / "paper" / "sp1").mkdir(parents=True)
    monkeypatch.setattr(bs.paths, "data_dir", lambda: data)
    assert bs.build()["status"] == "missing"
    (data / "paper" / "state.json").write_text(json.dumps(STATE))
    b = bs.build(compute_holdings=False)
    assert b["status"] == "ok" and b["closed_vs_open"]["total"]["closed"]["n"] == 4 and b["slippage"]["trades"] == 0
    assert "win rate counts closed trades only" in b["words"]


def test_beta_and_volatility_per_holding():
    """27 Oct: Ananta said "my facts hold no beta or volatility figure for any stock"."""
    import numpy as np
    import pandas as pd
    from india import bookstats as bs
    rng = np.random.default_rng(1)
    days = pd.bdate_range("2026-03-02", periods=160)
    m = rng.normal(0, 0.01, len(days))
    nifty = 20000 * np.cumprod(1 + m)
    hi = 100 * np.cumprod(1 + 1.5 * m + rng.normal(0, 0.002, len(days)))
    lo = 100 * np.cumprod(1 + 0.5 * m + rng.normal(0, 0.002, len(days)))
    prices = pd.concat([pd.DataFrame({"symbol": "HI", "date": days, "adj_close": hi}), pd.DataFrame({"symbol": "LO", "date": days, "adj_close": lo})])
    out = bs.beta_vol(prices, pd.DataFrame({"date": days, "close": nifty}), ["HI", "LO"])
    assert out["status"] == "ok"
    assert 1.35 < out["per_holding"]["HI"]["beta"] < 1.65 and 0.35 < out["per_holding"]["LO"]["beta"] < 0.65
    assert out["per_holding"]["HI"]["vol_ann"] > out["per_holding"]["LO"]["vol_ann"]
    assert out["words"].index("HI beta") < out["words"].index("LO beta") and "no test of beta" in out["words"]
    jumpy = prices.copy()
    jumpy.loc[(jumpy["symbol"] == "LO") & (jumpy["date"] >= days[100]), "adj_close"] *= 0.5     # a missed corporate action
    assert bs.beta_vol(jumpy, pd.DataFrame({"date": days, "close": nifty}), ["LO"])["per_holding"]["LO"].get("unreliable")


def test_words_say_when_every_close_is_a_stop_and_no_trade_reached_its_hold():
    """29 Oct audit: '0 of 37 closed won' read as a losing book when every close was a stop by construction."""
    st = {"trades": {
        "a": {"book": "exec", "policy": "hold_20d", "campaign": "PULL", "status": "closed", "net_ret": -0.08, "exit_reason": "stop", "bars_seen": 3, "risk_frac": 0.08},
        "b": {"book": "exec", "policy": "hold_20d", "campaign": "PULL", "status": "closed", "net_ret": -0.07, "exit_reason": "stop", "bars_seen": 5, "risk_frac": 0.08},
        "c": {"book": "exec", "policy": "hold_20d", "campaign": "REV", "status": "open", "entry_adj": 100, "last_close_adj": 103, "bars_seen": 7, "risk_frac": 0.08},
    }}
    s = bs.split(bs.trade_rows(st, "hold_20d"))
    assert s["closes"] == {"stops": 2, "time_or_target": 0, "other": 0, "longest_open_sessions": 7}
    assert "every close so far is a stop-loss; no trade has reached its hold yet" in s["words"]
    st["trades"]["b"]["exit_reason"] = "time"
    s = bs.split(bs.trade_rows(st, "hold_20d"))
    assert "(1 by stop-loss, 1 by time or target)" in s["words"]
