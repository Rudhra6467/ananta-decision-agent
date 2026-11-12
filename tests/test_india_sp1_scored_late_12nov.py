"""12 Nov 2026, the keen outside audit, audit repair 4 (open-list flag 120), G-01 (Madhav's yes of 12 Nov 01:52, which re-opens the 9 Nov
decision R-048): the options line's 6 Nov Bank Nifty trade was to close at the next open; the next day in Kite's candles was the Muhurat
hour of Sun 8 Nov (about an hour of bars, no full session), so the study's outcome was 'not defined', the trade had no result and every
total left it out. A NEXTOPEN exit is now the next REGULAR session's open; a noted trade is scored again while its contract trades, once,
and marked scored late; the note stays in the hash-chained ledger and is never written twice. Each check failed against the code before.
No Kite, no live data: the candles, the plan and the calendar are made here."""
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from india import ocstudy, readmodel, sp1paper  # noqa: E402

D5, D6, D8, D9, D10 = (dt.date(2026, 11, d) for d in (5, 6, 8, 9, 10))
TOK = {"NIFTY 50": 1, "NIFTY BANK": 2}
OPT = {"token": 3, "tradingsymbol": "BANKNIFTY26NOV57500CE", "lot": 35, "expiry": "2026-11-23", "strike": 57500, "type": "CE"}


def _bars(day: dt.date, start: float, step: float, gap: float = 0.0) -> list[dict]:
    """A regular session's 375 minute bars, or the Muhurat hour's 60 (13:45-14:44 IST) on Sun 8 Nov."""
    mins = range(270, 330) if day == D8 else range(ocstudy.NMIN)
    out = []
    for m in mins:
        p = start + gap + step * m
        out.append({"date": day, "m": m, "open": p, "high": p + 1.0, "low": p - 1.0, "close": p + 0.5, "volume": 1})
    return out


def _fake_candles(k, token, interval, a, b):
    rows = []
    for day in (D5, D6, D8, D9, D10):
        if a <= day <= b:
            if token == TOK["NIFTY 50"]:
                rows += _bars(day, 25500.0, 0.05, gap=10.0 * (day - D5).days)
            elif token == TOK["NIFTY BANK"]:
                rows += _bars(day, 57000.0, 0.2, gap=60.0 * (day - D5).days)        # a gentle rise: the 1 x ATR stop is never touched
            elif token == OPT["token"] and day != D5:
                rows += _bars(day, 300.0, 0.1, gap=0.0 if day == D6 else 700.0)      # the call opens far higher on Mon 9 Nov
    return pd.DataFrame(rows, columns=["date", "m", "open", "high", "low", "close", "volume"])


def _world(tmp_path, monkeypatch, noted: bool):
    root = tmp_path / "paper" / "sp1"
    root.mkdir(parents=True)
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(sp1paper, "ROOT", root)
    monkeypatch.setattr(sp1paper, "DECISIONS", root / "decisions.jsonl")
    monkeypatch.setattr(sp1paper, "OUTCOMES", root / "outcomes.jsonl")
    plan = tmp_path / "plan_2026-11-06.json"
    plan.write_text(json.dumps({"prev_date": "2026-11-05", "index_tokens": TOK, "overnight": {"BANKNIFTY": {"atr14_prev": 600.0}},
                                "contracts": {"NIFTY": {"lot": 75}, "BANKNIFTY": {"lot": 35}}}))
    monkeypatch.setattr(sp1paper, "_plan_path", lambda d: plan)
    monkeypatch.setattr(sp1paper, "_specials", lambda: {dt.date(2026, 2, 1)})          # the real list: 8 Nov is not in it
    monkeypatch.setattr(sp1paper.kite, "Kite", lambda *a, **k: object())
    calls = []
    monkeypatch.setattr(sp1paper, "_candles", lambda *a: calls.append(a[1]) or _fake_candles(*a))
    monkeypatch.setattr(sp1paper, "_ist_now", lambda: dt.datetime(2026, 11, 16, 17, 30, tzinfo=sp1paper.IST))
    dec = sp1paper._append(root / "decisions.jsonl", {
        "kind": "decision", "date": "2026-11-06", "index": "BANKNIFTY", "point": "D0", "tradable": True, "entry_bar": 1, "fill_next_bar": 2,
        "decided_at": "2026-11-06T09:15:09+05:30", "choice": {"action": 10, "exit": "NEXTOPEN", "dir": 1, "pred_net": 5.0},
        "contracts": {"option": dict(OPT)}})
    if noted:                                   # what the scorer wrote on the evening of Mon 9 Nov
        sp1paper._append(root / "outcomes.jsonl", {"kind": "outcome", "date": "2026-11-06", "index": "BANKNIFTY", "point": "D0", "action": 10,
                                                   "note": "the study's outcome is not defined for this day (e.g. NEXTOPEN with no usable next session)",
                                                   "decision_hash": dec["hash"]})
    return root, calls


