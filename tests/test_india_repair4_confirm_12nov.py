"""12 Nov 2026, audit repair 4's confirm check (~/ananta_runs/keen_audit/recheck/pkg4_confirm.md), the records half:
C1, a regular weekday short of some minutes for a data reason was called "no regular session" and the trade was scored two days later;
    and a trade scored with no price for its option was in no total and named by none;
C4, after its option expired, a left-out trade was still promised a score ("until scored", "with no result yet");
C5, two skipped days read as one ("Sun 8 Nov, Mon 9 Nov is no regular session").
Each check failed against the code before (26a82c4). No Kite, no live data: the candles, the plan and the ledgers are made here."""
import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from india import managed, morningview, ocstudy, readmodel, sp1paper  # noqa: E402
from tests.test_india_sp1_scored_late_12nov import OPT, TOK, _world  # noqa: E402

W3, W4, W5 = (dt.date(2026, 11, d) for d in (3, 4, 5))
D6, D8, D9, D10 = (dt.date(2026, 11, d) for d in (6, 8, 9, 10))


def _bars(day: dt.date, start: float, step: float, gap: float, mins) -> list[dict]:
    return [{"date": day, "m": m, "open": start + gap + step * m, "high": start + gap + step * m + 1.0, "low": start + gap + step * m - 1.0,
             "close": start + gap + step * m + 0.5, "volume": 1} for m in mins]


def _candles(days: dict, first):
    """days: {day: minutes}. Index bars rise gently (no stop is touched); the option opens far higher on every day after the first."""
    def fake(k, token, interval, a, b):
        rows = []
        for day, mins in days.items():
            if a <= day <= b:
                if token == TOK["NIFTY 50"]:
                    rows += _bars(day, 25500.0, 0.05, 10.0 * (day - first).days, mins)
                elif token == TOK["NIFTY BANK"]:
                    rows += _bars(day, 57000.0, 0.2, 60.0 * (day - first).days, mins)
                elif token == OPT["token"] and day > first:
                    rows += _bars(day, 300.0, 0.1, 0.0 if day == first + dt.timedelta(days=1) else 500.0, mins)
        return pd.DataFrame(rows, columns=["date", "m", "open", "high", "low", "close", "volume"])
    return fake


def _decide(root, tmp_path, monkeypatch, day: dt.date, prev: dt.date):
    (root / "decisions.jsonl").unlink()
    plan = tmp_path / f"plan_{day}.json"
    plan.write_text(json.dumps({"prev_date": prev.isoformat(), "index_tokens": TOK, "overnight": {"BANKNIFTY": {"atr14_prev": 600.0}},
                                "contracts": {"NIFTY": {"lot": 75}, "BANKNIFTY": {"lot": 35}}}))
    monkeypatch.setattr(sp1paper, "_plan_path", lambda d: plan)
    return sp1paper._append(root / "decisions.jsonl", {
        "kind": "decision", "date": day.isoformat(), "index": "BANKNIFTY", "point": "D0", "tradable": True, "entry_bar": 1, "fill_next_bar": 2,
        "decided_at": f"{day}T09:15:09+05:30", "choice": {"action": 10, "exit": "NEXTOPEN", "dir": 1, "pred_net": 5.0},
        "contracts": {"option": dict(OPT)}})


