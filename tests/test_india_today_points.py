"""4 Nov (Madhav): the Today screen says its facts as short points, the headline is one line, and each box holds two numbers.
The short forms are read from the owners' sentences (records morningview.py, allocator.py); these pin the known sentences and the
rule that an unknown sentence is split, never dropped."""
import datetime as dt

from jarvis.india import surfaces as s

VIEW = ["US: the S&P 500 closed +0.3% (3 Nov), the Nasdaq +0.6%.",
        "Nifty closed at 23,811 on 3 Nov (+1.6%), with no clear trend: +2.5% against its ten-week average, -0.8% against its long-term average; "
        "50% of the 250 most-traded stocks are above their long-term average.",
        "The fear gauge is at 15.66, +18% against its ten-week average — options are pricing more movement than usual.",
        "Yesterday foreign institutions bought ₹6,837 crore and domestic institutions sold ₹3,679 crore.",
        "Odds for today, from how Nifty has behaved since 2005: up 40% (a close above 23,882), down 33% (below 23,739), flat 27%. These are base rates, not a read of today.",
        "Something new the view may say one day; and a second part."]


def test_view_points_short_and_nifty_first():
    p = s._view_points(VIEW)
    assert p[0] == "Nifty closed 23,811 (+1.6%) on 3 Nov · no clear trend"
    assert p[1] == "US: S&P 500 +0.3% · Nasdaq +0.6%"
    assert "India VIX 15.66 (+18% vs usual) · bigger swings priced in" in p
    assert "Foreign institutions bought ₹6,837 cr · domestic sold ₹3,679 cr" in p
    assert any(x.startswith("History's odds for the day: up 40% · down 33% · flat 27%") for x in p)
    assert "Something new the view may say one day" in p and "And a second part" in p, "an unknown sentence is split, not dropped"
    assert not any("fear gauge" in x for x in p), "screens say India VIX"
    assert any("−0.8%" in x for x in p), "a typographic minus"


HS = [{"symbol": "UNITDSPR", "action": "TIDY", "why": "Only ₹1,381, +53% on what you paid: too small to matter either way. Sell it and put the money to work."},
      {"symbol": "JIOFIN", "action": "TRIM", "why": "Middling (51/100) but 23% of your stocks, -21% on what you paid: more than a middling stock should be. Trim it toward 15%."},
      {"symbol": "IEX", "action": "REDUCE", "why": "Weak (30/100): poor result. It is 2% of your stocks, -55% on what you paid. Halving it limits the damage if the slide continues."}]
BENCH = {"frozen_ret_pct": 1.15, "nifty500_ret_pct": 3.79, "frozen_day": "2026-10-22", "managed_ret_pct": 1.07, "managed_sessions": 2, "sessions": 8}


def test_holdings_points(monkeypatch):
    from jarvis.india import compare
    monkeypatch.setattr(compare, "same_window", lambda *a, **k: {"ready": False})
    p = s._holdings_points(HS, BENCH)
    assert p[0] == "Halve IEX; trim JIOFIN; tidy up UNITDSPR", "the bigger move first"
    assert p[1] == "Since 22 Oct: your holdings +1.15% · Nifty 500 +3.79%"
    assert "UNITDSPR: only ₹1,381, too small to matter" in p
    assert "JIOFIN: 23% of your stocks, −21% on cost · trim to 15%" in p
    assert "IEX: 2% of your stocks, −55% on cost · halve it" in p
    assert "Managed book +1.07% · session 2 of 60" in p


def test_holdings_points_compare_the_same_days(monkeypatch):
    """5 Nov (synopsis): the managed book (from 29 Oct) was put beside your holdings from 22 Oct; one window now."""
    from jarvis.india import compare
    monkeypatch.setattr(compare, "same_window", lambda *a, **k: {"ready": True, "since_words": "29 Oct", "managed_pct": 1.51, "yours_pct": 3.78,
                                                                 "nifty500_pct": 3.78, "sessions": 3})
    p = s._holdings_points(HS, BENCH)
    assert p[1] == "Since 29 Oct: managed +1.51% · your holdings +3.78% · Nifty 500 +3.78%"
    assert "Managed book: session 3 of 60" in p and not any("Since 22 Oct" in x for x in p)


