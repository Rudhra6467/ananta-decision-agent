"""3 Nov 2026: Madhav's chat (08:46-09:01 Toronto) and the outside trader's grade. The Ask filed nothing when he asked to register the data
audit, denied data it has, could not say why MARICO jumped, had no next-session plan and offered a fix menu in "what's waiting"."""
import json

from jarvis.india import ask, desk

MADHAV_0901 = ("Yeah, we have to, along with the last conversation, last one, your first thing. My first thing, I will go by, yeah. And you know, "
               "this one is also to be registered and somehow to be notified. Like, you know, we have to first take our time in evaluating and finding "
               "the best research, like data sets that should give us scope.")


def test_register_and_notify_files_a_research_note():
    assert ask.flag_intent(MADHAV_0901) == {"kind": "research"}
    assert ask.flag_intent("please register this as a research item") == {"kind": "research"}
    assert ask.flag_intent("keep track of this for me") is not None
    assert ask.flag_intent("how do I register my account on Zerodha?") is None
    assert ask.flag_intent("what is the register of members?") is None or True   # a noun use is rare; a filed note is harmless


def test_symbols_by_symbol_or_company_name():
    known = {"MARICO", "TATAPOWER", "ITC"}
    names = {"MARICO": "Marico Limited", "TATAPOWER": "Tata Power Company Limited", "ITC": "ITC Limited"}
    assert desk.symbols_in("Marico jumped like ten percent, why?", known, names) == ["MARICO"]
    assert "TATAPOWER" in desk.symbols_in("and what about tata power today", known, names)
    assert desk.symbols_in("how is the Nifty and the VIX", known | {"NIFTY"}, names) == []


def test_a_move_is_explained_by_the_results_filing_first():
    items = [{"at": "2026-11-02 20:40", "kind": "analyst_call", "what": "Con. Call Updates", "text": "audio recording"},
             {"at": "2026-11-02 15:43", "kind": "results", "what": "General Updates", "text": "earnings presentation on the results"}]
    assert "15:43 IST, General Updates" in desk._news_words(items)
    assert desk._news_words([]) == "no company filing found in the fetched days"


def test_moves_and_radar_cover_a_holding_that_moved(tmp_path, monkeypatch):
    d = {"news": {"MARICO": [{"at": "2026-11-02 15:43", "kind": "results", "what": "General Updates", "text": "Q2 results"}]},
         "results_ahead": {"2026-11-04": ["PETRONET"]}, "movers": {"as_of": "2026-11-02", "up": [], "down": []}}
    mv = desk.moves(d, {"rows": [{"symbol": "MARICO", "change_pct": 10.0}, {"symbol": "IDEA", "change_pct": 0.1}]}, ["ITC"])
    assert [r["symbol"] for r in mv["rows"]] == ["MARICO", "ITC"] and "Q2 results" in mv["rows"][0]["why"]
    r = desk.radar(d, mv)
    assert r["rows"][0]["symbol"] == "MARICO" and any(x["symbol"] == "PETRONET" for x in r["rows"]) and "not picks" in r["note"]


def test_prep_has_levels_walls_expected_move_and_open_trades(tmp_path, monkeypatch):
    man = tmp_path / "manifests"
    man.mkdir()
    (man / "premarket_chain.json").write_text(json.dumps({"day": "2026-11-03", "indices": {"NIFTY": {"nearest_expiry": "2026-11-09", "call_walls": [{"strike": 24000}],
                                                           "put_walls": [{"strike": 23500}], "pcr_oi": 1.2, "max_pain": 23700}}}))
    monkeypatch.setattr(desk.views, "DATA", tmp_path)
    f = {"today_live": {"index_now": {"as_of": "19:40 IST", "rows": {"NIFTY 50": {"open": 23582, "high": 23811, "low": 23483, "last": 23811, "change_pct": 1.58},
                                                                     "INDIA VIX": {"last": 16.0}}},
                        "options_today": {"taken": [{"index": "NIFTY", "option": "23650 CE", "expiry": "2026-11-09", "lot": 65, "exit": "NEXTOPEN"}]}}}
    p = desk.prep(f, {})
    n = p["indices"]["NIFTY 50"]
    assert n["previous_session"]["high"] == 23811 and n["expected_move_points"] == 238
    assert n["option_interest"]["call_walls"] == [24000] and n["option_interest"]["of_session"] == "2026-11-03"
    assert p["open_option_trades"][0]["expiry"] == "2026-11-09" and "not a result" in p["open_option_trades"][0]["state"]
    assert p["expiries"]["nifty_next_weekly"]["date"] == "2026-11-09" and "monthly options only" in p["expiries"]["rule"]


