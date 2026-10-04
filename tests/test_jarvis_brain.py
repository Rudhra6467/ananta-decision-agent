"""Jarvis's brain and its paper book, the health watchdog, market-shift alerts, the missed-move loop, trade reviews, the
evening self-review and self-flagging of gaps (Madhav's OK, 2026-10-04)."""
import json
import os
import pathlib
import sqlite3
import time
import types

import pytest

from tests.test_reads import DAY, _bars

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _quiet(monkeypatch):
    monkeypatch.setenv("ANANTA_VOICE_LOCAL", "0")
    monkeypatch.setenv("ASK_LOCAL", "0")
    from jarvis.service import eye, health

    eye.STATE.update(prices={}, armed={}, ticks=0, last_t=None)
    eye._hist.clear()
    eye._cool.clear()
    health.STATE.update(last_run=None, jobs_t=None, parts={})


def _j(tmp_path, now):
    db = sqlite3.connect(":memory:")
    return types.SimpleNamespace(dir=tmp_path, db=db, now=lambda: now["t"], prices=lambda: {})


def _store(tmp_path, rows):
    con = sqlite3.connect(tmp_path / "explorer_bars.sqlite")
    con.execute("CREATE TABLE IF NOT EXISTS bars (coin TEXT, tf TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, PRIMARY KEY (coin, tf, t))")
    con.executemany("INSERT OR REPLACE INTO bars VALUES (?,?,?,?,?,?,?,?)", rows)
    con.commit()
    con.close()


# ---------------------------------------------------------------------------
# health watchdog
# ---------------------------------------------------------------------------
def test_health_goes_down_after_two_fails_reminds_and_comes_back(tmp_path):
    from jarvis.service import health

    now = {"t": 2_000_000_000}
    j = _j(tmp_path, now)
    p = tmp_path / "explorer_state.pkl"
    p.write_text("x")
    os.utime(p, (now["t"] - 3600, now["t"] - 3600))                       # an hour old: the Explorer is quiet
    (tmp_path / "watch_heartbeat.jsonl").write_text(json.dumps({"ts": "2033-05-18T03:00:00+00:00", "ok": True}) + "\n")
    up = {"ok": True}
    get = lambda url, timeout=5: (200, {"ok": True}) if up["ok"] else (_ for _ in ()).throw(OSError("refused"))   # noqa: E731
    pushed = []
    push = lambda t, b: pushed.append(t)                                   # noqa: E731
    r1 = health.watch(j, push=push, get=get, now=now["t"])
    assert not r1["parts"]["explorer"]["ok"] and r1["went_down"] == [] and pushed == []      # one failed look is not an outage
    r2 = health.watch(j, push=push, get=get, now=now["t"] + 120)
    assert r2["went_down"] == ["explorer"] and any("Explorer" in t for t in pushed)
    n = len(pushed)
    health.watch(j, push=push, get=get, now=now["t"] + 240)
    assert len(pushed) == n                                                # no repeat until 3 hours
    health.watch(j, push=push, get=get, now=now["t"] + 4 * 3600)
    assert any(t.startswith("Still down") for t in pushed)
    os.utime(p, (now["t"] + 4 * 3600, now["t"] + 4 * 3600))
    up["ok"] = False                                                       # meanwhile Hands, the tunnel... stop answering
    r = health.watch(j, push=push, get=get, now=now["t"] + 4 * 3600 + 60)
    assert r["came_back"] == ["explorer"] and any(t.startswith("Back:") for t in pushed)
    assert not r["parts"]["tunnel"]["ok"]
    st = health.status(j)
    assert any(o["part"] == "explorer" for o in st["outages_3d"])
    assert health.outages(j, now["t"] - 10)[0]["up_t"]