def test_a_weekday_short_of_some_minutes_is_still_a_regular_session(tmp_path, monkeypatch):
    # C1: Wed 4 Nov has 340 bars from 09:15 to 15:29 (35 minutes missing at midday, a data gap): its open is the exit, not Thursday's
    root, _ = _world(tmp_path, monkeypatch, noted=False)
    gap = [m for m in range(ocstudy.NMIN) if not 100 <= m < 135]
    full = range(ocstudy.NMIN)
    monkeypatch.setattr(sp1paper, "_candles", lambda *a: _candles({dt.date(2026, 11, 2): full, W3: full, W4: gap, W5: full}, dt.date(2026, 11, 2))(*a))
    _decide(root, tmp_path, monkeypatch, W3, dt.date(2026, 11, 2))
    sp1paper.score(day=W5, log=lambda s: None)
    rows = sp1paper._rows(root / "outcomes.jsonl")
    assert len(rows) == 1 and rows[0]["exit_day"] == "2026-11-04" and "skipped_days" not in rows[0]
    assert rows[0]["legs"]["option"]["exit_rule"] == "next session 09:16 open"
    # the Muhurat hour (13:45-14:44 IST) reaches neither the open nor the close: still no regular session
    assert sp1paper._regular_sessions(pd.DataFrame(_bars(W4, 1.0, 0.0, 0.0, range(270, 330))).assign(index_name="NIFTY BANK"), "NIFTY BANK") == set()
    assert sp1paper._regular_sessions(pd.DataFrame(_bars(W4, 1.0, 0.0, 0.0, gap)).assign(index_name="NIFTY BANK"), "NIFTY BANK") == {W4}


def test_two_skipped_days_read_as_two(tmp_path, monkeypatch):
    # C5: Sun 8 Nov (the Muhurat hour) and Mon 9 Nov (made a short special session here) are skipped; the words say so of both
    root, _ = _world(tmp_path, monkeypatch, noted=True)
    short = range(270, 330)
    full = range(ocstudy.NMIN)
    monkeypatch.setattr(sp1paper, "_candles", lambda *a: _candles({dt.date(2026, 11, 5): full, D6: full, D8: short, D9: short, D10: full},
                                                                  dt.date(2026, 11, 5))(*a))
    sp1paper.score(day=dt.date(2026, 11, 16), log=lambda s: None)
    late = sp1paper._rows(root / "outcomes.jsonl")[-1]
    assert late["skipped_days"] == ["2026-11-08", "2026-11-09"] and late["exit_day"] == "2026-11-10"
    assert "(Tue 10 Nov; Sun 8 Nov and Mon 9 Nov are no regular sessions)" in late["legs"]["option"]["exit_rule"]
    assert late["late_why"].startswith("Its next open fell on Sun 8 Nov and Mon 9 Nov, which are no regular sessions, so it was first left")
    assert sp1paper._no_regular([D8]) == "Sun 8 Nov is no regular session"


