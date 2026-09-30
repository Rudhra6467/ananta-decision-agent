"""Candidate paper runner: parity with the research indicators + forward behaviour."""
import math
from pathlib import Path

from src.intelligence import candidate_paper as cp

H, H4, D = cp.H_MS, cp.H4_MS, cp.D_MS
T0 = 1_780_000_000_000 - (1_780_000_000_000 % D)


def _series(n, step, start, f, width=0.004):
    out = []
    for i in range(n):
        c0, c1 = f(i), f(i + 1)
        out.append([start + i * step, c0, max(c0, c1) * (1 + width), min(c0, c1) * (1 - width), c1, 10.0])
    return out


def test_indicators_match_research_versions():
    try:
        import numpy as np

        from src.research import entry_v2, mtf_entry
    except ImportError:  # the agent venv has no numpy; parity is checked where it exists
        return
    rng = np.random.default_rng(3)
    c = list(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 400))))
    bars = [[i, c[i - 1] if i else c[0], c[i] * 1.01, c[i] * 0.99, c[i], 1.0] for i in range(400)]
    assert max(abs(a - b) for a, b in zip(cp.ema(c, 20), mtf_entry.ema(np.array(c), 20))) < 1e-9
    h, lo, cl = (np.array([b[k] for b in bars]) for k in (2, 3, 4))
    assert max(abs(a - b) for a, b in zip(cp.atr(bars), mtf_entry.atr(h, lo, cl))) < 1e-9
    tr = entry_v2.trend_of(np.array(c))
    assert all(cp.trend(c[: i + 1]) == tr[i] for i in range(60, 400, 7))


def _feed():
    """Daily + 4h uptrend ending at T0, wide enough 4h bars for the >=3% target rule."""
    daily = _series(200, D, T0 - 200 * D, lambda i: 100 * math.exp(0.004 * i))
    h4 = _series(200, H4, T0 - 200 * H4, lambda i: 150 * math.exp(0.0015 * i), width=0.015)
    return {"1d": daily, "4h": h4, "1h": []}


def _hours(level, n, dip=None, crash_from=None):
    out = []
    for i in range(n):
        px = level * (1 + 0.0003 * i)
        o, hh, ll, c = px, px * 1.002, px * 0.998, px * 1.0003
        if dip and i == dip[0]:
            ll = dip[1]
        if crash_from is not None and i >= crash_from:
            o = hh = ll = c = level * 0.5
        out.append([T0 + i * H, o, hh, ll, c, 1.0])
    return out


def _fetcher(feed, upto_ms):
    return lambda coin, tf, limit: [b for b in feed[tf] if b[0] < upto_ms] if coin == "BTC" else []


def _add_4h_at_T0(feed):
    c = feed["4h"][-1][4]
    feed["4h"].append([T0, c, c * 1.015, c * 0.985, c * 1.002, 10.0])  # closes at T0 + 4h
    s = cp.setup_at(feed["4h"], feed["1d"], len(feed["4h"]) - 1)
    assert s is not None, "fixture must be an uptrend with a >=3% target"
    return s


def test_forward_only_then_arms_fills_and_stops(tmp_path):
    book = tmp_path / "b.sqlite"
    feed = _feed()
    level = feed["4h"][-1][4]
    feed["1h"] = _hours(level, 2)
    r0 = cp.tick(fetch=_fetcher(feed, T0 + 1 * H), now_ms=T0 + 2 * H, book_path=book)
    assert r0["ledger"]["closed"] == 0 and not r0["ledger"]["open"] and not r0["events"]  # forward only
    s = _add_4h_at_T0(feed)
    feed["1h"] = _hours(level, 40, dip=(6, s["limit"] * 0.999), crash_from=20)
    r1 = cp.tick(fetch=_fetcher(feed, T0 + 30 * H), now_ms=T0 + 31 * H, book_path=book)
    kinds = [e["kind"] for e in r1["events"]]
    assert kinds == ["ARMED", "FILLED", "CLOSED"], kinds
    led = r1["ledger"]
    assert led["closed"] == 1 and led["losses"] == 1 and led["counts_for_m2"] is False and led["exec"] is False
    b = cp.Book(book)
    t = b.trades()[0]
    b.close()
    assert abs(t["entry"] - s["limit"]) < 1e-9  # limit fill at the limit (bar opened above it)
    assert t["entry_ms"] == T0 + 6 * H  # never before the setup closed (T0+4h)
    stop = t["entry"] - 1.5 * t["A"]
    assert abs(t["exit"] - min(stop, feed["1h"][20][1])) < 1e-9  # crash opens below the stop: fill at the open
    fees = t["entry_fee_usd"] + t["qty"] * t["exit"] * (cp.NDAX_FEE + cp.HALF_SPREAD["BTC"])
    assert abs(t["net_usd"] - (t["qty"] * (t["exit"] - t["entry"]) - fees)) < 1e-6