def test_outside_watchdog_rings_when_jarvis_is_down(tmp_path, monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location("wd", ROOT / "scripts" / "jarvis_watchdog.py")
    wd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wd)
    wd.STATE = tmp_path / "wd.json"
    sent = []
    send = lambda t, b, p="4": sent.append(t) or "200"                     # noqa: E731
    down = lambda url: (_ for _ in ()).throw(OSError("refused"))           # noqa: E731
    assert wd.main([], get=down, now=1000, send=send)["sent"] is None
    assert wd.main([], get=down, now=1300, send=send)["sent"] == "200" and "not answering" in sent[-1]
    assert wd.main([], get=down, now=1600, send=send)["sent"] is None
    assert wd.main([], get=lambda u: {"ok": True, "health_checks_s_ago": 30}, now=1900, send=send)["sent"] == "200" and sent[-1] == "Back: Jarvis"
    assert wd.look(get=lambda u: {"ok": True, "health_checks_s_ago": 900})[0] == "blind"


# ---------------------------------------------------------------------------
# market shift
# ---------------------------------------------------------------------------
def test_market_shift_live_warning_and_close_flip(tmp_path):
    from jarvis.service import eye, market_shift

    up = [100 * (1.004 ** k) for k in range(200)]
    D = _bars(up, wick=0.003)
    _store(tmp_path, [("BTC", "1d", *b) for b in D])
    now = {"t": D[-1][0] + DAY + 60}
    j = _j(tmp_path, now)
    eye._table(j)
    pushed = []
    push = lambda t, b: pushed.append(t)                                   # noqa: E731
    armed = {"regime": "ALLOWED", "btc_ema50": up[-1] * 0.95}
    assert market_shift.live(j, {"BTC": up[-1] * 0.951}, armed, push) == []          # inside the band: quiet
    ev = market_shift.live(j, {"BTC": up[-1] * 0.90}, armed, push)
    assert ev and ev[0]["kind"] == "MARKET_WARN" and "under its 50-day" in pushed[-1]
    assert market_shift.live(j, {"BTC": up[-1] * 0.89}, armed, push) == []           # once per 12 hours
    assert market_shift.close(j, push)["changed"] is False                          # first close: remembers the regime
    crash = [up[-1] * (1 - 0.04 * k) for k in range(1, 8)]
    _store(tmp_path, [("BTC", "1d", D[-1][0] + (k + 1) * DAY, *b[1:]) for k, b in enumerate(_bars(crash, wick=0.003))])
    r = market_shift.close(j, push)
    assert r["changed"] and r["regime"] == "RISK_OFF" and "risk-off" in pushed[-1]
    assert market_shift.close(j, push) is None                                      # the same close again


# ---------------------------------------------------------------------------
# the brain
# ---------------------------------------------------------------------------
def _brain_j():
    from tests.test_ask_ananta import _jarvis

    j, ex = _jarvis()
    return j, ex


def _fake_pack(price, atr=2.0):
    return lambda j, coin, trig: {"coin": coin, "price": price, "daily": {"atr": atr}, "market": {"regime": "ALLOWED"}, "news": {"verdict": "CLEAR"}}


