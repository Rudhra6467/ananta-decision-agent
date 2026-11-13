"""Audit repair 2, India dates and marks (12 Nov 2026, the keen outside audit; open-list flag 118). Each finding's checks failed before its
fix. G-09 (the options review day) is checked in tests/test_voice_knows_plan_11nov.py, beside the 11 Nov check it corrects."""
import datetime as dt
import json

from jarvis import placekit as K
from jarvis.india import livesession as L
from jarvis.india import places as IP
from jarvis.india import surfaces as IS
from tests.test_places_india import TODAY, india  # noqa: F401  (india is the places fixture: fixed inputs, no live data)

UTC = dt.timezone.utc
_FIXTURES = (india,)                                                                     # the places fixture, used by name below


def _box(surface: dict, label: str) -> dict:
    for part in surface.get("parts") or []:
        for c in part.get("items") or part.get("cards") or []:
            if isinstance(c, dict) and c.get("label") == label:
                return c
    raise AssertionError(f"no {label} box")


# ------------------------------------------------------------------------------------------------ G-05: one fear-gauge value
def test_the_fear_gauge_is_read_with_the_index_boxes_under_their_day(india_reference):
    """Kite's read after Monday's close: the gauge comes from the same read and under the same day as the Nifty boxes."""
    table = {"NSE:NIFTY 50": (25044.65, 24986.40), "NSE:NIFTY BANK": (59741.25, 58850.65), "NSE:INDIA VIX": (17.56, 17.63)}

    def fetch(syms):
        return {s: {"last_price": table[s][0], "ohlc": {"open": table[s][0], "high": table[s][0], "low": table[s][0], "close": table[s][1]}}
                for s in syms if s in table}

    L._CACHE.clear()
    clk = L.clock("2026-11-06", dt.datetime(2026, 11, 9, 10, 30, tzinfo=UTC))           # Mon 9 Nov 16:00 IST, after the close
    tile = IS._index_tile({}, clk, fetch)
    assert tile["pages"][0]["sub2"] == "Mon 9 Nov close"
    # 12 Nov evening (repair 2's outside check, N4): after the close Zerodha's number is called its last price, never "the close", which
    # the closing-bars path keeps for the index file's value (the voice's)
    assert tile["vix"]["value"] == "17.56" and tile["vix"]["when"] == "Mon 9 Nov · last price" and tile["vix"]["source"] == "Zerodha's last price"
    assert abs(tile["vix"]["change_pct"] - (-0.4)) < 0.01
    L._CACHE.clear()
    live = L.clock("2026-11-06", dt.datetime(2026, 11, 9, 6, 0, tzinfo=UTC))             # Mon 9 Nov 11:30 IST, in the session: as before
    assert IS._index_tile({}, live, fetch)["vix"]["when"].startswith("Live · ")
    L._CACHE.clear()


def test_markets_and_the_gauges_page_show_that_one_value_never_a_number_cut_from_a_sentence(india, monkeypatch):
    """Before: Markets cut 'VIX 17.4' (Monday's) out of a card's sentence and showed it under Wednesday's date; the gauge's own page showed
    the last 5-minute candle (17.53); the exchange's close was 17.56."""
    t = json.loads(json.dumps(TODAY))
    t["tiles"][0]["vix"] = {"value": "17.56", "when": "Mon 9 Nov close", "change_pct": -0.4}
    t["cards"] = [{"kind": "close", "points": ["Nifty 25,045 (+0.2%) · Bank Nifty 59,741 (+1.5%) · VIX 15.1"]}]   # an older sentence
    monkeypatch.setattr(IS, "today", lambda full=True: json.loads(json.dumps(t)))
    m = IP.markets()
    box = _box(m, "Fear gauge")
    assert box["value"] == "17.56" and box.get("change") == "−0.4%"
    assert "15.1" not in json.dumps(m, ensure_ascii=False)
    peek = next(p for p in m["parts"] if p.get("t") == "peek")
    assert peek.get("note") == "Mon 9 Nov close"                                         # the boxes' one day, the gauge's too
    page = IP.index_page("vix")
    hero = next(p for p in page["parts"] if p.get("t") == "hero")
    assert hero["value"] == "17.56" and hero.get("since") == "Mon 9 Nov close"