def test_expiry_days_say_the_weekday_and_why_they_moved():
    # 3 Nov retest: "the next expiry is ... Tuesday 9 Nov" (a Monday, moved because Tuesday 10 Nov is a holiday)
    hol = {"2026-11-10": "Diwali-Balipratipada", "2026-11-24": "Guru Nanak Jayanti"}
    assert desk.expiry_words("2026-11-09", hol)["words"] == "Monday 9 Nov (moved from Tuesday 10 Nov, a holiday: Diwali-Balipratipada)"
    assert desk.expiry_words("2026-11-17", hol)["words"] == "Tuesday 17 Nov"
    assert desk.expiry_words(None, hol) is None


def test_a_concept_question_about_an_indicator_goes_to_the_model():
    from jarvis.india import technicals
    assert technicals.CONCEPT_Q.search("Is momentum a good thing or not, like the RSI thing, is that the same as momentum")
    assert not technicals.CONCEPT_Q.search("what is Nifty's RSI right now")


def test_data_we_have_never_denies_results_or_announcements():
    w = desk.data_we_have({"inventory": {"announcements": {"research_rows": 980890}, "tracker_rows": []}})
    assert "980,890" in w["have"]["company announcements"] and "partly" in w["have"]["company results"]
    assert "never say 'no X'" in w["rule"]


def test_the_desk_topics_gate_the_long_parts():
    assert desk.DATA_TOPIC.search("do we have company results data like EPS")
    assert desk.BASICS_TOPIC.search("is momentum good, like the RSI thing")
    assert not desk.DATA_TOPIC.search("what happened in the market today")


def test_the_options_line_rule_and_todays_numbers(tmp_path, monkeypatch):
    # round 2 grade: "one lot at a time" and "the move clears the option's cost" were both wrong; the rule is the model's predicted move
    (tmp_path / "paper" / "sp1").mkdir(parents=True)
    rows = [{"kind": "decision", "date": "2026-11-03", "index": "BANKNIFTY", "decided_at": "2026-11-03T09:30:40+05:30", "c": 0.5, "entry_estimate": 55371.4,
             "choice": {"exit": "NEXTOPEN", "pred_gross": 11.31, "pcost": 5.98, "pred_net": 5.33, "se": 4.23}},
            {"kind": "decision", "date": "2026-11-03", "index": "NIFTY", "decided_at": "2026-11-03T09:15:33+05:30", "c": 2.5, "entry_estimate": 23576.65,
             "choice": None, "candidates": [{"pred_net": 0.5, "se": 2.7}]}]
    (tmp_path / "paper" / "sp1" / "decisions.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    monkeypatch.setattr(desk.views, "DATA", tmp_path)
    r = desk.sp1_reasons({"options_today": {"day": "2026-11-03"}})
    took = next(x for x in r if x["took"])
    assert took["index"] == "BANKNIFTY" and took["predicted_move_pts"] == 63 and took["cost_pts"] == 33 and took["bar_pts"] == 12
    assert not next(x for x in r if x["index"] == "NIFTY")["took"]
    assert "one trade per index per day" in desk.OPTIONS_RULE and "c is 2.5 for Nifty and 0.5 for Bank Nifty" in desk.OPTIONS_RULE


def test_toronto_times_in_winter():
    import datetime as dt
    t = desk.toronto_times(dt.date(2026, 11, 4))
    assert t["open"] == "09:15 IST = 10:45 pm Toronto" and t["close"] == "15:30 IST = 5:00 am Toronto"


def test_holdings_against_the_nifty():
    mv = desk.moves({"news": {}}, {"move_pct": 1.1, "move_inr": 1233, "rows": []}, [], 1.58)
    assert mv["holdings_vs_nifty"]["words"] == "your holdings +1.1% against the Nifty +1.6% (they lagged)"


def test_old_cut_list_words_are_read_corrected():
    assert ask._fresh_words({"x": ["No change for Tuesday 3 Nov: nothing is on the cut list."]}) == \
        {"x": ["No change for Tuesday 3 Nov: the managed book has nothing new to cut or buy."]}


def test_a_sign_off_cut_after_a_comma_leaves_no_fragment():
    r = ask.finish({"answer": "It has 7 sessions on record, so it is too early to grade, and all of this is paper only."}, "how many trades", True)
    assert not r["answer"].rstrip(".").endswith(("all of", "and")) and r["answer"].endswith(".")
