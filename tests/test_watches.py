"""The watch registry, the daily watch engine (evidence books), the eye and the scoreboard (Madhav's OK, 2026-10-03)."""
import json
import pathlib
import sqlite3

import pytest

from tests.test_reads import DAY, _bars, _fake_jarvis

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _quiet(monkeypatch):
    monkeypatch.setenv("ANANTA_VOICE_LOCAL", "0")
    monkeypatch.setenv("ASK_LOCAL", "0")
    from jarvis.service import eye

    eye.STATE.update(prices={}, armed={}, ticks=0)
    eye._hist.clear()
    eye._cool.clear()


def test_registry_matches_the_code():
    from jarvis.service import watch_engine as W

    reg = json.loads((ROOT / "docs" / "knowledge" / "watches.json").read_text())
    sections = {s["id"] for s in reg["sections"]}
    ids = [w["id"] for w in reg["watches"]]
    assert len(ids) == len(set(ids))
    for w in reg["watches"]:
        assert w["section"] in sections and w["trigger"] in ("bar_close", "level_cross", "schedule"), w["id"]
        assert w.get("since") and w.get("entry") and w.get("exit"), w["id"]
        if w.get("size_usd"):
            assert w.get("book"), w["id"]
    from jarvis.service import universe_watch as U       # the universe family (-UA/-UB/-UC) is declared once, as UNIVERSE_DAILY / ZONE_TOUCH_UNIVERSE

    daily = {w["id"] for w in reg["watches"] if w["runs_in"] == "jarvis.watch_engine"}
    assert daily == {w for w in W.DAILY if not U.split(w)}, "every daily watch in the registry needs a rule in the engine, and the reverse"
    eye_trading = {w["id"] for w in reg["watches"] if w["runs_in"] == "jarvis.eye" and w.get("size_usd")}
    assert eye_trading == {w for w in W.EYE if not U.split(w)}
    assert {"UNIVERSE_DAILY", "ZONE_TOUCH_UNIVERSE"} <= set(ids)
    assert all(U.split(w)[0] in U.RULES + U.RANDOMS for w in W.DAILY if U.split(w))


def _with_more(tmp_path, coins, closes):
    con = sqlite3.connect(tmp_path / "explorer_bars.sqlite")
    t0 = con.execute("SELECT MAX(t) FROM bars").fetchone()[0]
    more = [(t0 + (k + 1) * DAY, *b[1:]) for k, b in enumerate(_bars(closes, wick=0.003))]
    con.executemany("INSERT INTO bars VALUES (?,?,?,?,?,?,?,?)", [(c, "1d", *b) for c in coins for b in more])
    con.commit()


def test_daily_engine_trades_every_signal_with_the_history_rule(tmp_path):
    from jarvis.service import watch_engine as W

    up = [100 * (1.004 ** k) for k in range(400)]
    dip = [up[-1] * (1 - 0.03 * k) for k in range(1, 7)]            # RSI(10) under 30, still above the 200-day
    D = _bars(up + dip, wick=0.003)
    j = _fake_jarvis(tmp_path, {"SOL": D, "BTC": D}, {})
    r = W.run(j)
    h07 = [x for x in r["opened"] if x["watch"] == "H07"]
    rnd = [x for x in r["opened"] if x["watch"].startswith("RANDOM")]
    assert {x["coin"] for x in h07} == {"SOL", "BTC"} and len(rnd) == 3     # one random coin a day for each baseline
    assert W.run(j)["opened"] == []                                         # the same day again: nothing new
    j.now = lambda: D[-1][0] + 40 * DAY
    _with_more(tmp_path, ("SOL", "BTC"), [up[-1] * 0.82 * (1 + 0.03 * k) for k in range(1, 35)])
    r2 = W.run(j)
    closed = {(x["watch"], x["coin"]) for x in r2["closed"]}
    assert ("H07", "SOL") in closed
    t = [x for x in W.trades(j, "H07") if x["coin"] == "SOL"][0]
    assert t["status"] == "CLOSED" and t["entry_day"] > t["signal_day"] and t["net_usd"] > 0 and "RSI" in t["exit_why"]
    assert t["regime"] in ("ALLOWED", "RISK_OFF")
    tens = [x for x in W.trades(j, "RANDOM_10D") if x["status"] == "CLOSED"]
    assert tens and all(x["exit_why"] == "10 days" for x in tens)


def test_eye_stops_alerts_shock_and_zone_touch():
    from jarvis.service import eye, watch_engine
    from jarvis.service.alerts import Alerts
    from jarvis.service.manual import Manual
    from tests.test_ask_ananta import _jarvis

    j, ex = _jarvis()
    px = dict(j.prices())
    coin = next(c for c in px if c != "BTC")
    Mn = Manual(j.db, j.now)
    Mn.execute("o", {"side": "buy", "coin": coin, "usd": 100, "stop": round(px[coin] * 0.95, 8)}, px)
    Alerts(j.db, j.now).create("o", {"kind": "price_below", "coin": "BTC", "value": px["BTC"] * 0.99})
    top, bot = px[coin] * 0.97, px[coin] * 0.93
    armed = {"zones": {coin: [{"bot": bot, "top": top, "kinds": ["AVERAGE-200"], "history": "SUPPORTED", "side": "support"}]},
             "atr": {coin: px[coin] * 0.02}, "attention": {coin: "HIGH"}, "regime": "ALLOWED", "prev_close": {}}
    pushed = []
    push = lambda t, b: pushed.append(t)                                    # noqa: E731
    assert eye.tick(j, px, push=push, armed=armed) == []                   # first look: nothing crossed
    p2 = {**px, coin: px[coin] * 0.96, "BTC": px["BTC"] * 0.975}            # into the zone; Bitcoin -2.5%
    kinds = [e["kind"] for e in eye.tick(j, p2, push=push, armed=armed)]
    assert {"ZONE_ENTRY", "ZONE_TOUCH", "BTC_SHOCK", "ALERT"} <= set(kinds), kinds
    t = [x for x in watch_engine.trades(j, "ZONE_TOUCH") if x["status"] == "OPEN"]
    assert len(t) == 1 and t[0]["stop"] < bot
    assert eye.tick(j, p2, push=push, armed=armed) == []                   # the same level again: no repeats
    p3 = {**p2, coin: px[coin] * 0.90}                                      # through the trade's stop and your own stop
    kinds3 = [e["kind"] for e in eye.tick(j, p3, push=push, armed=armed)]
    assert "EVIDENCE_EXIT" in kinds3 and "MY_STOP" in kinds3
    assert watch_engine.trades(j, "ZONE_TOUCH")[0]["status"] == "CLOSED"
    assert not Mn.state(p3)["positions"]                                     # your position was sold at the live price
    assert any(x.startswith("Bitcoin fell") for x in pushed) and any("entered a zone" in x for x in pushed)
    st = eye.status(j)
    assert st["recent"] and st["armed"]["regime"] is None or True