def test_same_window_counts_all_three_from_the_managed_start(tmp_path):
    import json
    from jarvis.india import compare
    acct = tmp_path / "paper" / "account"
    acct.mkdir(parents=True)
    (acct / "view.json").write_text(json.dumps({"benchmark": {"managed_start_day": "2026-10-30", "managed_sessions": 3}}))
    rows = [{"day": "2026-10-29", "frozen_inr": 160536, "nifty500_ret_pct": 1.13, "managed_ret_pct": None},
            {"day": "2026-10-30", "frozen_inr": 163076, "nifty500_ret_pct": 0.92, "managed_ret_pct": 0.04},
            {"day": "2026-11-04", "frozen_inr": 166606, "nifty500_ret_pct": 4.95, "managed_ret_pct": 1.51}]
    (acct / "benchmark.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    w = compare.same_window(tmp_path)
    # 12 Nov 2026 (the keen audit, G-12): the row labelled 29 Oct holds the 30 Oct close's prices (the managed book's start), and its index
    # runs only to 29 Oct; all three now count from the 30 Oct close, the index from the row labelled that day
    assert w["ready"] and w["since"] == "2026-10-30" and w["managed_pct"] == 1.51
    assert w["yours_pct"] == 3.78 and w["nifty500_pct"] == round(((1 + 4.95 / 100) / (1 + 0.92 / 100) - 1) * 100, 2) and w["managed_minus_yours_pts"] == -2.27
    assert "30 Oct close" in w["words"] and "session 3 of 60" in w["words"].lower()


def test_watch_points():
    p = s._watch_points(["Next options expiry: 9 Nov (NIFTY).",
                         "The lines that decide the day's label: above 23,882 is an up day, below 23,739 a down day.",
                         "Option chain at yesterday's close (context only; no edge found in it): Bank Nifty: puts/calls open 0.97, max pain 55,600, biggest call wall "
                         "58,000, put wall 58,000; Nifty: puts/calls open 1.93, max pain 23,700, biggest call wall 23,850, put wall 23,700.",
                         "Results today: CEWATER. A results day can gap either way."])
    assert p[:2] == ["Next options expiry: 9 Nov (NIFTY)", "Up day above 23,882 · down day below 23,739"]
    assert "Nifty options: most calls at 23,850, most puts at 23,700 (context only)" in p
    assert "Results today: CEWATER" in p


def test_split_points_keeps_brackets_whole():
    assert s._split_points("F&O ban list today: KAYNES (no new positions; cash is fine); next part. Last one.") == [
        "F&O ban list today: KAYNES (no new positions; cash is fine)", "Next part", "Last one"]


def test_headline_one_short_line():
    clk = {"today_india": "2026-11-05"}
    assert s.headline({"for_session": "2026-11-05", "no_change": True, "buys": [], "cuts": []}, clk) == "No change today"
    assert s.headline({"for_session": "2026-11-06", "no_change": True}, clk) == "No change tomorrow"
    assert s.headline({"for_session": "2026-11-04", "no_change": True}, clk) == "No change on Wed"
    assert s.headline({"for_session": "2026-11-05", "buys": [{"symbol": "A"}, {"symbol": "B"}], "cuts": [{"symbol": "X"}]}, clk) == "2 swaps today"
    assert s.headline({"for_session": "2026-11-05", "buys": [], "cuts": [{"symbol": "X"}]}, clk) == "1 cut today, cash kept"
    assert s.headline({}, clk) == "No plan yet"


def test_option_open():
    assert s._option_open({"exit": "NEXTOPEN"}, {"state": "closed"})
    assert not s._option_open({"exit": "T1515"}, {"state": "closed", "latest_session": "2026-11-04", "today_india": "2026-11-04"})


def test_index_tile_falls_back_to_the_nightly_closes():
    rm = {"market": {"newer_closes": {"NIFTY 50": {"date": "2026-11-04", "close": 23960.6, "d1": 0.0063},
                                      "NIFTY BANK": {"date": "2026-11-04", "close": 55913.6, "d1": 0.0067}}}}
    t = s._index_tile(rm, None)
    a, b = t["pages"]
    assert (a["label"], a["value"], a["tone"]) == ("Nifty 50", "23,961", "good") and a["sub"].startswith("+150 (+0.6%)")
    assert (b["label"], b["value"]) == ("Bank Nifty", "55,914") and b["sub2"] == "Wed 4 Nov close"


def test_account_tile_stocks_then_options():
    t = s._account_tile({"value_inr": 162212, "stocks_inr": 84598, "options_inr": 50000, "cash_inr": 27614, "positions": 11}, {}, None)
    a, b = t["pages"]
    assert (a["label"], a["value"], a["sub"], a["sub2"]) == ("Stocks", "₹84,598", "11 stocks", "Cash ₹27,614")
    assert (b["label"], b["value"], b["sub"]) == ("Options", "₹50,000", "No open trade")
    assert dt.date  # the date module stays imported for the clock cases above


def test_options_page_one_open_trade(monkeypatch):
    from jarvis.india import livesession
    monkeypatch.setattr(livesession, "options_today", lambda clk, fetch=None: {"taken": [
        {"index": "BANKNIFTY", "exit": "NEXTOPEN", "option": "55800 CE", "paper_move_inr_per_lot": 534}]})
    b = s._account_tile({"value_inr": 1, "stocks_inr": 1, "options_inr": 50000, "positions": 11}, {}, {"state": "before_open"})["pages"][1]
    assert (b["sub"], b["sub2"], b["tone2"]) == ("Open · Bank Nifty", "55800 CE · +₹534", "good")
    assert all(len(x) <= 18 for x in (b["sub"], b["sub2"])), "a half-width box holds about 17 characters a line"
