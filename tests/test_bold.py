"""Fix A8 (Oct 15): the bold book. Off unless both locks are open (BOLD_BOOK=1 and Madhav's approval in the mandate file); when on,
it must take its single best idea on a dial-open day (a PASS becomes a recorded mandate miss) and may sit on a closed day with a
reason. Its trades and twins are its own (never the safe book's slots or budget)."""
import json

from tests.test_universe_live import J

DAY = 86400
NOW = 1_760_000_000 - 1_760_000_000 % DAY + 900
PX = {"SOL": 100.0, "ETH": 50.0, "ADA": 1.0}


def _ready(tmp_path, monkeypatch, dial=1.0):
    from jarvis.service import bold, brain, stance

    j = J(tmp_path, now=NOW)
    brain._table(j)
    stance._table(j)
    f = {"dial": {"dial": dial}, "candidates": [{"coin": c, "close": p, "live": p} for c, p in PX.items()]}
    j.db.execute("INSERT INTO stance (day, t, dial, facts, source) VALUES (?,?,?,?,?)", (stance._day(NOW), NOW - 300, dial, json.dumps(f), "brain"))
    j.db.commit()
    monkeypatch.setattr(bold, "enabled", lambda: (True, ""))
    monkeypatch.setattr(stance, "candidates", lambda jj: list(PX))
    monkeypatch.setattr(brain, "_live_px", lambda jj, c: PX.get(c))
    monkeypatch.setattr(brain, "_atr", lambda jj, c: PX[c] * 0.04)
    monkeypatch.setattr(brain, "_regime_now", lambda jj: "ALLOWED")
    return j


def _reply(**kw):
    d = {"action": "TAKE", "coin": "SOL", "exit_plan": "TREND", "stop": 92.0, "thesis": "the strongest trend", "why_not_others": "weaker"}
    d.update(kw)
    return json.dumps(d), {"in": 1000, "out": 100, "model": "fake"}


def test_off_unless_both_locks_are_open(tmp_path, monkeypatch):
    from jarvis.service import bold

    j = J(tmp_path, now=NOW)
    monkeypatch.delenv("BOLD_BOOK", raising=False)
    monkeypatch.setattr(bold, "mandate", lambda: {"approved": "Madhav, test"})
    assert bold.enabled() == (False, "off: BOLD_BOOK is not 1 in the service's environment")
    monkeypatch.setenv("BOLD_BOOK", "1")
    monkeypatch.setattr(bold, "mandate", lambda: {"approved": None})
    ok, why = bold.enabled()
    assert not ok and "not approved" in why

    def never(u):
        raise AssertionError("no model call while off")
    assert "off" in bold.run(j, call=never)
    assert not j.db.execute("SELECT 1 FROM sqlite_master WHERE name='bold_decisions'").fetchone()     # nothing written at all


def test_an_open_day_must_take_one_and_a_pass_is_asked_once_more(tmp_path, monkeypatch):
    from jarvis.service import bold, brain

    j = _ready(tmp_path, monkeypatch, dial=1.0)
    replies = iter([_reply(action="SIT", thesis="nothing good"), _reply()])
    r = bold.run(j, call=lambda u: next(replies))
    assert r["action"] == "TAKE" and r["coin"] == "SOL" and r["cost_usd"] > 0
    rows = dict(j.db.execute("SELECT watch, coin FROM evidence_trades WHERE status='OPEN'").fetchall())
    assert rows["JARVIS_BOLD"] == "SOL" and rows["RANDOM_BOLD"] in ("ETH", "ADA")
    assert brain._account_open(j) == 0                                     # never the safe book's slots
    assert bold.run(j, call=lambda u: _reply()) is None                    # once a day
    assert bold.record(j)["open"] == 1 and bold.record(j)["decisions"] == {"TAKE": 1}


def test_a_refused_pick_on_an_open_day_is_a_recorded_mandate_miss(tmp_path, monkeypatch):
    from jarvis.service import bold

    j = _ready(tmp_path, monkeypatch, dial=1.0)
    r = bold.run(j, call=lambda u: _reply(stop=70.0))                      # 30% away, twice
    assert r["action"] == "MISS" and r["note"].startswith("mandate miss") and "15%" in r["note"]
    assert not j.db.execute("SELECT 1 FROM evidence_trades").fetchone()


