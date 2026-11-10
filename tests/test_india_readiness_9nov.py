"""9 Nov 2026 (the outsider readiness review; Madhav: "yes, lets complete", and at 18:25 Toronto "how to make sure the agent adjusts itself
according to the given situation without sticking to old decisions"): the open seen before it happens, the options line's plan said, holdings
first, and a second look at the morning view when the facts it was written with have moved."""
import datetime as dt
import json
import sys

from jarvis.india import livesession, preopen, readiness, recheck

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
VIEW = {"session": "2026-11-11", "setup": {"scenario_levels": {"up_above": 25120.0, "down_below": 24970.0}},
        "premarket": {"gift": {"taken_at": "2026-11-11T08:29:00+05:30", "change_pct": 0.4}}}


def _pre(n, b, moved=True, day="2026-11-11"):
    return {"day": day, "taken_at": f"{day}T09:09:03+05:30", "index_moved": moved,
            "indexes": {"NIFTY 50": {"last": round(25045 * (1 + n / 100)), "prev_close": 25045, "chg_pct": n}, "NIFTY BANK": {"last": 59741, "prev_close": 59741, "chg_pct": b}}}


# ---------------------------------------------------------------------------------------------------------------- the second look
def test_the_view_stands_when_the_pre_open_agrees_with_what_it_was_written_with():
    r = recheck.at_preopen(VIEW, _pre(0.5, 0.6))
    assert r["changed"] is False and "the view stands" in r["words"]


def test_the_second_look_says_so_when_the_open_comes_in_the_other_way():
    r = recheck.at_preopen(VIEW, _pre(-0.6, -0.9))
    assert r["changed"] is True and "weaker than the view was written with" in r["words"]
    assert "already below the line that makes it a down day (24,970)" in r["words"]


def test_a_view_with_no_overnight_read_says_what_is_new():
    v = {**VIEW, "premarket": {}}
    assert recheck.at_preopen(v, _pre(0.7, 0.4))["changed"] is True
    flat = recheck.at_preopen(v, _pre(0.1, 0.0))
    assert flat["changed"] is False and "a flat open, as the view assumed" in flat["words"]
    assert recheck.at_preopen(VIEW, _pre(0.0, 0.0, moved=False))["words"] is None            # no index reading: nothing is claimed


def test_a_big_gap_and_the_options_lines_row_are_said():
    plan = {"row": {"BANKNIFTY": {"words": "Bank Nifty is indicated +1.3% (up): for that open the plan says a short (a put option, one lot), closing at 15:15 IST."}}}
    r = recheck.at_preopen(VIEW, _pre(1.2, 1.3), plan)
    assert r["changed"] and "A gap of 1% or more" in r["words"] and "Options line: Bank Nifty is indicated +1.3%" in r["words"]


def test_the_options_lines_read_of_the_open_is_checked_against_the_pre_open():
    """6 Nov 2026: the line read Bank Nifty's open as 57,545.7 (-0.39%, its 'down' row); the pre-open's matched open was 57,812.9 (+0.07%, 'flat')."""
    pre = {"indexes": {"NIFTY BANK": {"last": 57812.9, "chg_pct": 0.07}, "NIFTY 50": {"last": 24538.2, "chg_pct": 0.01}}}
    d0 = [{"index": "BANKNIFTY", "state": {"gap": -0.003945570342188898, "open": 57545.7}}, {"index": "NIFTY", "state": {"gap": -0.00075, "open": 24518.2}}]
    cc = recheck.crosscheck(d0, pre)
    bank, nifty = cc[0], cc[1]
    assert bank["line_row"] == "down" and bank["preopen_row"] == "flat" and not bank["same_row"] and "a different row of its plan" in bank["words"]
    assert nifty["same_row"] and "the same row" in nifty["words"]
    look = recheck.at_opening(None, pre, {"NIFTY 50": {"change_pct": 0.6}, "NIFTY BANK": {"change_pct": 0.5}}, d0)
    assert look["changed"] and any("Its decision stands as taken" in p for p in look["points"])       # read-only: nothing about the line changes