def test_the_6_nov_trade_is_scored_late_at_the_next_regular_open_once_and_the_note_stays(tmp_path, monkeypatch):
    root, calls = _world(tmp_path, monkeypatch, noted=True)
    sp1paper.score(day=dt.date(2026, 11, 24), log=lambda s: None)                        # after the contract's expiry: not tried, no Kite read
    assert calls == [] and len(sp1paper._rows(root / "outcomes.jsonl")) == 1
    sp1paper.score(day=dt.date(2026, 11, 16), log=lambda s: None)
    rows = sp1paper._rows(root / "outcomes.jsonl")
    assert len(rows) == 2 and rows[0].get("note") and "index_proxy" not in rows[0]       # the note stays where it was
    late = rows[1]
    assert late["scored_late"] is True and late["index_proxy"]["next_day"] is True and late["skipped_days"] == ["2026-11-08"]
    assert "Sun 8 Nov" in late["late_why"] and "Mon 9 Nov" in late["late_why"] and "12 Nov 2026" in late["late_why"]
    opt = late["legs"]["option"]
    assert opt["exit"] == 300.0 + 700.0 + 0.1 * 1 and "Mon 9 Nov" in opt["exit_rule"] and opt["net_rs_realistic"] > 0
    sp1paper.score(day=dt.date(2026, 11, 17), log=lambda s: None)                        # scored once: nothing more, no second note
    assert len(sp1paper._rows(root / "outcomes.jsonl")) == 2 and sp1paper.verify()["outcomes"]["chain"] == "intact"
    book = json.loads((root / "book.json").read_text())["by_index"]["BANKNIFTY"]
    assert book["trades"] == 1 and book["scored_late"] == 1 and book["option_1lot_rs_realistic_fill"] == round(opt["net_rs_realistic"])


def test_a_next_open_on_a_weekend_special_session_is_the_next_regular_open_the_first_time(tmp_path, monkeypatch):
    root, _ = _world(tmp_path, monkeypatch, noted=False)
    sp1paper.score(day=D8, log=lambda s: None)                                           # Sun 8 Nov: no regular session yet, it waits
    assert sp1paper._rows(root / "outcomes.jsonl") == []
    sp1paper.score(day=D9, log=lambda s: None)
    rows = sp1paper._rows(root / "outcomes.jsonl")
    assert len(rows) == 1 and "index_proxy" in rows[0] and not rows[0].get("note")       # it was 'not defined' before
    assert rows[0]["skipped_days"] == ["2026-11-08"] and not rows[0].get("scored_late")


