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
