"""9 Nov 2026 (Madhav, 19:51 Toronto: "Yes to all your recommendations"; recommendation 1: the options line reads the official 09:15 open, as
its study did, not the session's first tick). The quote's open is taken only when the line's own pre-open read confirms it; otherwise the open
is read as before."""
import datetime as dt

import pandas as pd

from india import sp1paper

DAY = dt.date(2026, 11, 6)


class K:
    def __init__(self, opens: dict, last: dict | None = None, fail: bool = False):
        self.opens, self.last, self.fail, self.calls = opens, last or {}, fail, 0

    def get(self, path, params=None):
        self.calls += 1
        if self.fail:
            raise RuntimeError("no answer")
        names = [v for _, v in params]
        return {n: {"last_price": self.last.get(n[4:]), "ohlc": {"open": self.opens.get(n[4:], 0)}} for n in names}


def test_the_quotes_open_is_taken_only_when_the_pre_open_read_confirms_it():
    k = K({"NIFTY BANK": 57812.9})
    assert sp1paper.official_open(k, "NIFTY BANK", {"NIFTY BANK": 57812.9}) == (57812.9, "the quote's open, confirmed by the pre-open read")       # 6 Nov: equal to the rupee
    assert sp1paper.official_open(K({"NIFTY BANK": 59219.95}), "NIFTY BANK", {"NIFTY BANK": 59235.45})[0] == 59219.95                              # 9 Nov: 0.03% apart
    off, why = sp1paper.official_open(k, "NIFTY BANK", {"NIFTY BANK": 58400.0})          # a stale open (another day's): 1% from the pre-open read
    assert off is None and "not within 0.1%" in why
    assert sp1paper.official_open(k, "NIFTY BANK", {})[0] is None                         # no pre-open read: nothing confirms it
    assert sp1paper.official_open(K({}), "NIFTY BANK", {"NIFTY BANK": 57812.9})[0] is None      # the quote gave no open
    assert sp1paper.official_open(K({}, fail=True), "NIFTY BANK", {"NIFTY BANK": 57812.9})[0] is None


def test_the_pre_open_read_is_each_indexs_last_price():
    k = K({}, last={"NIFTY 50": 24538.2, "NIFTY BANK": 57812.9})
    assert sp1paper.preopen_levels(k) == {"NIFTY 50": 24538.2, "NIFTY BANK": 57812.9}


def _first_tick(monkeypatch, ticks: dict):
    """The forming 09:15 bar as Kite serves it live: its open is the session's first tick."""
    def candles(k, token, interval, a, b):
        return pd.DataFrame([{"date": DAY, "m": 0, "open": ticks[token], "high": ticks[token], "low": ticks[token], "close": ticks[token], "volume": 0}])
    monkeypatch.setattr(sp1paper, "_candles", candles)
    monkeypatch.setattr(sp1paper.time, "sleep", lambda s: None)


def test_d0_reads_the_official_open_live_and_the_first_tick_when_it_is_not_confirmed(monkeypatch):
    tokens = {"NIFTY 50": 1, "NIFTY BANK": 2}
    _first_tick(monkeypatch, {1: 24518.2, 2: 57545.7})                 # 6 Nov's first ticks
    k = K({"NIFTY 50": 24538.2, "NIFTY BANK": 57812.9})                # the official opens
    arrs, info = sp1paper.index_bars(k, DAY, tokens, 0, live=True, pre={"NIFTY 50": 24538.2, "NIFTY BANK": 57812.9})
    assert float(arrs["NIFTY BANK"]["open"][0]) == 57812.9 and float(arrs["NIFTY 50"]["open"][0]) == 24538.2
    assert info["NIFTY BANK"]["source"].startswith("official open") and info["NIFTY BANK"]["pre_open"] == 57812.9 and info["NIFTY BANK"]["bars"] == 1
    # Bank Nifty's gap that day: official +0.07% (the plan's 'flat' row), first tick -0.39% ('down')
    prev = 57773.65
    assert abs(57812.9 / prev - 1) < 0.0025 and (57545.7 / prev - 1) <= -0.0025
    # no pre-open read (a late start): exactly the old behaviour, and the ledger says why
    arrs, info = sp1paper.index_bars(k, DAY, tokens, 0, live=True, pre={})
    assert float(arrs["NIFTY BANK"]["open"][0]) == 57545.7 and "official open not used: no pre-open read" in info["NIFTY BANK"]["source"]
    # the replay and every later point are untouched: no quote is asked for
    k2 = K({"NIFTY 50": 1.0, "NIFTY BANK": 1.0})
    arrs, info = sp1paper.index_bars(k2, DAY, tokens, 0, live=False)
    assert float(arrs["NIFTY BANK"]["open"][0]) == 57545.7 and info["NIFTY BANK"]["source"] == "historical" and k2.calls == 0