def test_a_closed_day_may_sit_with_a_reason(tmp_path, monkeypatch):
    from jarvis.service import bold

    j = _ready(tmp_path, monkeypatch, dial=0.0)
    r = bold.run(j, call=lambda u: _reply(action="SIT", thesis="the dial is closed and nothing has a measured edge here"))
    assert r["action"] == "SIT" and "measured edge" in r["why"]
    assert j.db.execute("SELECT action, why FROM bold_decisions").fetchone()[0] == "SIT"


def test_the_bold_twin_pays_the_bold_books_costs(monkeypatch):
    from jarvis.service import registry, watch_engine

    monkeypatch.setattr(registry, "cost", lambda c, reg=None: 0.0123)
    assert watch_engine._cost("NEWCOIN", "RANDOM_BOLD") == 0.0123 == watch_engine._cost("NEWCOIN", "JARVIS_BOLD")
    assert watch_engine._cost("NEWCOIN", "RANDOM_10D") != 0.0123


def test_the_switches_the_brain_obeys_stop_the_bold_book_too(tmp_path, monkeypatch):
    """BRAIN_ENABLED=0 (or Ask switched off, or the day's AI budget used up) means no model call: an open day is a recorded miss
    with the reason, never a silent skip."""
    from jarvis.service import bold

    j = _ready(tmp_path, monkeypatch, dial=1.0)
    monkeypatch.setenv("BRAIN_ENABLED", "0")

    def never(u):
        raise AssertionError("no model call with the brain switched off")
    r = bold.run(j, call=never)
    assert r["action"] == "MISS" and "BRAIN_ENABLED" in r["note"] and r["cost_usd"] == 0
    assert j.db.execute("SELECT action, note FROM bold_decisions").fetchone() == ("MISS", r["note"])
    assert not j.db.execute("SELECT 1 FROM evidence_trades").fetchone()


def test_no_stacking_a_held_coin_is_recorded_not_bought_again(tmp_path, monkeypatch):
    """Madhav, Oct 16: the bold book may not stack the same coin. A pick of a coin it already holds open is WOULD_ADD:
    recorded with its plan and price, no trade and no twin opened, and the day still counts as decided."""
    from jarvis.service import bold

    j = _ready(tmp_path, monkeypatch, dial=1.0)
    first = bold.run(j, call=lambda u: _reply())
    assert first["action"] == "TAKE"
    n_trades = j.db.execute("SELECT COUNT(*) FROM evidence_trades").fetchone()[0]
    j.now = lambda: NOW + DAY                                   # next UTC day, same pick
    from jarvis.service import stance
    j.db.execute("INSERT INTO stance (day, t, dial, facts, source) VALUES (?,?,?,?,?)",
                 (stance._day(NOW + DAY), NOW + DAY - 300, 1.0,
                  json.dumps({"dial": {"dial": 1.0}, "candidates": [{"coin": c, "close": p, "live": p} for c, p in PX.items()]}), "brain"))
    j.db.commit()
    second = bold.run(j, call=lambda u: _reply())
    assert second["action"] == "WOULD_ADD" and second["coin"] == "SOL" and "no stacking" in second["note"]
    assert j.db.execute("SELECT COUNT(*) FROM evidence_trades").fetchone()[0] == n_trades    # nothing opened, no twin
    row = j.db.execute("SELECT action, trade_id, random_id FROM bold_decisions WHERE day=?", (bold._day(NOW + DAY),)).fetchone()
    assert row == ("WOULD_ADD", None, None)
    assert bold.run(j, call=lambda u: _reply()) is None                                    # the day is decided once


# -- Oct 20, Madhav "4. yes": each candidate's T3 rating in the pick input, T3's wording corrected, a flag (never a block) -------------
def _t3_book(tmp_path, ratings: dict) -> None:
    """A T3 book (portfolio_book.sqlite) with its decision for the close the facts were built on."""
    import sqlite3

    con = sqlite3.connect(str(tmp_path / "portfolio_book.sqlite"))
    con.execute("CREATE TABLE decisions (day_t INTEGER PRIMARY KEY, json TEXT)")
    con.execute("INSERT INTO decisions VALUES (?, ?)", (NOW - NOW % DAY, json.dumps({"ratings": ratings})))
    con.commit()
    con.close()


def _bars(close_t: int, n: int, step: float) -> list[tuple]:
    out, px = [], 100.0
    for i in range(n):
        t = close_t - (n - i) * DAY
        out.append((t, px, px * 1.01, px * 0.99, px, 1.0))
        px *= 1 + step
    return out


