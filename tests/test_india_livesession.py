"""Never again (Madhav, 2 Nov 2026: "these are huge mistakes, I want you to take care and make sure these things don't repeat again").

On Monday 2 Nov at 16:38 IST (06:08 Toronto) the India Ask said "Monday's session is happening" an hour after the close, said it had "no
record" of the options line's decisions although they were in its ledger from 09:15-09:45 IST, said it could not see the live market although
the read-only Kite connection reads it, and answered "yesterday" with Friday. These tests pin the clock, today's block and the answer guard to
those exact moments and those exact sentences."""
import datetime as dt
import json

import pytest

from jarvis.india import livesession as L

UTC = dt.timezone.utc
AT_0608_TORONTO = dt.datetime(2026, 11, 2, 11, 8, tzinfo=UTC)      # Monday 16:38 IST, 68 minutes after the close
AT_2218_SUNDAY = dt.datetime(2026, 11, 2, 3, 18, tzinfo=UTC)       # Monday 08:48 IST, before the open
AT_MIDSESSION = dt.datetime(2026, 11, 2, 6, 0, tzinfo=UTC)         # Monday 11:30 IST


def _quote_stub(syms):
    table = {"NSE:NIFTY 50": (23440.8, 23222.3, 23053.1), "NSE:NIFTY BANK": (55002.2, 54837.2, 54686.95), "NSE:INDIA VIX": (15.5, 15.3, 15.3),
             "NFO:BANKNIFTY26NOV55000CE": (811.05, 0, 0), "NFO:NIFTY26N0323300CE": (96.95, 0, 0), "NSE:TCS": (3100.0, 3000.0, 3000.0)}
    return {s: {"last_price": table[s][0], "ohlc": {"open": table[s][1], "high": table[s][0], "low": table[s][1], "close": table[s][2]}} for s in syms if s in table}


@pytest.fixture(autouse=True)
def _clean_cache():
    L._CACHE.clear()
    yield
    L._CACHE.clear()


@pytest.fixture
def ledger(tmp_path):
    rows = [{"kind": "plan", "date": "2026-11-02", "made_at": "2026-11-02T08:31:23+05:30"},
            {"kind": "decision", "date": "2026-11-02", "index": "NIFTY", "point": "D0", "decided_at": "2026-11-02T09:15:33+05:30", "choice": None},
            {"kind": "decision", "date": "2026-11-02", "index": "BANKNIFTY", "point": "D1", "decided_at": "2026-11-02T09:30:43+05:30", "entry_estimate": 54953.0,
             "choice": {"dir": 1, "exit": "NEXTOPEN"}, "contracts": {"option": {"strike": 55000.0, "type": "CE", "tradingsymbol": "BANKNIFTY26NOV55000CE", "lot": 30}},
             "quotes_at_decision": {"NFO:BANKNIFTY26NOV55000CE": 882.85}},
            {"kind": "decision", "date": "2026-11-02", "index": "NIFTY", "point": "D2", "decided_at": "2026-11-02T09:45:44+05:30", "entry_estimate": 23304.2,
             "choice": {"dir": 1, "exit": "NEXTOPEN"}, "contracts": {"option": {"strike": 23300.0, "type": "CE", "tradingsymbol": "NIFTY26N0323300CE", "lot": 65}},
             "quotes_at_decision": {"NFO:NIFTY26N0323300CE": 110.55}}]
    p = tmp_path / "decisions.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return p


def _live(now, ledger_path, monkeypatch):
    clk = L.clock("2026-10-30", now)
    return {"clock": clk, "index_now": L.index_now(clk, _quote_stub), "options_today": L.options_today(clk, _quote_stub, path=ledger_path)}


# ---- the clock -------------------------------------------------------------------------------------------------------------------------------

def test_after_the_close_is_closed_today_and_says_how_long_ago():
    c = L.clock("2026-10-30", AT_0608_TORONTO)
    assert c["state"] == "closed" and c["latest_session"] == "2026-11-02" and not c["latest_session_in_nightly_data"]
    assert "CLOSED" in c["words"] and "1 h 8 min ago" in c["words"] and "6:08 am in Toronto" in c["words"]
    assert "Monday 2 Nov, today in India (finished)" in c["relative_days"]


def test_sunday_night_toronto_is_monday_before_the_open():
    c = L.clock("2026-10-30", AT_2218_SUNDAY)
    assert c["state"] == "before_open" and c["latest_session"] == "2026-10-30" and c["next_session"] == "2026-11-02"
    assert "has not started yet" in c["relative_days"] and "Sunday 1 Nov, 10:18 pm" in c["words"]