def test_dip_before_setup_close_is_ignored(tmp_path):
    book = tmp_path / "b.sqlite"
    feed = _feed()
    level = feed["4h"][-1][4]
    feed["1h"] = _hours(level, 2)
    cp.tick(fetch=_fetcher(feed, T0 + 1 * H), now_ms=T0 + 2 * H, book_path=book)
    s = _add_4h_at_T0(feed)
    feed["1h"] = _hours(level, 12, dip=(2, s["limit"] * 0.99))  # hour 2 is inside the 4h bar, before its close
    r = cp.tick(fetch=_fetcher(feed, T0 + 10 * H), now_ms=T0 + 11 * H, book_path=book)
    assert "FILLED" not in [e["kind"] for e in r["events"]]


def test_unfilled_order_expires_after_24h(tmp_path):
    book = tmp_path / "b.sqlite"
    feed = _feed()
    level = feed["4h"][-1][4]
    feed["1h"] = _hours(level, 2)
    cp.tick(fetch=_fetcher(feed, T0 + 1 * H), now_ms=T0 + 2 * H, book_path=book)
    _add_4h_at_T0(feed)
    feed["1h"] = _hours(level, 40)
    r = cp.tick(fetch=_fetcher(feed, T0 + 35 * H), now_ms=T0 + 36 * H, book_path=book)
    assert [e["kind"] for e in r["events"]] == ["ARMED"]
    b = cp.Book(book)
    assert (b.state("BTC") or {}).get("orders") == []  # expired at setup close + 24h, never filled
    b.close()


def test_v1_ride_exits_on_daily_close_below_ema20(tmp_path):
    book = tmp_path / "v1.sqlite"
    feed = _feed()
    level = feed["4h"][-1][4]
    feed["1h"] = _hours(level, 2)
    cp.tick(fetch=_fetcher(feed, T0 + 1 * H), now_ms=T0 + 2 * H, book_path=book, rules="V1_RIDE")
    s = _add_4h_at_T0(feed)
    feed["1h"] = _hours(level, 30, dip=(6, s["limit"] * 0.999))
    # the daily bar that opens at T0 closes at T0+24h far below its EMA20 (but the hourly prices stay above the stop)
    feed["1d"].append([T0, level, level * 1.01, level * 0.5, level * 0.6, 1.0])
    r = cp.tick(fetch=_fetcher(feed, T0 + 28 * H), now_ms=T0 + 29 * H, book_path=book, rules="V1_RIDE")
    kinds = [(e["kind"], e.get("reason")) for e in r["events"]]
    assert kinds == [("ARMED", None), ("FILLED", None), ("CLOSED", "DAILY_EMA20")], kinds
    b = cp.Book(book)
    t = b.trades()[0]
    b.close()
    assert t["rules"] == "V1_RIDE" and abs(t["exit"] - feed["1h"][24][1]) < 1e-9  # the open of the first hour after the daily close
    assert t["exit_ms"] == T0 + 25 * H


def test_v1_ride_stop_is_wider_than_v0(tmp_path):
    book = tmp_path / "v1.sqlite"
    feed = _feed()
    level = feed["4h"][-1][4]
    feed["1h"] = _hours(level, 2)
    cp.tick(fetch=_fetcher(feed, T0 + 1 * H), now_ms=T0 + 2 * H, book_path=book, rules="V1_RIDE")
    s = _add_4h_at_T0(feed)
    hours = _hours(level, 20, dip=(6, s["limit"] * 0.999))
    e = s["limit"]
    hours[10][3] = e - 2.0 * s["A"]  # would stop V0 (1.5A), must NOT stop V1 (2.5A)
    hours[14][3] = e - 2.6 * s["A"]  # stops V1
    feed["1h"] = hours
    r = cp.tick(fetch=_fetcher(feed, T0 + 18 * H), now_ms=T0 + 19 * H, book_path=book, rules="V1_RIDE")
    closed = [e_ for e_ in r["events"] if e_["kind"] == "CLOSED"]
    assert len(closed) == 1 and closed[0]["reason"] == "STOP"
    b = cp.Book(book)
    t = b.trades()[0]
    b.close()
    assert t["exit_ms"] == T0 + 15 * H and abs(t["exit"] - (e - 2.5 * s["A"])) < 1e-9


def test_wind_down_never_opens_new_positions(tmp_path):
    book = tmp_path / "v0.sqlite"
    feed = _feed()
    level = feed["4h"][-1][4]
    feed["1h"] = _hours(level, 2)
    cp.tick(fetch=_fetcher(feed, T0 + 1 * H), now_ms=T0 + 2 * H, book_path=book, new_entries=False)
    s = _add_4h_at_T0(feed)
    feed["1h"] = _hours(level, 30, dip=(6, s["limit"] * 0.999))
    r = cp.tick(fetch=_fetcher(feed, T0 + 28 * H), now_ms=T0 + 29 * H, book_path=book, new_entries=False)
    assert r["events"] == [] and r["ledger"]["closed"] == 0 and not r["ledger"]["open"]


def test_no_setup_in_downtrend():
    daily = _series(200, D, T0 - 200 * D, lambda i: 100 * math.exp(-0.004 * i))
    h4 = _series(200, H4, T0 - 200 * H4, lambda i: 50 * math.exp(-0.0015 * i))
    assert all(cp.setup_at(h4, daily, k) is None for k in range(60, 200))


if __name__ == "__main__":
    import inspect
    import tempfile

    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn(*([Path(tempfile.mkdtemp())] if inspect.signature(fn).parameters else []))
            print("ok", name)