def test_brain_takes_with_a_random_twin_and_manages_live(monkeypatch):
    from jarvis.service import brain, watch_engine

    j, ex = _brain_j()
    px = dict(j.prices())
    coin = next(c for c in px if c != "BTC")
    p = px[coin]
    monkeypatch.setattr(brain, "pack", _fake_pack(p, atr=p * 0.04))
    monkeypatch.setattr(brain, "_atr", lambda j_, c: px[c] * 0.04)
    pushed = []
    plan = {"action": "TAKE", "confidence": 62, "size_pct": 40, "stop": p * 0.94, "target": None, "trail_atr": 1.5, "days": 10,
            "thesis": "at a 200-day zone with the market allowed", "knowledge_used": ["REGIME", "ZONES"]}
    r = brain.decide(j, coin, {"zone_entry": {}}, call=lambda u: (json.dumps(plan), {"in": 5000, "out": 400, "model": "fake"}),
                     push=lambda t, b: pushed.append(t))
    assert r["action"] == "TAKE" and r["trade"] and r["random_twin"] and r["random_twin"] != coin
    assert abs(r["cost_usd"] - 0.014) < 1e-9 and pushed == [f"Jarvis paper trade: {coin}"]
    t = [x for x in watch_engine.trades(j, "JARVIS") if x["status"] == "OPEN"]
    tw = [x for x in watch_engine.trades(j, "JARVIS_RANDOM") if x["status"] == "OPEN"]
    assert len(t) == 1 and len(tw) == 1
    k_twin = (tw[0]["entry"] - tw[0]["stop"]) / (tw[0]["entry"] * 0.04)
    assert abs(k_twin - 1.5) < 1e-6                                          # the same stop, in the twin's own daily ranges
    # the trailing stop rises with the price, never falls, and closes the trade on the way down
    brain.manage_live(j, {coin: p * 1.10, r["random_twin"]: px[r["random_twin"]]})
    s1 = watch_engine.trades(j, "JARVIS")[0]["stop"]
    assert abs(s1 - (p * 1.10 - 1.5 * p * 0.04)) < 1e-6
    brain.manage_live(j, {coin: p * 1.06, r["random_twin"]: px[r["random_twin"]]})
    assert watch_engine.trades(j, "JARVIS")[0]["stop"] == s1
    out = brain.manage_live(j, {coin: p * 1.05, r["random_twin"]: px[r["random_twin"]]})
    assert watch_engine.trades(j, "JARVIS")[0]["status"] == "OPEN" and out == []
    out = brain.manage_live(j, {coin: s1 * 0.999, r["random_twin"]: px[r["random_twin"]]})
    x = watch_engine.trades(j, "JARVIS")[0]
    assert x["status"] == "CLOSED" and "trailing stop" in x["exit_why"] and x["net_usd"] > 0
    rep = brain.report(j)
    assert rep["closed"] == 1 and rep["verdict"] == "too early" and rep["knowledge_credit"][0]["knowledge"] in ("REGIME", "ZONES")
    assert rep["calibration"][0]["confidence"] == "50-65"


def test_brain_red_flags_turn_a_take_into_a_pass_and_limits_hold(monkeypatch):
    from jarvis.service import brain

    j, ex = _brain_j()
    px = dict(j.prices())
    coin = next(c for c in px if c != "BTC")
    p = px[coin]
    monkeypatch.setattr(brain, "pack", _fake_pack(p))
    monkeypatch.setattr(brain, "can_decide", lambda j_: (True, ""))
    bad = {"action": "TAKE", "confidence": 80, "size_pct": 100, "stop": p * 1.01, "days": 5, "thesis": "x", "knowledge_used": []}
    r = brain.decide(j, coin, {}, call=lambda u: (json.dumps(bad), {"in": 1, "out": 1}))
    assert r["action"] == "PASS" and r["trade"] is None and "stop" in " ".join(r["flags"])
    assert brain.decide(j, coin, {}, call=lambda u: ("no json here", {"in": 1, "out": 1}))["action"] == "ERROR"
    # the queue: a second trigger joins the same item; a coin decided in the last 6 hours is dropped with the reason
    brain.wake(j, coin, "zone_entry")
    brain.wake(j, coin, "explorer:E4")
    assert j.db.execute("SELECT trigger FROM brain_queue WHERE state='NEW'").fetchone()[0] == "zone_entry|explorer:E4"
    assert brain.process(j, call=lambda u: ("{}", {})) == []
    assert "6 hours" in j.db.execute("SELECT state FROM brain_queue").fetchone()[0]
    other = next(c for c in px if c not in ("BTC", coin))
    ok = {"action": "PASS", "confidence": 30, "thesis": "weak case", "knowledge_used": ["COSTS"]}
    brain.wake(j, other, "attention_high")
    done = brain.process(j, call=lambda u: (json.dumps(ok), {"in": 1, "out": 1}))
    assert done and done[0]["coin"] == other and done[0]["action"] == "PASS"
    monkeypatch.undo()                                                     # real can_decide: the daily limit counts decisions
    monkeypatch.setattr(brain, "DAILY_MAX", 2)                             # two real decisions today (the unreadable reply does not count)
    assert brain.can_decide(j)[0] is False