def test_midsession_and_pre_open_and_weekend():
    assert L.clock("2026-10-30", AT_MIDSESSION)["state"] == "open"
    assert L.clock("2026-10-30", dt.datetime(2026, 11, 2, 3, 35, tzinfo=UTC))["state"] == "pre_open"      # 09:05 IST
    assert L.clock("2026-10-30", dt.datetime(2026, 11, 1, 6, 0, tzinfo=UTC))["state"] == "no_session"     # Sunday


# ---- today's block ---------------------------------------------------------------------------------------------------------------------------

def test_options_today_reads_the_ledger_with_the_option_price_now(ledger):
    clk = L.clock("2026-10-30", AT_0608_TORONTO)
    o = L.options_today(clk, _quote_stub, path=ledger)
    assert o["decisions"] == 3 and len(o["taken"]) == 2
    assert "Bank Nifty long at 09:30 IST" in o["words"] and "Nifty long at 09:45 IST" in o["words"] and "passed on Nifty at 09:15" in o["words"]
    assert o["taken"][0]["paper_move_inr_per_lot"] == round((811.05 - 882.85) * 30)


def test_no_decision_yet_is_said_plainly(tmp_path):
    p = tmp_path / "d.jsonl"
    p.write_text(json.dumps({"kind": "plan", "date": "2026-11-02", "made_at": "2026-11-02T08:31:23+05:30"}) + "\n")
    o = L.options_today(L.clock("2026-10-30", AT_MIDSESSION), _quote_stub, path=p)
    assert o["decisions"] == [] and "no decision is in its ledger yet" in o["words"]


def test_index_now_has_todays_close_after_the_close_and_says_a_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "DATA", tmp_path)            # no closing bars on file: the failure is said plainly
    clk = L.clock("2026-10-30", AT_0608_TORONTO)
    i = L.index_now(clk, _quote_stub)
    assert "Nifty 23,440.80, say 23,441 (+1.68%" in i["words"] and "today's close" in i["words"]
    L._CACHE.clear()
    bad = L.index_now(clk, lambda syms: (_ for _ in ()).throw(RuntimeError("Kite down")))
    assert not bad.get("rows") and "could not reach the live prices" in bad["words"]


def test_holdings_today_moves_the_paper_copy():
    clk = L.clock("2026-10-30", AT_0608_TORONTO)
    h = L.holdings_today(clk, [{"symbol": "TCS", "qty": 10}], _quote_stub)
    assert h["move_inr"] == 1000 and "up about Rs 1,000" in h["words"]


# ---- the guard: the exact sentences of 2 Nov ---------------------------------------------------------------------------------------------

BAD_2NOV = [
    ("So, what happened on the Monday market?", "Sir, I can't tell you how Monday's market went: my data runs only through Friday 30 Oct, and I have no Monday prices yet, which is why I kept giving you Friday."),
    ("Why didn't you have that data?", "Yes, sir, Monday's session is happening in India, but I work from daily closing data, nothing intraday."),
    ("What about the Monday?", "The morning plan was 11 practice buys at the open, but I have no record of what either did, so I won't guess."),
    ("opening update", "Sir, the options line is signed in and its plan is written, but I have no record of what it decided this morning, so I won't guess at the opening."),
    ("We should know about the current session.", "Right now I work only from daily closing data, with nothing intraday, so during the session I can't see where the Nifty is trading."),
    ("What happened with the market yesterday?", "Sir, on Friday 30 Oct the Nifty closed at 23,053, up 0.5%, but it is still in a downtrend."),
]


@pytest.mark.parametrize("q,a", BAD_2NOV)
def test_every_wrong_sentence_of_2_nov_is_caught(q, a, ledger, monkeypatch):
    live = _live(AT_0608_TORONTO, ledger, monkeypatch)
    assert L.check(a, live, q), a


def test_a_right_answer_passes(ledger, monkeypatch):
    live = _live(AT_0608_TORONTO, ledger, monkeypatch)
    good = ("Sir, today, Monday 2 Nov, the Nifty closed at 23,440.80, up 1.68%; the session closed at 15:30 IST, an hour ago. The options line went "
            "long Bank Nifty at 09:30 and Nifty at 09:45, both closing at tomorrow's open. Friday's full data is what the research book still uses.")
    assert L.check(good, live, "What happened with the market today?") == []


def test_before_the_open_an_answer_about_friday_is_right(ledger, monkeypatch):
    live = _live(AT_2218_SUNDAY, ledger, monkeypatch)
    assert L.check("Sir, the Nifty closed at 23,053 on Friday 30 Oct; today's session opens at 09:15 IST.", live, "What's up with the market now?") == []
    assert L.check("Sir, the market is open and trading higher.", live, "What's up with the market now?")