def test_the_first_hour_is_read_against_the_pre_open():
    pre = _pre(0.8, 0.9)
    assert "has reversed" in recheck.at_opening(None, pre, {"NIFTY 50": {"change_pct": -0.4}}, [])["words"]
    assert "given back more than half" in recheck.at_opening(None, pre, {"NIFTY 50": {"change_pct": 0.2}}, [])["words"]
    held = recheck.at_opening(None, pre, {"NIFTY 50": {"change_pct": 1.1}}, [])
    assert "held or extended" in held["words"] and held["changed"] is False


# ---------------------------------------------------------------------------------------------------------------- the pre-open read
def _fetch(rows):
    return lambda syms: {s: {"last_price": rows.get(s, (100, 100))[0], "ohlc": {"close": rows.get(s, (100, 100))[1]}} for s in syms}


def test_ten_stocks_all_at_their_previous_close_is_not_a_reading():
    """9 Nov 2026: every one of the ten came back equal to its previous close while the index had moved 0.4%; it was said as '0 of 10 higher, 0 lower'."""
    livesession._CACHE.clear()
    d = preopen.read(_fetch({"NSE:NIFTY 50": (25076.85, 24986.4), "NSE:NIFTY BANK": (59235.45, 58850.65)}), dt.datetime(2026, 11, 9, 9, 9, tzinfo=IST))
    assert d["index_moved"] and d["heavy"]["n"] == 0 and "no matched price came through" in d["heavy"]["note"]
    w = preopen.words(d)
    assert "Nifty indicated near 25,077 (+0.4%" in w and "heavy stocks" not in w


def test_the_phone_note_says_the_open_the_view_and_the_options_line():
    d = {**_pre(0.4, 0.7), "recheck": {"changed": False}, "options_plan": {"row": {"NIFTY": {"choice": "no trade"}, "BANKNIFTY": {"choice": "a short (a put option, one lot), closing at 15:15 IST"}}}}
    n = preopen.push_words(d)
    assert n.startswith("Indicated open at 09:09 IST: Nifty +0.4%, Bank Nifty +0.7%.") and "In line with the 08:30 view." in n
    assert "Options line for that open: Nifty no trade, Bank Nifty a short (put)." in n
    assert "This changes the 08:30 view." in preopen.push_words({**d, "recheck": {"changed": True}})
    assert preopen.push_words({**d, "index_moved": False}) is None


def test_the_second_look_is_added_to_the_read(monkeypatch):
    monkeypatch.setattr(livesession, "options_plan", lambda clk, indicated=None: {"row": {"NIFTY": {"words": "Nifty is indicated -0.6% (down): for that open the plan says no trade.", "choice": "no trade"}},
                                                                                  "short": "x", "missing": [], "made_at": "t"})
    d = preopen.second_look(_pre(-0.6, -0.9), clk={"state": "pre_open"}, view=VIEW)
    assert d["recheck"]["changed"] and d["options_plan"]["row"]["NIFTY"]["choice"] == "no trade"
    assert "Against the 08:30 morning view" in preopen.words(d)


# ---------------------------------------------------------------------------------------------------------------- the four code answers
CLK = {"state": "before_open", "today_india": "2026-11-11", "latest_session": "2026-11-09", "latest_session_words": "Monday 9 Nov", "next_session_words": "Wednesday 11 Nov"}


def test_the_four_questions_are_recognised_and_nothing_else():
    yes = ["How will the market open?", "how will it open tomorrow", "what does the pre-open say", "What will the options line do at the open?", "what's the plan for the open",
           "Did any of my stocks file anything?", "any news on my holdings", "Has anything changed since the morning view?", "is the view still valid"]
    no = ["How are my holdings doing?", "what is the plan for today", "open the money screen", "how did the options line do yesterday", "what is the view for today"]
    for q in yes:
        assert readiness.answer(q, {"clock": CLK}) is not None, q
    for q in no:
        assert readiness.answer(q, {"clock": CLK}) is None, q