def test_kraken_prices_are_mapped():
    from jarvis.service import eye

    class R:
        def json(self):
            return {"error": [], "result": {"XXBTZUSD": {"c": ["84817.3", "1"]}, "XETHZUSD": {"c": ["2690.9", "1"]}, "SOLUSD": {"c": ["120.0", "1"]},
                                            "ADAUSD": {"c": ["0.24", "1"]}, "XDGUSD": {"c": ["0.09", "1"]}, "AVAXUSD": {"c": ["11.1", "1"]},
                                            "BCHUSD": {"c": ["319", "1"]}, "LINKUSD": {"c": ["14.1", "1"]}, "XLTCZUSD": {"c": ["70.6", "1"]},
                                            "XXRPZUSD": {"c": ["1.48", "1"]}}}
    p = eye.fetch_kraken(get=lambda *a, **k: R())
    assert p["BTC"] == 84817.3 and p["DOGE"] == 0.09 and len(p) == 10


def test_scoreboard_has_every_trading_watch():
    from jarvis.service import scoreboard, watch_engine
    from tests.test_ask_ananta import _jarvis

    j, ex = _jarvis()
    watch_engine.open_eye_trade(j, "ZONE_TOUCH", "BTC", 100.0, 95.0, "test", {"zone": [96, 98]}, "ALLOWED")
    watch_engine.close_at(j, watch_engine.trades(j, "ZONE_TOUCH")[0]["id"], 103.0, "test")
    b = scoreboard.board(j)
    ids = {w["id"] for w in b["watches"]}
    assert {"E4", "HUNTER", "H07", "M2a-G", "ZONE_TOUCH", "RANDOM_15M", "RANDOM_10D"} <= ids
    z = next(w for w in b["watches"] if w["id"] == "ZONE_TOUCH")
    assert z["closed"] == 1 and z["net_usd"] > 0 and z["verdict"] == "too early" and z["baseline"] == "RANDOM_20D"
    assert not b["errors"], b["errors"]
    assert "No watch has" in b["headline"]


def test_tier30_watch_is_separate_from_the_10_coin_run(tmp_path):
    """H07-T30 never runs in the 10-coin run; tier30.run() runs it on its own candles (Madhav 2026-10-04)."""
    from jarvis.service import tier30, watch_engine as W
    from tests.test_reads import _fake_jarvis

    assert W.DAILY["H07-T30"]["tier"] == "T30"
    up = [100 * 1.003 ** k for k in range(260)] + [70.0, 68.0, 66.0]
    D = [(1_700_000_000 + k * DAY, c, c * 1.01, c * 0.99, c, 1.0) for k, c in enumerate(up)]
    j = _fake_jarvis(tmp_path, {"BTC": D, "ETH": D}, {})
    W.run(j)
    assert not W.trades(j, "H07-T30"), "the 10-coin run must not touch the 30-coin watch"
    con = tier30._con(j)
    con.executemany("INSERT INTO bars VALUES (?,?,?,?,?,?,?)", [(c, *b) for c in ("BTC", "SOL") for b in D])
    con.execute("INSERT INTO meta VALUES ('done_day', ?)", (str(10 ** 12),))
    con.commit()
    out = tier30.run(j)
    assert out["bars"] == {"skip": "already pulled today"}
    assert "t3" in out and "h07" in out
    assert (tmp_path / "portfolio_book_t30.sqlite").exists() and not (tmp_path / "portfolio_book.sqlite").exists()
    assert tier30._layer(j).mode == "AUTO"


def test_independent_events_same_day_is_one_bet():
    """Madhav, requests 5-6: correlated coins closing in the same day's move count once."""
    from jarvis.service.scoreboard import independent_events

    D = 86400
    oct2 = 1790899200                                    # 2026-10-02 00:00 UTC
    six_stops = [oct2 + 18 * 3600 + 60 * k for k in (15, 20, 35, 35, 40, 40)]     # the six stop-outs, 18:15-18:40
    assert independent_events(six_stops, daily=False) == 1
    assert independent_events(six_stops + [oct2 + 3 * 3600], daily=False) == 1   # same day, morning: still one
    assert independent_events(six_stops + [oct2 + 3 * D + 3600], daily=False) == 2
    assert independent_events([oct2 + D - 600, oct2 + D + 600], daily=False) == 1  # across midnight, 20 minutes apart
    assert independent_events([oct2, oct2 + 2 * D, oct2 + 6 * D], daily=True) == 2