def test_scrub_drops_the_wrong_sentences_and_leads_with_today(ledger, monkeypatch):
    live = _live(AT_0608_TORONTO, ledger, monkeypatch)
    out = L.scrub("Yes, sir, Monday's session is happening in India. The levels were 23,122 and 22,984.", live)
    assert "happening" not in out and "CLOSED" in out and "23,122" in out and "Nifty 23,440.80" not in out     # only the fact that was wrong
    out = L.scrub("Sir, I can't see where the Nifty is trading. The levels were 23,122 and 22,984.", live)
    assert "Nifty 23,440.80" in out and "can't see" not in out


def test_indicator_answers_on_daily_data_are_not_price_claims(ledger, monkeypatch):
    """2 Nov round: the indicator panel's honest "Ananta's own daily data, nothing intraday" was taken for "can't see today's prices"."""
    live = _live(AT_0608_TORONTO, ledger, monkeypatch)
    a = "Sir, as of the Fri 30 Oct close (Ananta's own daily data, nothing intraday): the Nifty's RSI is 48. Studies use daily closing data only."
    assert L.check(a, live, "What is the Nifty's RSI?") == []
    assert L.scrub(a, live) == a


def test_tomorrow_is_not_an_older_session(ledger, monkeypatch):
    live = _live(AT_0608_TORONTO, ledger, monkeypatch)
    a = "Yes, sir, the Bank Nifty trade is down on paper, about Rs -2,154. Both close at tomorrow's (Tue 3 Nov) open, Tuesday."
    assert L.check(a, live, "the options trades you took this morning, is it in loss now?") == []


def test_toronto_afternoon_after_india_midnight_still_means_mondays_session(ledger):
    """2 Nov round, 13:30 Toronto = 00:00 IST Tuesday: 'today' is still Monday for Madhav, and Monday's close, high and low stay readable."""
    at = dt.datetime(2026, 11, 2, 18, 33, tzinfo=UTC)
    c = L.clock("2026-10-30", at)
    assert c["state"] == "before_open" and c["latest_session"] == "2026-11-02" and c["today_india"] == "2026-11-03"
    assert "still mean Monday 2 Nov's session" in c["relative_days"] and "'tomorrow' means Tuesday 3 Nov" in c["relative_days"]
    i = L.index_now(c, _quote_stub)
    assert "at the close of Monday 2 Nov" in i["words"] and i["rows"]["NIFTY 50"]["high"] == 23440.8
    assert L.options_today(c, _quote_stub, path=ledger)["taken"]



def test_friday_as_the_base_of_a_live_number_is_about_today(ledger, monkeypatch):
    """Moment harness, 2 Nov 11:30 IST: '+1.2% on Friday's close, as of 11:30 IST' answers about today; Friday is only the base."""
    live = _live(AT_0608_TORONTO, ledger, monkeypatch)
    a = "Sir, at 11:30 IST the Nifty is at 23,331, up 1.2% on Friday's close."
    assert L.check(a, live, "How is the market doing right now?") == []
    wrong = "Sir, the Nifty closed at 23,053 on Friday, down 0.4%."
    assert L.check(wrong, live, "How is the market doing right now?")


def test_where_is_the_nifty_is_answered_not_navigated():
    """Moment harness, 2 Nov: 'how is the market right now, like where is the Nifty?' got 'Taking you to Markets'."""
    from jarvis.india import appmap
    assert appmap.quick_command("Ananta how is the market right now, like where is the Nifty?") is None
    assert appmap.quick_command("Where is the Nifty?") is None
    assert appmap.quick_command("where are my options?")          # a plain "where is X" for a screen still navigates
    assert appmap.quick_command("take me to markets")


def test_options_today_says_in_code_whether_each_index_is_for_or_against_the_trade(ledger):
    """Moment harness, 2 Nov: the model said 'both indexes are up since entry' while Bank Nifty was below its entry."""
    c = L.clock("2026-10-30", AT_0608_TORONTO)
    o = L.options_today(c, _quote_stub, path=ledger)
    bn = next(x for x in o["taken"] if x["index"] == "BANKNIFTY")
    nf = next(x for x in o["taken"] if x["index"] == "NIFTY")
    assert bn["index_since_entry_pts"] == 49 and "above where it was taken" in bn["index_since_entry_words"] and "for the trade" in bn["index_since_entry_words"]
    assert nf["index_since_entry_pts"] == 137 and "in loss" in o["words"]