def _ledgers(tmp_path, monkeypatch, outcomes):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    (tmp_path / "paper" / "sp1").mkdir(parents=True, exist_ok=True)
    (tmp_path / "paper" / "sp1" / "outcomes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in outcomes))
    (tmp_path / "paper" / "sp1" / "decisions.jsonl").write_text(json.dumps(
        {"kind": "decision", "date": "2026-11-06", "index": "BANKNIFTY", "contracts": {"option": dict(OPT)}}) + "\n")


NO_PRICE = {"kind": "outcome", "date": "2026-11-06", "index": "BANKNIFTY", "scored_at": "2026-11-09T17:30:00+05:30", "exit_day": "2026-11-09",
            "index_proxy": {"next_day": True}, "legs": {"option": {"tradingsymbol": OPT["tradingsymbol"],
                                                                   "note": "no Kite candles for the contract at the entry or exit minute"}}}
NOTED = {"kind": "outcome", "date": "2026-11-06", "index": "BANKNIFTY", "note": "the study's outcome is not defined for this day"}


def test_a_trade_scored_with_no_option_price_is_left_out_and_said_so(tmp_path, monkeypatch):
    # C1's tail: if a trade's later open falls after its option's expiry, it is scored with no option price; it was in no total and in no
    # left-out word
    _ledgers(tmp_path, monkeypatch, [NO_PRICE])
    monkeypatch.setattr(managed, "_today_ist", lambda: "2026-11-13", raising=False)
    ol = managed.options_line("2026-10-30")
    assert ol["trades"] == 0 and ol["result_inr"] == 0
    assert ol["left_out"] == [{"date": "2026-11-06", "index": "BANKNIFTY", "why": "no option price", "expiry": "2026-11-23", "never": False}]
    assert managed.options_words(50000.0, ol, "2026-10-30").endswith("; 1 trade left out.")
    monkeypatch.setattr(readmodel, "_today_ist", lambda: "2026-11-13", raising=False)
    s = readmodel.sp1("2026-11-06")
    assert s["left_out"][0]["why"] == "no option price" and "Not in these figures: 1 trade with no result yet (BANKNIFTY Fri 6 Nov)" in s["words"]


def test_after_its_option_expires_a_left_out_trade_is_never_promised_a_score(tmp_path, monkeypatch):
    # C4: the morning view said "left out until scored" and the read model "with no result yet" after the contract had expired
    _ledgers(tmp_path, monkeypatch, [NOTED])
    for mod in (managed, readmodel, morningview):
        monkeypatch.setattr(mod, "_today_ist", lambda: "2026-11-24", raising=False)                   # the day after the 23 Nov expiry
    ol = managed.options_line("2026-10-30")
    assert ol["left_out"] == [{"date": "2026-11-06", "index": "BANKNIFTY", "expiry": "2026-11-23", "never": True}]
    mb = {"options_value_inr": 50000, "options_inr": 50000, "options_result_inr": 0, "options_trades": 0, "options_left_out": ol["left_out"]}
    assert morningview._options_words(mb).endswith("; 1 options trade left out, never scored: its option expired)")
    s = readmodel.sp1("2026-11-06")
    assert "Not in these figures: 1 trade never scored, its option expired (BANKNIFTY Fri 6 Nov)" in s["words"] and "no result yet" not in s["words"]
    for mod in (managed, readmodel, morningview):
        monkeypatch.setattr(mod, "_today_ist", lambda: "2026-11-13", raising=False)                   # before the expiry: the words as they were
    ol = managed.options_line("2026-10-30")
    mb["options_left_out"] = ol["left_out"]
    assert morningview._options_words(mb).endswith("; 1 options trade left out until scored)")
    assert "Not in these figures: 1 trade with no result yet (BANKNIFTY Fri 6 Nov)" in readmodel.sp1("2026-11-06")["words"]


# ---- 12 Nov 2026, the second confirm check of repair 4 (pkg4_confirm2.md): C1's rest, D1, D2, D4 ----

def test_a_weekday_that_opens_at_0915_is_a_regular_session_however_it_ends():
    # C1: a day missing only its 09:15 bar, or only its last half hour, was still "no regular session"
    def frame(day, mins):
        return pd.DataFrame(_bars(day, 1.0, 0.0, 0.0, mins)).assign(index_name="NIFTY BANK")
    no_0915 = range(1, ocstudy.NMIN)
    no_last_half = range(0, ocstudy.NMIN - 30)
    outage = range(0, 145)                                                       # an exchange outage from 11:40
    muhurat = range(270, 330)
    for mins, regular in ((no_0915, True), (no_last_half, True), (outage, True), (muhurat, False), (range(2, ocstudy.NMIN), False)):
        assert (sp1paper._regular_sessions(frame(W4, mins), "NIFTY BANK") == {W4}) is regular, (mins, regular)


def test_a_trade_scored_with_no_option_price_is_tried_again_and_counted_once(tmp_path, monkeypatch):
    # D1: it was never tried again, while every sentence naming it promised a score
    root, _ = _world(tmp_path, monkeypatch, noted=False)
    full = range(ocstudy.NMIN)
    first = dt.date(2026, 11, 2)
    days = {first: full, W3: full, W4: full, W5: full}
    gap_on_w4 = _candles(days, first)

    def no_option_on_w4(k, token, interval, a, b):                                # Kite has no option candles for Wed 4 Nov yet
        df = gap_on_w4(k, token, interval, a, b)
        return df[df["date"] != W4] if token == OPT["token"] else df
    monkeypatch.setattr(sp1paper, "_candles", lambda *a: no_option_on_w4(*a))
    _decide(root, tmp_path, monkeypatch, W3, first)
    sp1paper.score(day=W4, log=lambda s: None)
    rows = sp1paper._rows(root / "outcomes.jsonl")
    assert len(rows) == 1 and "net_rs_realistic" not in rows[0]["legs"]["option"] and rows[0]["legs"]["option"].get("note")
    monkeypatch.setattr(readmodel, "_today_ist", lambda: "2026-11-05", raising=False)
    s = readmodel.sp1("2026-11-03")
    assert s["left_out"][0]["why"] == "no option price" and "with no result yet (BANKNIFTY Tue 3 Nov)" in s["words"]
    monkeypatch.setattr(sp1paper, "_candles", lambda *a: gap_on_w4(*a))           # the candles are there the next evening
    sp1paper.score(day=W5, log=lambda s: None)
    rows = sp1paper._rows(root / "outcomes.jsonl")
    assert len(rows) == 2 and rows[1]["scored_late"] is True and rows[1]["legs"]["option"]["net_rs_realistic"] > 0
    assert rows[1]["late_why"].startswith("Kite had no price for its option at the exit when it was first scored")
    book = json.loads((root / "book.json").read_text())["by_index"]["BANKNIFTY"]
    assert book["trades"] == 1 and book["scored_late"] == 1                           # counted once
    s = readmodel.sp1("2026-11-03")
    assert s["left_out"] == [] and "Not in these figures" not in s["words"]
    sp1paper.score(day=dt.date(2026, 11, 6), log=lambda s: None)                    # scored once: nothing more
    assert len(sp1paper._rows(root / "outcomes.jsonl")) == 2


def test_a_trade_whose_own_day_stays_short_is_noted_once_and_named(tmp_path, monkeypatch):
    # D2: a trade whose own day was short of minutes was tried every evening for ever and named by no total
    root, _ = _world(tmp_path, monkeypatch, noted=False)
    full, short = range(ocstudy.NMIN), [m for m in range(ocstudy.NMIN) if not 100 <= m < 135]
    first = dt.date(2026, 11, 2)
    monkeypatch.setattr(sp1paper, "_candles", lambda *a: _candles({first: full, W3: short, W4: full, W5: full}, first)(*a))
    _decide(root, tmp_path, monkeypatch, W3, first)
    sp1paper.score(day=W5, log=lambda s: None)                                       # two days on: still waiting, nothing written
    assert sp1paper._rows(root / "outcomes.jsonl") == []
    sp1paper.score(day=dt.date(2026, 11, 6), log=lambda s: None)                    # three days on: noted once
    sp1paper.score(day=dt.date(2026, 11, 9), log=lambda s: None)
    rows = sp1paper._rows(root / "outcomes.jsonl")
    assert len(rows) == 1 and rows[0]["note"].startswith("the day's minute bars are not complete on Kite")
    monkeypatch.setattr(readmodel, "_today_ist", lambda: "2026-11-09", raising=False)
    assert readmodel.sp1("2026-11-03")["left_out"][0]["date"] == "2026-11-03"


def test_two_trades_whose_options_expired_read_as_two():
    # D4: "its option expired" was said of two trades
    mb = {"options_value_inr": 50000, "options_inr": 50000, "options_result_inr": 0, "options_trades": 0,
          "options_left_out": [{"date": "2026-11-06", "index": "BANKNIFTY", "expiry": "2026-11-23"},
                               {"date": "2026-11-10", "index": "NIFTY", "expiry": "2026-11-17"}]}
    import unittest.mock as um
    with um.patch.object(morningview, "_today_ist", lambda: "2026-11-24"):
        assert morningview._options_words(mb).endswith("; 2 options trades left out, never scored: their options expired)")