def test_the_read_model_names_a_trade_left_out_until_it_is_scored(tmp_path, monkeypatch):
    root, _ = _world(tmp_path, monkeypatch, noted=True)
    monkeypatch.setattr(readmodel, "_today_ist", lambda: "2026-11-13", raising=False)                  # before the option's 23 Nov expiry
    sp1paper.write_book()
    s = readmodel.sp1("2026-11-06")
    assert "Not in these figures: 1 trade with no result yet (BANKNIFTY Fri 6 Nov)" in s["words"]
    assert s["left_out"] == [{"date": "2026-11-06", "index": "BANKNIFTY", "expiry": "2026-11-23", "never": False}]
    sp1paper.score(day=dt.date(2026, 11, 16), log=lambda s: None)
    s = readmodel.sp1("2026-11-06")
    assert "Not in these figures" not in s["words"] and s["left_out"] == [] and "1 scored trade(s) (1 scored late)" in s["words"]


# ---- 12 Nov 2026, the outside check of repair 4 (N6): a weekday special session is no regular session either ----
W2, W3, W4, W5 = (dt.date(2026, 11, d) for d in (2, 3, 4, 5))       # Tue 3 Nov decided; Wed 4 Nov made a short weekday session here


def _bars_w(day: dt.date, start: float, step: float, gap: float = 0.0) -> list[dict]:
    mins = range(270, 330) if day == W4 else range(ocstudy.NMIN)
    return [{"date": day, "m": m, "open": start + gap + step * m, "high": start + gap + step * m + 1.0, "low": start + gap + step * m - 1.0,
             "close": start + gap + step * m + 0.5, "volume": 1} for m in mins]


def _fake_candles_w(k, token, interval, a, b):
    rows = []
    for day in (W2, W3, W4, W5):
        if a <= day <= b:
            if token == TOK["NIFTY 50"]:
                rows += _bars_w(day, 25500.0, 0.05, gap=10.0 * (day - W2).days)
            elif token == TOK["NIFTY BANK"]:
                rows += _bars_w(day, 57000.0, 0.2, gap=60.0 * (day - W2).days)
            elif token == OPT["token"] and day != W2:
                rows += _bars_w(day, 300.0, 0.1, gap=0.0 if day == W3 else 500.0)
    return pd.DataFrame(rows, columns=["date", "m", "open", "high", "low", "close", "volume"])


def test_a_next_open_on_a_weekday_special_session_is_scored_at_the_next_whole_session(tmp_path, monkeypatch):
    root, _ = _world(tmp_path, monkeypatch, noted=False)
    (root / "decisions.jsonl").unlink()
    plan = tmp_path / "plan_2026-11-03.json"
    plan.write_text(json.dumps({"prev_date": "2026-11-02", "index_tokens": TOK, "overnight": {"BANKNIFTY": {"atr14_prev": 600.0}},
                                "contracts": {"NIFTY": {"lot": 75}, "BANKNIFTY": {"lot": 35}}}))
    monkeypatch.setattr(sp1paper, "_plan_path", lambda d: plan)
    monkeypatch.setattr(sp1paper, "_candles", lambda *a: _fake_candles_w(*a))
    sp1paper._append(root / "decisions.jsonl", {
        "kind": "decision", "date": "2026-11-03", "index": "BANKNIFTY", "point": "D0", "tradable": True, "entry_bar": 1, "fill_next_bar": 2,
        "decided_at": "2026-11-03T09:15:09+05:30", "choice": {"action": 10, "exit": "NEXTOPEN", "dir": 1, "pred_net": 5.0},
        "contracts": {"option": dict(OPT)}})
    sp1paper.score(day=W5, log=lambda s: None)
    rows = sp1paper._rows(root / "outcomes.jsonl")
    assert len(rows) == 1 and "index_proxy" in rows[0] and not rows[0].get("note")       # it was noted 'not defined', for ever, before
    assert rows[0]["skipped_days"] == ["2026-11-04"] and rows[0]["exit_day"] == "2026-11-05"
    assert "Thu 5 Nov" in rows[0]["legs"]["option"]["exit_rule"] and "Wed 4 Nov is no regular session" in rows[0]["legs"]["option"]["exit_rule"]