def test_how_it_opens_uses_the_pre_open_then_gift_nifty_then_says_it_cannot_see():
    g = {"words": "GIFT Nifty, the Nifty future that trades overnight, is up 0.4% from where it stood at the last NSE close."}
    plan = {"row": {"NIFTY": {"words": "Nifty is indicated +0.4% (up): for that open the plan says no trade."}}}
    a = readiness.how_it_opens({"clock": CLK, "gift": g, "options_plan": plan})
    assert "GIFT Nifty" in a and "Options line: Nifty is indicated +0.4%" in a and "go to your phone" in a
    b = readiness.how_it_opens({"clock": CLK, "gift": g, "preopen": {"words": "Pre-open read at 09:09 IST, before the 09:15 open: Nifty indicated near 25,077."}})
    assert b.startswith("Sir, pre-open read at 09:09 IST") and "GIFT" not in b
    c = readiness.how_it_opens({"clock": CLK, "gift": {"error": "NeedLogin"}})
    assert "cannot see the open yet" in c and "(NeedLogin)" in c
    assert "the market is open" in readiness.how_it_opens({"clock": {**CLK, "state": "open"}, "index_now": {"words": "Nifty 25,100."}})


def test_the_plan_answer_never_guesses_before_the_plan_is_written():
    a = readiness.options_plan({"clock": CLK, "options_today": {"words": "No options decisions in the ledger for Monday 9 Nov."}})
    assert "not written yet" in a and "down, flat or up" in a and "On Monday 9 Nov it has no decision in its ledger." in a
    # found on the first live ask (10 Nov): on a holiday it said "the decision points for this session have passed" and read out the block
    # written for the model ("say it as a closed trade ..."). The last session is now one short sentence from the ledger rows.
    ot = {"decisions": 5, "words": "... say it as a closed trade with this result, never today's option price ...",
          "taken": [{"index": "BANKNIFTY", "direction": "short", "at": "09:15", "result": {"net_inr": -6054}}]}
    h = readiness.options_plan({"clock": {**CLK, "state": "no_session"}, "options_today": ot})
    assert "the plan for Wednesday 11 Nov is not written yet" in h and "On Monday 9 Nov it took Bank Nifty short at 09:15 IST, closed about −₹6,054 on paper." in h
    assert "say it as" not in h and "have passed" not in h
    live_day = {"clock": {**CLK, "state": "closed", "today_india": "2026-11-09"}, "options_today": ot}
    assert "decision points for today have passed" in readiness.options_plan(live_day)
    b = readiness.options_plan({"clock": CLK, "options_plan": {"words": "The options line's plan for the 09:15 open: Nifty: no trade.", "row": {}}})
    assert b.startswith("Sir, the options line's plan for the 09:15 open")


def test_what_changed_reads_the_days_second_looks(monkeypatch, tmp_path):
    monkeypatch.setattr(preopen, "OUT", tmp_path)
    assert "nothing has been checked against this morning's view yet" in readiness.what_changed({"clock": CLK})
    (tmp_path / "2026-11-11.json").write_text(json.dumps({"recheck": {"changed": True, "words": "At 08:30 GIFT Nifty pointed to +0.4%; the pre-open now indicates Nifty -0.6%."}}))
    a = readiness.what_changed({"clock": CLK})
    assert a.startswith("Yes, sir.") and "09:09 second look" in a and "a change to a rule waits for your yes" in a
    assert "no second look on file for Monday 9 Nov" in readiness.what_changed({"clock": {**CLK, "state": "no_session"}})


# ---------------------------------------------------------------------------------------------------------------- one price, one calendar, one set of words
def test_one_option_trade_is_said_with_one_entry_price(tmp_path):
    led = tmp_path / "decisions.jsonl"
    led.write_text(json.dumps({"kind": "decision", "date": "2026-11-09", "index": "BANKNIFTY", "point": "D0", "decided_at": "2026-11-09T09:15:32+05:30", "entry_estimate": 59117.2,
                               "choice": {"dir": -1, "exit": "ATRSTOP"}, "contracts": {"option": {"tradingsymbol": "BANKNIFTY26NOV59100PE", "strike": 59100.0, "type": "PE", "lot": 30, "expiry": "2026-11-24"}},
                               "quotes_at_decision": {"NFO:BANKNIFTY26NOV59100PE": 752.8}}) + "\n")
    clk = {"latest_session": "2026-11-09", "latest_session_words": "Monday 9 Nov", "today_india": "2026-11-09", "state": "open", "ts": 0}
    w = livesession.options_today(clk, fetch=lambda syms: {}, path=led)["words"]
    assert "quoted near Rs 752.8 when it decided" in w and "its paper fill is the next minute's price" in w and "at about Rs" not in w