def test_with_no_reading_the_gauge_says_so_rather_than_borrow_a_sentences_number(india, monkeypatch):
    t = json.loads(json.dumps(TODAY))
    t["cards"] = [{"kind": "close", "points": ["VIX 15.1"]}]
    monkeypatch.setattr(IS, "today", lambda full=True: json.loads(json.dumps(t)))
    monkeypatch.setattr(IP, "index_candles", lambda *a, **k: {})
    m = IP.markets()
    assert not any(isinstance(c, dict) and c.get("label") == "Fear gauge"
                   for p in m["parts"] for c in (p.get("items") or p.get("cards") or []))
    hero = next(p for p in IP.index_page("vix")["parts"] if p.get("t") == "hero")
    assert hero["value"] == "—"



# ------------------------------------------------------------------------------------------------ G-04: Home's plan names its own day
def test_homes_plan_block_names_the_plans_own_day_after_the_indian_day_turns(india, monkeypatch):
    """The audit's moment: Wed 11 Nov 2:30 pm Toronto is Thu 12 Nov 1:00 am in India, before the open; the plan on file is Wednesday's.
    Before: 'Before the open · Thu 12 Nov' over 'No change on Wednesday.'"""
    monkeypatch.setattr(IP, "_clk", lambda: {"state": "before_open", "latest_session": "2026-11-11", "next_session": "2026-11-12",
                                             "today_india": "2026-11-12"})
    monkeypatch.setattr(IP, "_evening_at", lambda: "8:20 pm Toronto (06:50 IST)")
    today = next(p for p in IP.home()["parts"] if p["t"] == "today")
    assert today["label"] == "Last plan · Wed 11 Nov"
    assert today["line"] == "No change on Wednesday."
    assert today["sub"] == "Plan for Thu 12 Nov: written at 8:20 pm Toronto (06:50 IST)." and "Wed" not in today["sub"]
    assert K.nwords(today["sub"]) <= K.MAX["today_sub"]           # 12 Nov (N11): it was one word over the block's second line
    monkeypatch.setattr(IP, "_evening_at", lambda: "")
    assert next(p for p in IP.home()["parts"] if p["t"] == "today")["sub"] == "The plan for Thu 12 Nov is not written yet."


def test_when_the_plan_is_for_the_coming_session_the_block_is_as_before(india, monkeypatch):
    monkeypatch.setattr(IP, "_clk", lambda: {"state": "closed", "latest_session": "2026-11-09", "next_session": "2026-11-11",
                                             "today_india": "2026-11-10"})
    today = next(p for p in IP.home()["parts"] if p["t"] == "today")
    assert today["label"] == "Next session · Wed 11 Nov" and today["line"] == "No change on Wednesday."


# ------------------------------------------------------------------------------------------------ G-03: the account's number says its close
def test_the_accounts_value_carries_the_day_of_the_book_it_comes_from(monkeypatch):
    """Before: the value came from the managed book and its 'as of' from the account book's marks (two books marked at different times)."""
    from jarvis.india import compare, views
    monkeypatch.setattr(views, "allocation_plan", lambda full=True: {})
    monkeypatch.setattr(IS, "_account_view", lambda: {"marks": {"last_session": "2026-11-11"}, "benchmark": {}})
    monkeypatch.setattr(IS, "_managed", lambda: {"value_inr": 164725, "day": "2026-11-09", "plan": {}, "clock": {}})
    monkeypatch.setattr(compare, "same_window", lambda: {"ready": False})
    monkeypatch.setattr(IS, "_options_block", lambda acct: {})
    m = IS.money()
    assert m["value_inr"] == 164725 and m["value_owner"] == "the managed book"
    assert m["as_of_day"] == "2026-11-09" and m["as_of"] == "NSE close Mon 9 Nov"