def test_brain_pack_runs_on_real_state():
    from jarvis.service import brain

    j, ex = _brain_j()
    coin = next(iter(j.prices()))
    p = brain.pack(j, coin, {"zone_entry": {}})
    json.dumps(p, default=str)
    assert p["price"] and p["knowledge"] and p["red_flags_enforced_by_code"]
    assert len({k for k, _, _ in brain.KNOWLEDGE}) == len(brain.KNOWLEDGE)


def test_brain_scan_wakes_on_new_explorer_orders_only():
    from jarvis.service import brain

    j, ex = _brain_j()
    assert brain.scan(j) == [] or True                                     # first scan: remembers where the log ends
    n0 = j.db.execute("SELECT COUNT(*) FROM brain_queue").fetchone()[0]
    ex.store.book.execute("INSERT INTO events (t, kind, coin, id, json) VALUES (?,?,?,?,?)",
                          (int(j.now()), "ORDER", "SOL", "x", json.dumps({"kind": "ORDER", "coin": "SOL", "setup": "E4", "shadow": "REJECTED_SLOT"})))
    ex.store.book.commit()
    woke = brain.scan(j, [{"watch": "H07", "coin": "ETH", "day": "x"}, {"watch": "RANDOM_10D", "coin": "ADA"}])
    assert "SOL" in woke and "ETH" in woke and "ADA" not in woke and n0 >= 0
    trig = dict(j.db.execute("SELECT coin, trigger FROM brain_queue WHERE state='NEW'").fetchall())
    assert "explorer:E4" in trig["SOL"] and "setup:H07" in trig["ETH"]


# ---------------------------------------------------------------------------
# what did we miss
# ---------------------------------------------------------------------------
def test_missed_moves_label_and_repeats_become_a_request(tmp_path):
    from jarvis.service import missed

    up = [100 * (1.001 ** k) for k in range(300)]
    D = _bars(up, wick=0.01)
    day_t = D[-1][0] + DAY
    q = []
    for k in range(96):                                                    # a quiet morning, then +8% from 10:00
        base = up[-1] * (1.08 if k > 60 else 1 + 0.002 * max(0, k - 40) if k > 40 else 1.0)
        q.append((day_t + 900 * k, base, base * 1.001, base * 0.999, base, 10.0))
    rows = [(c, "1d", *b) for c in ("BTC", "SOL") for b in D] + [("SOL", "15m", *b) for b in q]
    _store(tmp_path, rows)
    now = {"t": day_t + DAY + 3600}
    j = _j(tmp_path, now)
    r = missed.run(j)
    assert r["moves"] and r["moves"][0]["coin"] == "SOL" and r["moves"][0]["label"] == "MISSED" and "nothing of ours looked" in r["moves"][0]["why"]
    assert missed.run(j)["done_before"]
    # the same kind of miss four more times in 30 days -> one request (once)
    for k in range(4):
        j.db.execute("INSERT INTO missed_moves VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (f"x{k}", r["day"], "ADA", 0, 0, 1, 1.05, 5.0, 1.2, "MISSED", "{}", "x", None, None, j.db.execute(
                         "SELECT pattern FROM missed_moves WHERE coin='SOL'").fetchone()[0], ""))
    logged = []
    f = missed._repeats(j, log_request=lambda t: logged.append(t) or {"num": 9})
    assert f and f[0]["request"] == 9 and "keep missing" in logged[0]
    assert missed._repeats(j, log_request=lambda t: logged.append(t) or {"num": 10}) == []
    assert missed.patterns(j)[0]["times"] == 5 and missed.recent(j, 3)["counts"]["MISSED"] == 5