def test_the_exit_words_have_one_wording():
    if str(livesession.RECORDS) not in sys.path:
        sys.path.append(str(livesession.RECORDS))
    import importlib
    assert importlib.import_module("india.sp1plan").EXIT_WORDS == livesession.EXIT_WORDS


def test_the_voice_reads_the_one_calendar(monkeypatch, tmp_path):
    from jarvis.india import desk, views
    assert not hasattr(desk, "EVENTS")                      # the hand-kept list is gone: one owner (records india/registrations/calendar_ahead.json)
    (tmp_path / "manifests").mkdir()
    far = (dt.date.today() + dt.timedelta(days=20)).isoformat()
    (tmp_path / "manifests" / "calendar.json").write_text(json.dumps({"events": [
        {"date": "2020-01-01", "what": "old"}, {"date": far, "what": "RBI monetary policy decision", "time_ist": "10:00", "first_session_words": "Friday 4 Dec",
                                                "options_line_event_day": True, "words": "RBI monetary policy decision: ...", "source": "RBI press release"}]}))
    monkeypatch.setattr(views, "DATA", tmp_path)
    ev = desk.calendar_events()
    assert [e["what"] for e in ev] == ["RBI monetary policy decision"] and ev[0]["options_line_event_day"] is True and ev[0]["source"]


def test_the_changed_question_is_not_taken_for_a_request_to_hear_the_view():
    """Found on the first live ask: 'has anything changed since the morning view?' was answered by the flow that reads the view out."""
    from jarvis.india import ask
    assert readiness.CHANGED_Q.search("Ananta, has anything changed since the morning view?") and ask.MORNING.search("has anything changed since the morning view?")
    src = open(ask.__file__).read()
    assert src.index("readiness_flow(t) or morning_flow(t, who)") > 0          # the order in the chain: the question first, then the reading


def test_a_company_known_by_its_initials_keeps_them_in_capitals(monkeypatch, tmp_path):
    from jarvis.india import askwords
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "quotebook_names.json").write_text(json.dumps({
        "IRFC": {"name": "Indian Railway Finance Corporation Limited", "kind": "stock", "aliases": ["irfc"], "norm": "indian railway finance"},
        "TATAPOWER": {"name": "Tata Power Company Limited", "kind": "stock", "aliases": ["tata power"], "norm": "tata power company"}}))
    monkeypatch.setenv("ANANTA_INDIA_DATA", str(tmp_path))
    monkeypatch.setattr(askwords, "_NAMES", {"t": 0.0, "v": {}})
    n = askwords.company_names()
    assert n["IRFC"] == "IRFC" and n["TATAPOWER"] == "Tata Power"


def test_a_trade_with_no_result_is_shown_beside_the_options_lines_record(tmp_path, monkeypatch):
    """Madhav, 9 Nov 19:51 Toronto ("Yes to all your recommendations", 2): the 6 Nov Bank Nifty trade stays unscored and shown as such."""
    from jarvis.india import surfaces
    monkeypatch.setattr(surfaces, "DATA", tmp_path)
    (tmp_path / "paper" / "sp1").mkdir(parents=True)
    (tmp_path / "paper" / "sp1" / "book.json").write_text(json.dumps({"updated": "2026-11-09T17:30:07+05:30", "sessions": 11, "by_index": {"BANKNIFTY": {"trades": 10, "option_1lot_rs_realistic_fill": -5252.0}}}))
    (tmp_path / "paper" / "sp1" / "outcomes.jsonl").write_text("\n".join(json.dumps(x) for x in [
        {"kind": "outcome", "date": "2026-11-05", "index": "BANKNIFTY", "point": "D0", "index_proxy": {"net_bps": -1.0}},
        {"kind": "outcome", "date": "2026-11-06", "index": "BANKNIFTY", "point": "D0", "note": "the study's outcome is not defined for this day"}]) + "\n")
    cl = [{"name": "the options line", "done": 10, "so_far": "x"}]
    surfaces._sp1_clock(cl)
    assert "Not in these figures: 1 trade with no result (Fri 6 Nov, Bank Nifty)" in cl[0]["so_far"] and "stays unscored and is shown here" in cl[0]["so_far"]