def test_the_bold_input_carries_each_candidates_t3_rating_and_the_corrected_wording(tmp_path, monkeypatch):
    from jarvis.service import bold, brain, stance

    j = _ready(tmp_path, monkeypatch, dial=1.0)
    _t3_book(tmp_path, {"SOL": {"rating": "OK", "hold": True, "why": ["above both averages"]},
                        "ETH": {"rating": "OUT", "hold": False, "why": ["closed below its 20-day average (fast exit)"]}})
    monkeypatch.setattr(stance, "_closed_daily", lambda jj, c: [])          # ADA: no candles, so no rating
    seen = []
    r = bold.run(j, call=lambda u: (seen.append(u), _reply())[1])
    user = seen[0]
    facts = json.loads(user.split("Tonight's facts (JSON):\n", 1)[1].split("\n\n", 1)[0])
    t3 = {c["coin"]: (c["t3"], c["t3_rating"]) for c in facts["candidates"]}
    assert t3 == {"SOL": ("IN", "OK"), "ETH": ("OUT", "OUT"), "ADA": (None, None)}
    assert bold.T3_WORDS in user and "NOT a 20-day hold" in user and "first daily close under the 20-day average" in user
    t3_line = next(w for k, s, w in brain.KNOWLEDGE if k == "T3")
    assert "20-day exit" not in t3_line and "not a 20-day hold" in t3_line
    assert "time exit" not in next(w for k, s, w in brain.KNOWLEDGE if k == "TRAIL").replace("not a time exit", "")
    assert r["action"] == "TAKE" and r["flag"] is None                    # SOL is IN; the thesis does not cite T3 anyway
    pack, saved, flag = j.db.execute("SELECT pack, t3, flag FROM bold_decisions").fetchone()
    assert pack == bold.PACK == "t3-v1" and json.loads(saved)["ETH"]["source"] == "portfolio_book.sqlite" and flag is None
    assert "mandate" not in bold.T3_WORDS.lower()                          # the mandate is unchanged: one idea a day, dial open


def test_a_pick_that_cites_t3_on_a_coin_t3_rates_out_is_flagged_never_blocked(tmp_path, monkeypatch):
    from jarvis.service import bold

    j = _ready(tmp_path, monkeypatch, dial=1.0)
    _t3_book(tmp_path, {"SOL": {"rating": "OK", "hold": True}, "ETH": {"rating": "OUT", "hold": False}, "ADA": {"rating": "WEAK", "hold": True}})
    r = bold.run(j, call=lambda u: _reply(coin="ETH", stop=46.0, thesis="ETH as T3: the trend portfolio holds it for 20 days",
                                          knowledge_used=["T3"]))
    assert r["action"] == "TAKE" and r["coin"] == "ETH" and r["trade_id"]          # the decision stays with the brain
    assert r["flag"] == bold.FLAG_T3_OUT == "cites_t3_on_out"
    flag, ku = j.db.execute("SELECT flag, knowledge_used FROM bold_decisions").fetchone()
    assert flag == "cites_t3_on_out" and json.loads(ku) == ["T3"]
    t3 = {"SOL": {"t3": "IN"}, "ETH": {"t3": "OUT"}}
    assert bold.t3_flag("SOL", t3, "Trend Portfolio says yes") is None              # cites T3, rated IN: no flag
    assert bold.t3_flag("ETH", t3, "the dial is open, BTC leads") is None           # rated OUT but T3 not cited: no flag
    assert bold.t3_flag("ETH", t3, None, "per the PORTFOLIO LAYER") == "cites_t3_on_out"
    assert bold.t3_flag(None, t3, "T3") is None


def test_a_coin_in_no_t3_book_is_rated_by_portfolio_layer_on_its_daily_candles(tmp_path):
    from jarvis.service import bold
    from tests.test_universe_live import J

    j = J(tmp_path, now=NOW)
    close_t = NOW - NOW % DAY
    up, down = _bars(close_t, 80, 0.01), _bars(close_t, 80, -0.01)
    daily = {"BTC": up, "UPC": up, "DNC": down, "NEW": up[-20:]}
    f = {"candidates": [{"coin": c} for c in ("UPC", "DNC", "NEW")]}
    r = bold.t3_ratings(j, f, daily=lambda c: daily[c])
    assert r["UPC"]["t3"] == "IN" and r["UPC"]["source"] == "computed"
    assert r["DNC"]["t3"] == "OUT" and any("50-day" in w for w in r["DNC"]["why"])
    assert r["NEW"]["t3"] is None                                                   # under 50 days: not rated
    daily["BTC"] = down                                                             # Bitcoin under its 50-day: the gate is off
    assert bold.t3_ratings(j, f, daily=lambda c: daily[c])["UPC"]["t3"] == "OUT"