def test_practice_today_prices_the_open_trades_and_the_picks_bought_at_the_open(tmp_path):
    """Independent audit, 2 Nov: after the close Ananta could not say how the practice book did today (booked only at 08:00 IST next morning)."""
    (tmp_path / "decisions").mkdir()
    st = {"trades": {"a": {"book": "exec", "policy": "hold_20d", "status": "open", "campaign": "BRK", "symbol": "TCS", "entry_adj": 2900.0,
                           "last_close_adj": 3000.0, "last_date": "2026-10-30", "notional": 50000.0},
                     "c": {"book": "exec", "policy": "hold_20d", "status": "open", "campaign": "CTL", "symbol": "TCS", "entry_adj": 2900.0,
                           "last_close_adj": 3000.0, "last_date": "2026-10-30", "notional": 50000.0}},
          "decisions": {"2026-10-30": {"status": "pending"}}}
    (tmp_path / "state.json").write_text(json.dumps(st))
    (tmp_path / "decisions" / "2026-10-30.json").write_text(json.dumps({"signals": [{"symbol": "TCS", "campaign": "PULL"}, {"symbol": "TCS", "campaign": "CTL"}]}))
    c = L.clock("2026-10-30", AT_0608_TORONTO)
    p = L.practice_today(c, _quote_stub, path=tmp_path / "state.json")
    assert p["held"] == 1 and p["held_move_inr"] == round(50000 * 3000 / 2900 * (3100 / 3000 - 1))     # the control (CTL) is left out
    assert len(p["picks_filled"]) == 1 and p["picks_move_inr"] == round(50000 * (3100 / 3000 - 1))
    assert "practice book" in p["words"] and "today" in p["words"]


def test_holdings_today_reads_the_frozen_holdings_and_names_the_book(tmp_path, monkeypatch):
    (tmp_path / "paper" / "account").mkdir(parents=True)
    (tmp_path / "paper" / "account" / "frozen.json").write_text(json.dumps({"positions": {"TCS": {"qty": 10, "avg": 2000.0}}}))
    monkeypatch.setattr(L, "DATA", tmp_path)
    pos = L._frozen_positions()
    assert pos == [{"symbol": "TCS", "qty": 10}]
    h = L.holdings_today(L.clock("2026-10-30", AT_0608_TORONTO), pos, _quote_stub)
    assert "As you have it" in h["words"] and "not the twin" in h["words"]


def test_guard_also_checks_today_after_india_midnight(ledger):
    """Independent audit, 2 Nov: from IST midnight to the open (Madhav's evening) the older-session check was off."""
    at = dt.datetime(2026, 11, 2, 22, 30, tzinfo=UTC)          # Monday 17:30 Toronto = Tuesday 04:00 IST
    c = L.clock("2026-10-30", at)
    live = {"clock": c, "index_now": L.index_now(c, _quote_stub), "options_today": L.options_today(c, _quote_stub, path=ledger)}
    assert c["state"] == "before_open" and c["latest_session"] == "2026-11-02"
    assert L.check("Sir, the Nifty closed at 23,053 on Friday, up 0.5%.", live, "How did the market do today?")
    assert L.check("Sir, Monday's session closed with the Nifty at 23,441, up 1.7% on Friday.", live, "How did the market do today?") == []


def test_holidays_ahead_reads_the_nse_list(tmp_path, monkeypatch):
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "nse_holidays.json").write_text(json.dumps({"CM": [
        {"tradingDate": "08-Nov-2026", "description": "Diwali Laxmi Pujan*"}, {"tradingDate": "10-Nov-2026", "description": "Diwali-Balipratipada"}]}))
    monkeypatch.setattr(L, "DATA", tmp_path)
    h = L.holidays_ahead(L.clock("2026-10-30", AT_0608_TORONTO))
    assert len(h["rows"]) == 2 and "Muhurat" in h["words"] and "Tuesday 10 Nov: Diwali-Balipratipada" in h["words"]


def test_index_now_falls_back_to_the_closing_bars_when_zerodha_is_signed_out(tmp_path, monkeypatch):
    """Independent audit, 2 Nov: from 06:00 IST (sign-in lapses) to 07:10 IST (automatic sign-in) live prices fail every evening in Toronto."""
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "technicals.json").write_text(json.dumps({"indices": {"NIFTY 50": {"close": 23440.8, "prev_close": 23053.1, "as_of": "2026-11-02"}}}))
    monkeypatch.setattr(L, "DATA", tmp_path)
    c = L.clock("2026-10-30", dt.datetime(2026, 11, 3, 0, 40, tzinfo=UTC))      # Mon 19:40 Toronto = Tue 06:10 IST
    i = L.index_now(c, lambda syms: (_ for _ in ()).throw(RuntimeError("TokenException")))
    assert i["rows"]["NIFTY 50"]["last"] == 23440.8 and "closing bars" in i["words"] and "Monday 2 Nov" in i["words"]