def test_home_and_account_say_which_close_the_big_number_is_marked_at(india, monkeypatch):
    """Before: Home's 'Your paper account' had no date at all, beside index boxes dated the latest session."""
    monkeypatch.setattr(IS, "_managed", lambda: {"start_inr": 160499, "start_day": "2026-10-30", "positions": 11, "day": "2026-11-09"})
    hero = next(p for p in IP.home()["parts"] if p["t"] == "hero")
    assert hero["label"] == "Your paper account · Mon 9 Nov close" and hero["value"] == "₹1,64,725"
    hero = next(p for p in IP.account()["parts"] if p["t"] == "hero")
    assert hero["since"] == "since Fri 30 Oct, at the Mon 9 Nov close"


# ------------------------------------------------------------------------------------------------ 12 Nov evening: repair 2's outside check
def test_the_accounts_comparison_and_chart_say_the_close_they_run_to_when_it_lags_the_big_number(india, monkeypatch):
    """N1 (S2, made by repair 2): from the nightly mark (about 12:45 pm Toronto) to the evening run (8:20 pm), Account's big number was at the
    day's close while 'How it compares' and the chart were still at the session before, and neither said which day it ran to."""
    from jarvis.india import compare
    real = IS.money

    def money(full=True):
        return dict(real(full), books_through="2026-11-09")
    monkeypatch.setattr(IS, "money", money)
    monkeypatch.setattr(compare, "same_window", lambda: {"ready": True, "through": "2026-11-09"})
    monkeypatch.setattr(IS, "_managed", lambda: {"start_inr": 160499, "start_day": "2026-10-30", "positions": 11, "day": "2026-11-10"})
    monkeypatch.setattr(IS, "portfolio_chart", lambda: {"chart": {"dates": ["2026-11-06", "2026-11-09"], "managed": [163000, 164725]}})
    parts = IP.account()["parts"]
    kv = next(p for p in parts if p.get("t") == "kv" and p.get("title") == "How it compares")
    assert "The big number above is at the Tue 10 Nov close; this runs to the Mon 9 Nov close and catches up after the evening run." in kv["foot"]
    ch = next(p for p in parts if p.get("t") == "chart")
    assert ch["caption"] == "One point a session, at the close. The Tue 10 Nov close joins after the evening run."
    monkeypatch.setattr(IS, "_managed", lambda: {"start_inr": 160499, "start_day": "2026-10-30", "positions": 11, "day": "2026-11-09"})
    parts = IP.account()["parts"]                                                          # after the evening run: no lag, the day is said
    kv = next(p for p in parts if p.get("t") == "kv" and p.get("title") == "How it compares")
    assert kv["foot"].endswith(" To the Mon 9 Nov close.") and "catches up" not in kv["foot"]
    assert next(p for p in parts if p.get("t") == "chart")["caption"] == "One point a session, at the close."


def test_a_holding_at_an_older_price_is_said_on_home_and_account(india, monkeypatch):
    """N7 (S3, on the path repair 2 touched): the managed book kept a holding's old price without a word when it had no bar that day."""
    mb = {"start_inr": 160499, "start_day": "2026-10-30", "positions": 11, "day": "2026-11-10", "kept_old_price": {"IEX": "2026-11-09"}}
    monkeypatch.setattr(IS, "_managed", lambda: dict(mb))
    hero = next(p for p in IP.home()["parts"] if p["t"] == "hero")
    assert hero["since"] == "since Fri 30 Oct · 1 at an older price"
    parts = IP.account()["parts"]
    assert any(p.get("t") == "line" and "No close that day, so at an older price: " in str(p) and "last marked Mon 9 Nov" in str(p) for p in parts)
    monkeypatch.setattr(IS, "_managed", lambda: dict(mb, kept_old_price={}))
    assert next(p for p in IP.home()["parts"] if p["t"] == "hero")["since"] == "since Fri 30 Oct"
    assert not any(p.get("t") == "line" and "older price" in str(p) for p in IP.account()["parts"])