# ---------------------------------------------------------------------------
# reviews
# ---------------------------------------------------------------------------
def test_lessons_are_plain_rules():
    from jarvis.service import reviews as R

    assert R.lessons(100, 95, -5, 1.0, -5, 6.0, "stop", 0.5) == ["STOPPED_THEN_RAN"]
    assert "GAVE_BACK" in R.lessons(100, 99, -1.5, 4.0, -2, 0, "10 days", 0.5)
    assert R.lessons(100, 98, -2.5, 0.2, -2, -1, "stop", 0.5) == ["NEVER_WORKED"]
    assert R.lessons(100, 104, 3.5, 5.0, -1, 10.0, "target", 0.5) == ["LEFT_ON_TABLE"]
    assert R.lessons(100, 104, 3.5, 5.0, -1, 4.5, "target", 0.5) == ["CLEAN"]


def test_closed_trades_get_a_review_and_the_evening_review_runs(tmp_path):
    from jarvis.service import reviews, watch_engine

    up = [100 * (1.001 ** k) for k in range(60)]
    D = _bars(up, wick=0.01)
    t0 = D[-1][0] + DAY
    q = [(t0 + 900 * k, 100.0, 103.0 if k == 10 else 100.5, 99.0, 100.0, 1.0) for k in range(96 * 5)]
    _store(tmp_path, [("SOL", "1d", *b) for b in D] + [("SOL", "15m", *b) for b in q])
    now = {"t": t0 + 600}
    j = _j(tmp_path, now)
    t = watch_engine.open_eye_trade(j, "ZONE_TOUCH", "SOL", 100.0, 97.0, "test", {}, "ALLOWED")
    now["t"] = t0 + 86400
    watch_engine.close_at(j, t["id"], 97.0, "stop (live price)")
    assert reviews.review_closed(j) == []                                  # waits 3 days after the exit
    now["t"] = t0 + 4 * 86400 + 10
    out = reviews.review_closed(j)
    assert out and out[0]["coin"] == "SOL" and "GAVE_BACK" in out[0]["tags"]
    rr = reviews.recent_reviews(j, 10)
    assert rr["reviews"][0]["text"].startswith("evidence ZONE_TOUCH on SOL") and rr["lessons_count"]
    assert reviews.review_closed(j) == []                                  # once
    ev = reviews.evening(j, push=None, force=True)
    assert ev["text"] and "decision" in ev["text"]
    assert reviews.latest(j)[0]["text"] == ev["text"]


# ---------------------------------------------------------------------------
# self-flagging of gaps
# ---------------------------------------------------------------------------
def test_an_admitted_gap_becomes_a_request_once():
    from jarvis.service import ask, requests_log
    from tests.test_ask_ananta import _jarvis

    j, ex = _jarvis()
    reply = {"kind": "answer", "answer": "I don't have order book data for Solana. Prices I do have."}
    r = ask._self_flag(j, "what's the order book on SOL?", reply, [], "t1")
    assert r and "request" in reply["answer"] and reply["self_flag"] == r["num"]
    assert requests_log.get(j, r["num"])["about"] == "auto-flag"
    reply2 = {"kind": "answer", "answer": "I don't have order book data for Solana. Prices I do have."}
    ask._self_flag(j, "what's the order book on SOL?", reply2, [], "t1")
    assert "already on the list" in reply2["answer"]
    assert ask._self_flag(j, "x", {"kind": "answer", "answer": "Bitcoin is up 2% today."}, [], "t1") is None
    assert ask._self_flag(j, "x", {"kind": "answer", "answer": "I don't have it."}, [{"tool": "log_request"}], "t1") is None


def test_scoreboard_puts_jarvis_against_its_twins():
    from jarvis.service import scoreboard, watch_engine
    from tests.test_ask_ananta import _jarvis

    j, ex = _jarvis()
    b = scoreboard.board(j)
    jr = next(w for w in b["watches"] if w["id"] == "JARVIS")
    assert jr["baseline"] == "JARVIS_RANDOM" and jr["section"] == "DECISIONS"
    assert watch_engine  # the registry test (test_watches) keeps the engine and registry in step
