"""Crypto's new look, brought level with India's (Madhav, 10 Nov 2026: "adding bitcoin, eth and sol in home square box in place of nifty
50 and bank nifty. Showing info in points (very simple words). And other changes to other tabs as well ... do the necessary changes to
crypto market Ananta as well"). Today: a one-line headline, a box of three live prices and a box for the account, every card as points.
Proof: an explanation under each top card. Charts for the three coins and the account. Display only: nothing here writes or decides."""
import datetime as dt
import json
import random
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from jarvis.service import surfaces as S
from tests.test_universe_live import J

DAY = 86400
TOR = ZoneInfo("America/Toronto")
ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "jarvis" / "app"
NOW = dt.datetime(2026, 11, 10, 2, 24, tzinfo=TOR)
CLOSED = {"dial": 0.0, "dial_words": "CLOSED: no new buys; cash is the position", "as_of_day": "2026-11-09",
          "why": ["Bitcoin closed 2026-11-09 at 75,368", "below its 50-day average (79,321)", "above its 200-day average (73,209)"]}
OPEN = {"dial": 1.0, "dial_words": "OPEN: buying allowed", "as_of_day": "2026-11-09",
        "why": ["Bitcoin closed 2026-11-09 at 82,000", "above its 50-day average (79,321)", "above its 200-day average (73,209)"]}
BOOK = {"started": "2026-10-11", "value_cad": 439.49, "cash_cad": 439.49, "return_pct": -12.1, "positions": {}, "closed": [], "recent_fills": [],
        "brakes": {}, "graduation": {"passed": 3, "of": 10, "verdict": "NOT READY", "closed_trades": 0}}
LINE = ("the dial is closed (Bitcoin under its 50- or 200-day average). Account: no core: cash; cash 100% (target 70%). Bold: SIT. "
        "Officer: cash is 100% of the book against a 70% target, for 16 days. Setups: Scanned 118 coins: 5 setups fired, 14 one step away. "
        "Best: BAT (pullback to the 20-day average in an uptrend), MUBARAK (short dip in an uptrend). Strongest against Bitcoin over 20 days: "
        "BMT, MEGA, JST. Held back by the closed dial (the brain reviews them only when the dial reopens): BAT PULL, MUBARAK H07, RLC H07. "
        "Touched their trigger today: MEGA (BRK). View: The dial stays CLOSED: BTC closed at 75,368, 5.0% under its 50-day (79,321).")


def _bars(n: int = 400, last_day: str = "2026-11-09", start_px: float = 60000.0, seed: int = 7) -> list[tuple]:
    """n daily candles ending on last_day (UTC), a seeded walk: (t, o, h, l, c, v)."""
    rnd = random.Random(seed)
    t_last = int(dt.datetime.fromisoformat(last_day).replace(tzinfo=dt.timezone.utc).timestamp())
    out, px = [], start_px
    for k in range(n):
        o = px
        c = o * (1 + rnd.uniform(-0.03, 0.031))
        out.append((t_last - (n - 1 - k) * DAY, o, max(o, c) * 1.005, min(o, c) * 0.995, c, 1000.0))
        px = c
    return out


def _prices(px: dict, at: dt.datetime):
    from jarvis.service.trade_guard import Prices
    return Prices(px, {c: at.timestamp() for c in px})


# ---------------------------------------------------------------------------------------------------------------- the headline and the boxes

def test_the_headline_is_one_short_line():
    two = [{"symbol": "BTC"}, {"symbol": "ETH"}]
    said = [S.headline(CLOSED, [], None), S.headline(CLOSED, two, None), S.headline(OPEN, [], None), S.headline(OPEN, two, None),
            S.headline(OPEN, two, "a loss brake blocks new buys until 7 pm today"), S.headline({"dial": None}, [], None)]
    assert said == ["No new buys: all in cash", "No new buys, 2 coins held", "Buying is on: all in cash", "Buying is on, 2 coins held",
                    "Buys paused by a loss brake", "No reading yet"]
    assert all(len(x) <= 28 for x in said)                                    # one line on a phone, beside the Details button


def test_the_first_box_is_bitcoin_ethereum_and_solana_live(monkeypatch):
    from jarvis.service import feed
    monkeypatch.setattr(feed, "last_closes", lambda j: {"BTC": 75368.41, "ETH": 2135.24, "SOL": 86.74})
    monkeypatch.setattr(feed, "prices", lambda j: _prices({"BTC": 74832.0, "ETH": 2123.0, "SOL": 86.29}, NOW))
    pages = S._coin_pages(None, CLOSED, NOW)
    assert [p["label"] for p in pages] == ["Bitcoin", "Ethereum", "Solana"] and [p["coin"] for p in pages] == ["BTC", "ETH", "SOL"]
    assert [p["value"] for p in pages] == ["$74,832", "$2,123", "$86.29"]
    assert pages[0]["sub"] == "−0.7% since 7 pm" and pages[0]["tone"] == "bad" and pages[0]["sub2"] == "Live · 2:24 am"
    assert all(len(p["sub"]) <= 17 and len(p["sub2"]) <= 17 for p in pages)   # a half-width box holds about 17 characters a line
    # no live price (the feed is older than ten minutes): the last daily close, and its day
    monkeypatch.setattr(feed, "prices", lambda j: _prices({}, NOW))
    pages = S._coin_pages(None, CLOSED, NOW)
    assert pages[0]["value"] == "$75,368" and pages[0]["sub"] == "Mon 9 Nov close" and "tone" not in pages[0]
    monkeypatch.setattr(feed, "last_closes", lambda j: {})
    assert S._coin_pages(None, CLOSED, NOW)[2]["sub"] == "no price on file"


def test_the_second_box_is_the_account_then_its_coins():
    p1, p2 = S._account_pages(BOOK, [])
    assert (p1["label"], p1["value"], p1["sub"], p1["sub2"], p1["tone"]) == ("Your account", "C$439", "−12.1% from C$500", "All in cash", "bad")
    assert (p2["label"], p2["value"], p2["sub"], p2["sub2"]) == ("Coins held", "C$0", "No coins held", "Cash C$439")
    pos = [{"symbol": "BTC", "value": 60.0}, {"symbol": "ETH", "value": 30.0}]
    p1, p2 = S._account_pages({**BOOK, "value_cad": 510.0, "cash_cad": 420.0, "return_pct": 2.0}, pos)
    assert p1["sub2"] == "2 coins · C$420 cash" and p1["tone"] == "good" and p2["value"] == "C$90" and p2["sub"] == "BTC and ETH"


# ---------------------------------------------------------------------------------------------------------------- the cards, as points

def test_the_market_card_says_the_dial_in_simple_words():
    closes = {"BTC": 75368.41, "ETH": 2135.24, "SOL": 86.74}
    pts = S._dial_points(CLOSED, closes, NOW)
    assert pts[:4] == ["Bitcoin closed at $75,368 on Mon 9 Nov", "That is 5.0% below its 50-day average ($79,321), so buying is off",
                       "It is 2.9% above its 200-day average ($73,209)", "Buying turns on when Bitcoin closes above both averages"]
    assert "Ethereum closed at $2,135 · Solana at $86.74" in pts and "Next check at the daily close, 7 pm Toronto" in pts
    up = S._dial_points(OPEN, closes, NOW)
    assert up[1].endswith("so buying is on") and "Buying turns off when Bitcoin closes below either average" in up
    assert not any("CLOSED" in p or "OPEN" in p or "v1" in p for p in pts + up)
    assert S._dial_points({"dial": None, "note": "not enough Bitcoin history in the feed yet"}, {}, NOW) == ["Not enough Bitcoin history in the feed yet"]


def test_the_setups_card_is_points_with_no_rule_codes():
    pts = S._setup_points(S._plan_parts(LINE))
    assert pts[0] == "118 coins checked: 5 show a buy setup, 14 are one step away"
    assert pts[1].startswith("Best: BAT (pullback to the 20-day average in an uptrend)")
    assert "Held back while buying is off: BAT, MUBARAK, RLC" in pts
    assert "Touched their trigger today: MEGA (breakout)" in pts and "Strongest against Bitcoin over 20 days: BMT, MEGA, JST" in pts
    assert not any(code in p for p in pts for code in ("H07", "PULL", "BRK"))


def test_a_note_becomes_its_sentences_and_numbers_stay_whole():
    assert S._sentences("Worth about C$439.49 today. Bitcoin is 5.0% under its average. Nothing needs you.") == [
        "Worth about C$439.49 today", "Bitcoin is 5.0% under its average", "Nothing needs you"]


def _j_with_fills(tmp_path, fills):
    from jarvis.service import ndax_book
    j = J(tmp_path)
    ndax_book._table(j)
    for f in fills:
        j.db.execute("INSERT INTO book500_fills VALUES (?,?,?,?,?,?,?,?,?,?)", f)
    return j


T26, T28, T29 = 1792973158, 1793145967, 1793232361     # 26, 28 and 29 Oct 2026, minutes after the daily close
FILLS = [(T26, "ETH", "BUY", "EDGE", 0.008315, 3271.40, 3265.0, 3271.40, 0.054, "H07: RSI(10) 30, above the 200-day"),
         (T28, "ETH", "BUY", "CORE", 0.009683, 3304.71, 3300.0, 3304.71, 0.064, "core-v2 tranche 1"),
         (T28, "BTC", "BUY", "CORE", 0.000563, 113719.86, 113000.0, 113719.86, 0.128, "core-v2 tranche 1"),
         (T29, "ETH", "SELL", "CORE", 0.009683, 3289.09, 3289.09, 3295.0, 0.064, "invalidation"),
         (T29, "BTC", "SELL", "CORE", 0.000563, 108815.09, 108815.09, 109000.0, 0.122, "dial closed")]


def test_a_buy_that_left_the_holdings_without_a_sale_is_said(tmp_path):
    """10 Nov 2026: 0.008315 ETH bought on 26 Oct (an edge trade) left the $500 book's holdings on 28 Oct when the core bought ETH; no
    sale was ever recorded, so the book's value leaves it out. The screens say so until Madhav decides the repair."""
    j = _j_with_fills(tmp_path, FILLS)
    gap = S.book_gap(j, {"positions": {}})
    assert len(gap) == 1 and gap[0]["coin"] == "ETH" and abs(gap[0]["qty"] - 0.008315) < 1e-12
    assert gap[0]["day"] == "2026-10-26" and gap[0]["paid_cad"] == 27.26
    said = S.gap_words(gap)
    assert said == "Under check: 0.008315 ETH bought on Mon 26 Oct for C$27.26 is missing from the book's holdings, so the value shown is too low."
    # once the holdings carry it again (or it is sold), nothing is said
    assert S.book_gap(j, {"positions": {"ETH": {"qty": 0.008315}}}) == [] and S.gap_words([]) is None


def _fake_today(monkeypatch, tmp_path, dial=CLOSED, book=BOOK, fills=()):
    from jarvis.service import discipline, exposure, feed, health, waiting
    j = _j_with_fills(tmp_path, list(fills))
    monkeypatch.setattr(S, "_book", lambda j: dict(book))
    monkeypatch.setattr(S, "_dial", lambda j: dict(dial))
    monkeypatch.setattr(S, "_officer_note", lambda j: {"day": "2026-11-10", "text": "The account sat in cash, worth about C$439.49. The H07 losses stopped. Nothing needs you."})
    monkeypatch.setattr(discipline, "plan_line", lambda j: {"line": LINE, "checks": [{"id": "idle_cash", "state": "FAIL", "words": "cash is 100% of the book against a 70% target, for 16 days"},
                                                                                     {"id": "core_exit", "state": "OK", "words": "no core position"}]})
    monkeypatch.setattr(health, "status", lambda j: {"all_ok": True, "down": [], "last_check_s_ago": 40})
    monkeypatch.setattr(waiting, "collect", lambda j: {"count": 0, "line": ""})
    monkeypatch.setattr(feed, "last_closes", lambda j: {"BTC": 75368.41, "ETH": 2135.24, "SOL": 86.74})
    monkeypatch.setattr(feed, "prices", lambda j: _prices({"BTC": 74832.0, "ETH": 2123.0, "SOL": 86.29}, dt.datetime.now(TOR)))
    monkeypatch.setattr(exposure, "books", lambda j: {"books": [{"book": "HOLD", "return_pct": -9.2}, {"book": "GATE50", "return_pct": -13.9}]})
    from jarvis import selfcheck
    monkeypatch.setattr(selfcheck, "check", lambda market=None, now=None: {"at": None, "items": []})
    monkeypatch.setattr(S, "like_for_like", lambda j: "")                     # it asks NDAX for a quote: never from a test
    return j


def test_today_has_the_india_shape_headline_boxes_and_points(monkeypatch, tmp_path):
    j = _fake_today(monkeypatch, tmp_path)
    d = S.today(j)
    assert d["headline"] == "No new buys: all in cash" and d["decision"].startswith("Buying is off (the dial is closed)")
    assert "nothing is placed, paper only" in d["decision_source"]
    assert [t["id"] for t in d["tiles"]] == ["market", "account"]
    assert [p["label"] for p in d["tiles"][0]["pages"]] == ["Bitcoin", "Ethereum", "Solana"]
    assert [p["label"] for p in d["tiles"][1]["pages"]] == ["Your account", "Coins held"]
    kinds = [c["kind"] for c in d["cards"]]
    assert kinds == ["market", "account", "setups", "checks", "note"] and len(set(kinds)) == len(kinds)   # the app keys each card on its kind
    for c in d["cards"]:
        assert c["points"] and all(isinstance(p, str) and p and not p.endswith(".") for p in c["points"]), c["kind"]
        assert c["text"]                                                       # older app builds still read the paragraph
    assert d["cards"][0]["accent"] and d["cards"][0]["label"] == "The market · buying is off"
    acct = d["cards"][1]["points"]
    assert acct[0] == "C$439.49, all in cash: no coins held" and acct[1] == "Down 12.1% since it started with C$500 on Sun 11 Oct"
    assert "Bitcoin just held since Sat 10 Oct: −9.2% · the hurdle to beat: −13.9%" in acct
    assert d["cards"][3]["points"] == ["Cash is 100% of the book against a 70% target, for 16 days"]
    assert d["cards"][4]["points"][1] == "The short dip losses stopped"       # no rule code on the screen
    assert len(d["numbers"]) == 2 and d["numbers"][0]["value"] == "75,368"    # the two single numbers stay for older builds
    assert d["running"] == {"ok": True, "words": "Everything is running", "checked": "checked just now"}
    assert d["evening"] is None and d["suggested"][0] == "Why is the dial closed?"


def test_today_says_the_missing_buy_second_on_the_account_card(monkeypatch, tmp_path):
    j = _fake_today(monkeypatch, tmp_path, fills=FILLS)
    acct = S.today(j)["cards"][1]["points"]
    assert acct[1].startswith("Under check: 0.008315 ETH bought on Mon 26 Oct") and acct[1].endswith("so the value shown is too low")
    m = S.money(j)
    assert m["under_check"].startswith("Under check: 0.008315 ETH") and "Under check" in m["holdings_note"]


def test_what_the_book_did_at_the_last_close_is_points(monkeypatch, tmp_path):
    close = dt.datetime(2026, 11, 10, tzinfo=dt.timezone.utc)                 # the Mon 9 Nov candle closed here
    book = {**BOOK, "closed": [{"coin": "SOL", "out": "2026-11-10", "pnl_cad": -3.38, "why": "10 days"}],
            "recent_fills": [{"t": close.timestamp() + 300, "coin": "SOL", "side": "SELL", "qty": 0.198418, "px": 125.15, "why": "10 days"},
                             {"t": close.timestamp() + 300, "coin": "BTC", "side": "BUY", "qty": 0.000528, "px": 112763.88, "why": "core-v2 tranche 1"},
                             {"t": close.timestamp() - DAY, "coin": "AVAX", "side": "SELL", "qty": 1.4655, "px": 12.14, "why": "RSI(10) over 40"}]}
    j = _fake_today(monkeypatch, tmp_path, book=book)
    ev = S.today(j)["evening"]
    assert ev["label"] == "What the $500 book did at the Mon 9 Nov close"
    assert ev["points"] == ["Sold Solana for C$24.83 (10 days): −C$3.38", "Bought Bitcoin for C$59.54"]


def test_the_status_line_says_a_high_self_check_item_first(monkeypatch):
    from jarvis import selfcheck
    monkeypatch.setattr(selfcheck, "check", lambda market=None, now=None: {"at": 1794269159.0, "items": [
        {"market": "crypto", "severity": "high", "source": "services", "what": "the crypto worker has not run its jobs for 78 minutes"}]})
    r = S._running({"all_ok": True, "down": []})
    assert r["ok"] is False and r["words"].startswith("The crypto worker has not run its jobs") and r["checked"].startswith("checked ")
    monkeypatch.setattr(selfcheck, "check", lambda market=None, now=None: {"at": None, "items": []})
    assert S._running({"all_ok": True, "down": [], "last_check_s_ago": 7200}) == {"ok": True, "words": "Everything was running at the last check", "checked": "checked 120 min ago"}
    assert S._running({"all_ok": False, "down": ["the eye"], "last_check_s_ago": 30})["words"] == "1 part down"


def test_money_says_the_plan_in_simple_words(monkeypatch, tmp_path):
    j = _fake_today(monkeypatch, tmp_path)
    m = S.money(j)
    assert m["plan"]["brief"] == "Buying is off. The core (the Bitcoin and Ethereum part) is in cash until Bitcoin closes above both its 50-day and 200-day averages."
    assert m["under_check"] is None and "Under check" not in m["holdings_note"]


# ---------------------------------------------------------------------------------------------------------------- Proof's explanations

def test_the_strategies_card_opens_an_explanation():
    from jarvis.service import strategy_status
    e = S.strategies_explain(strategy_status.load(), S._window(dt.date(2026, 11, 10)))
    assert e["title"] == "The strategies, explained" and e["ask"] == S.STRAT_Q and e["source"] == "the strategy register" and e["updated"]
    pts = e["points"]
    assert pts[0].startswith("A strategy is one way of trading") and " are on record: " in pts[1]
    assert any(p.startswith("The one measured edge is the short dip trade.") for p in pts)
    assert any(p.startswith("Until Mon 14 Dec no new crypto strategy is studied and no rule changes (Rule B). Day 27 of 60") for p in pts)
    assert not any(code in p for p in pts for code in ("H07", "E1-E8", "ZONE_TOUCH", "UNDER_REVIEW", "PARKED"))


def test_the_weekly_exam_card_opens_an_explanation(tmp_path):
    d = tmp_path / "docs" / "repair_shop" / "exam"
    d.mkdir(parents=True)
    last = {"day": "2026-11-08", "known": 20, "known_of": 20, "unknown": 9, "unknown_of": 10, "why": 5, "why_of": 5, "consistent": 2, "consistent_of": 2,
            "knows_pass": True, "unknowns_pass": True, "why_pass": True, "consistency_pass": True, "exam_pass": True,
            "rows": [{"id": "dial", "ok": True, "question": "What is the exposure dial's rule?"}, {"id": "staking", "ok": False, "question": "What did our review of Cardano staking rewards find?"}]}
    (d / "latest.json").write_text(json.dumps(last))
    hist = [{"day": "2026-10-11", "known_of": 20}, {"day": "2026-10-15", "known_of": 20, "exam_pass": True}, {"day": "2026-10-21", "known_of": 20, "exam_pass": False},
            {"day": "2026-11-02", "file": "voice_latest.json", "pass": True}, {"day": "2026-11-08", "known_of": 20, "exam_pass": True}]
    (d / "history.jsonl").write_text("\n".join(json.dumps(x) for x in hist) + "\n")
    e = S.exam_explain(tmp_path)
    assert e["title"] == "The weekly exam, explained" and e["updated"] == "Sun 8 Nov" and e["ask"] == S.EXAM_Q
    assert e["points"][1] == ("The last exam (Sun 8 Nov): knows 20 of 20, says 'I don't know' when it should 9 of 10, explains why 5 of 5, "
                              "gives the same answer when asked twice 2 of 2: pass.")
    assert e["points"][2] == "Marked wrong: “What did our review of Cardano staking rewards find?”."
    assert e["points"][3] == "2 of 3 graded runs passed, since Thu 15 Oct."   # only runs that carry the exam's own verdict; the voice exam is not one
    assert S.exam_explain(tmp_path / "nowhere") is None                        # no record: the card stands without an explanation


# ---------------------------------------------------------------------------------------------------------------- the charts

def test_a_coin_chart_is_closes_with_the_dials_two_averages(monkeypatch):
    from jarvis.service import feed
    from src.research import review25 as R
    bars = _bars()
    monkeypatch.setattr(feed, "daily", lambda j, coin: bars)
    c = S.chart(None, "btc")
    ch = c["chart"]
    assert c["name"] == "Bitcoin" and c["kind"] == "index" and c["as_of"] == "9 Nov close"
    assert len(ch["dates"]) == len(ch["closes"]) == len(ch["sma50"]) == len(ch["sma200"]) == 120 and ch["dates"][-1] == "2026-11-09"
    closes = [b[4] for b in bars]
    assert ch["sma50"][-1] == round(R.ema(closes, 50)[-1], 2) and ch["sma200"][-1] == round(R.sma(closes, 200)[-1], 2)   # the dial's own averages
    assert "its 50-day average" in c["words"] and "over the last 30 days" in c["words"] and c["words"].endswith("Buying is on only while Bitcoin closes above both lines.")
    assert c["x_labels"] == [S._dm(ch["dates"][0]), "9 Nov"] and c["note"].endswith("They are the averages the dial reads.")
    eth = S.chart(None, "Ethereum")
    assert eth["name"] == "Ethereum" and eth["note"].endswith("The dial reads the same two averages on Bitcoin.") and S.chart(None, "SOL")["coin"] == "SOL"
    with pytest.raises(ValueError):
        S.chart(None, "DOGE")


def test_the_account_chart_is_the_recorded_nights_against_the_yardsticks(monkeypatch, tmp_path):
    from jarvis.service import exposure, feed, officer
    j = _j_with_fills(tmp_path, [])
    officer._table(j)
    nights = {"2026-10-14": 497.75, "2026-10-15": 491.27, "2026-10-28": 452.03, "2026-11-10": 439.49}     # the note of day D follows the close of D-1
    for day, v in nights.items():
        j.db.execute("INSERT INTO officer_notes VALUES (?,?,?,?,?)", (day, 0, "note", json.dumps({"account": {"value_cad": v}}), 0.0))
    j.db.execute("INSERT INTO officer_notes VALUES (?,?,?,?,?)", ("2026-10-20", 0, "note", "not json", 0.0))   # a broken row is skipped, never guessed
    bars = _bars()
    monkeypatch.setattr(feed, "daily", lambda j, coin: bars)
    monkeypatch.setattr(S, "_book", lambda j: dict(BOOK))
    c = S.chart(j, "PORTFOLIO")
    ch = c["chart"]
    assert c["kind"] == "portfolio" and ch["dates"] == ["2026-10-10", "2026-10-13", "2026-10-14", "2026-10-27", "2026-11-09"]
    assert ch["yours"] == [500.0, 497.75, 491.27, 452.03, 439.49]            # the start, then each recorded night: nothing filled in between
    books = {b["book"]: b["return_pct"] for b in exposure.books(j)["books"]}
    assert ch["untouched"][-1] == round(500 * (1 + books["HOLD"] / 100), 2) and ch["nifty500"][-1] == round(500 * (1 + books["GATE50"] / 100), 2)   # one owner: exposure's books
    assert len(ch["untouched"]) == len(ch["nifty500"]) == 5 and all(isinstance(v, float) for v in ch["untouched"])
    assert c["lines"] == {"yours": "the book", "untouched": "Bitcoin held", "nifty500": "the hurdle"} and set(c["legend"]) == {"yours", "untouched", "nifty500"}
    assert c["x_labels"] == ["10 Oct", "9 Nov"] and c["as_of"] == "9 Nov close" and all(len(v) <= 20 for v in c["legend"].values())   # one line each on a phone
    assert c["words"].startswith("The $500 book stood at C$439.49 at the Mon 9 Nov close: −12.1% since it started with C$500 on Sun 11 Oct.")
    assert "Drawn from 4 recorded nights and the start." in c["words"] and "Under check" not in c["words"]
    # a correction written into the book with Madhav's yes is said under the chart: the nights before it were recorded without that money
    from jarvis.service import ndax_book
    ndax_book._put(j, "state", {"repairs": [{"day": "2026-11-10", "what": "a sale recorded late", "cash_added": 28.06}]})
    assert "Corrected on Tue 10 Nov: C$28.06 from a trade whose sale had not been recorded" in S.chart(j, "PORTFOLIO")["words"]
    # no nightly record yet: an empty chart that says so
    (tmp_path / "b").mkdir()
    e = S.account_chart(_j_with_fills(tmp_path / "b", []))
    assert e["chart"]["dates"] == [] and "nothing to draw yet" in e["words"]


def test_the_routes_answer_the_signed_in_owner_only(monkeypatch):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from jarvis.service import app as appmod, feed
    from tests.test_ask_ananta import _jarvis

    j, _ = _jarvis()
    monkeypatch.setattr(appmod, "_J", j)
    monkeypatch.setattr(appmod, "_JG", {})
    monkeypatch.setattr(appmod, "_A", {})
    bars = _bars()
    monkeypatch.setattr(feed, "daily", lambda j, coin: bars)
    c = TestClient(appmod.app)
    h = {"Authorization": f"Bearer {j.login('o@x.com', 'pw pw pw pw 1')}"}
    r = c.get("/v3/surface/chart/BTC", headers=h)
    assert r.status_code == 200 and r.json()["name"] == "Bitcoin" and len(r.json()["chart"]["closes"]) == 120, r.text
    assert c.get("/v3/surface/chart/DOGE", headers=h).status_code == 404
    assert c.get("/v3/surface/chart/BTC").status_code == 401, "signed in only"
    p = c.get("/v3/surface/chart/PORTFOLIO", headers=h)
    assert p.status_code == 200 and p.json()["kind"] == "portfolio" and "nothing to draw yet" in p.json()["words"], p.text   # a book not started yet
    t = c.get("/v3/surface/today", headers=h)                                 # the whole Today through the route, on a fresh test service
    assert t.status_code == 200 and t.json()["headline"] and [x["id"] for x in t.json()["tiles"]] == ["market", "account"], t.text
    assert all(card["points"] for card in t.json()["cards"])
    for name in ("money", "proof"):
        assert c.get(f"/v3/surface/{name}", headers=h).status_code == 200


# ---------------------------------------------------------------------------------------------------------------- display only; the app

def test_the_surfaces_only_read():
    src = (ROOT / "jarvis" / "service" / "surfaces.py").read_text()
    for banned in ("ndax_book.step", "_put(", "INSERT ", "UPDATE ", "DELETE ", "place_order", ".commit("):
        assert banned not in src, banned
    app = (ROOT / "jarvis" / "service" / "app.py").read_text()
    assert '@app.get("/v3/surface/chart/{name}")' in app


def test_the_app_draws_crypto_the_way_it_draws_india():
    charts = (APP / "src" / "newcharts.tsx").read_text()
    assert '"/v3/surface/chart"' in charts and all(f'key: "{k}"' in charts for k in ("BTC", "ETH", "SOL", "NIFTY", "BANKNIFTY"))
    assert "d?.lines" in charts and "d?.x_labels" in charts
    today = (APP / "app" / "new" / "today.tsx").read_text()
    assert "chartFor(p.label, mk, p.coin)" in today and "market={mk}" in today
    assert "openMoney(p.focus); }" not in today                              # crypto's boxes no longer skip the chart
    proof = (APP / "app" / "new" / "proof.tsx").read_text()
    assert "ex?.title ||" in proof
    assert "d.under_check" in (APP / "app" / "new" / "money.tsx").read_text()


# ---------------------------------------------------------------------------------------------------------------- the outsider's review, 10 Nov
# Madhav, 10 Nov 05:56 Toronto: "Ok, let's complete them" (fixes 1 to 6 and the strip list of claude/review-2026-11-10-outsider-crypto.md)

def test_the_note_reads_the_dial_afresh_and_knows_which_close_a_brake_fired_on(tmp_path, monkeypatch):
    from jarvis.service import exposure, ndax_book, officer
    j = _j_with_fills(tmp_path, [])
    j.now = lambda: 1793232361.0                                               # 29 Oct 2026, 00:06 UTC: the step on the 28 Oct candle
    ndax_book._put(j, "state", {"last_bar": 1793145600, "repairs": [{"day": "2026-10-28", "what": "a sale recorded late", "cash_added": 28.06}]})
    log = [{"day": "2026-10-22", "brake": "day_loss", "value": 484.69, "until": "2026-10-24"}, {"day": "2026-10-28", "brake": "day_loss", "value": 452.26, "until": "2026-10-30"}]
    monkeypatch.setattr(ndax_book, "status", lambda j: {"value_cad": 452.26, "cash_cad": 341.7, "return_pct": -9.55, "positions": {}, "closed": [],
                                                         "brakes": {"log": log}, "last_step": "2026-10-29 00:06", "started": "2026-10-11"})
    asked = []

    def state(j):
        asked.append(dict(exposure._CACHE))                                    # what was in hand when the note asked
        return {"dial_words": "OPEN: buying allowed", "why": ["Bitcoin closed 2026-10-28 at 80,000"], "as_of_day": "2026-10-28"}

    exposure._CACHE.update(t=9e18, v={"dial_words": "an answer kept from before the close"})
    monkeypatch.setattr(exposure, "state", state)
    f = officer.facts(j)
    assert asked[0]["v"] is None, "the note never reads a dial answer kept from before the close"
    assert f["dial"]["candle"] == f["dial"]["book_stepped_on"] == "2026-10-28" and "warning" not in f["dial"]
    assert f["account"]["brakes_today"].startswith("the day-loss brake fired at this close (no new buys until 2026-10-30)")   # it said "no brake fired today"
    assert f["account"]["corrections"] == [{"day": "2026-10-28", "what": "a sale recorded late", "cash_added": 28.06}]
    monkeypatch.setattr(exposure, "state", lambda j: {"dial_words": "CLOSED", "why": [], "as_of_day": "2026-10-27"})
    assert "different candle" in officer.facts(j)["dial"]["warning"]
    for must in ("never write that no brake fired", "do NOT close every note with its day", "A check with state OK is not a failure", "never\n\"caught\" as if it were a win"):
        assert must in officer.NOTE_RULES, must


def test_idle_cash_fails_only_when_something_may_buy(monkeypatch):
    from jarvis.service import discipline, ndax_book

    class _J:
        def now(self):
            return 1794269159.0

    state = {"value": 467.55, "cash": 467.55, "pos": {}, "cash_over_target_since": 1794269159 - 16 * 86400, "core_plan": {"state": "CLOSED", "cash_target": 0.7}}
    monkeypatch.setattr(ndax_book, "_get", lambda j, k, default=None: state)
    monkeypatch.setattr(ndax_book, "passed_rules", lambda j, dial: [])
    c = next(x for x in discipline.officer_checks(_J()) if x["id"] == "idle_cash")
    assert c["state"] == "OK" and "buying is off and no rule may trade, so cash is what the rules want" in c["words"]
    monkeypatch.setattr(ndax_book, "passed_rules", lambda j, dial: ["H07"])    # a rule may trade the closed dial: idle money is a fail again
    c = next(x for x in discipline.officer_checks(_J()) if x["id"] == "idle_cash")
    assert c["state"] == "FAIL" and "for 16 days" in c["words"]
    state["core_plan"]["state"] = "CONFIRMED"
    monkeypatch.setattr(ndax_book, "passed_rules", lambda j, dial: [])
    assert next(x for x in discipline.officer_checks(_J()) if x["id"] == "idle_cash")["state"] == "FAIL"   # buying is on: idle money fails


def test_a_parked_books_open_trades_run_to_their_exits_and_fill_nothing_new(tmp_path):
    from jarvis.service import watch_engine as W
    j = J(tmp_path)
    W._table(j)
    bars = _bars(120, "2026-11-09", 100.0)
    row = lambda i, status, k: {"id": i, "watch": "H07", "coin": "AAA", "source": "daily", "signal_t": bars[k - 1][0], "signal_day": W._day(bars[k - 1][0]),   # noqa: E731
                                "entry_t": bars[k][0] if status == "OPEN" else None, "entry_day": W._day(bars[k][0]) if status == "OPEN" else None,
                                "entry": bars[k][1] if status == "OPEN" else None, "stop": None, "status": status, "why": "test", "regime": None, "detail": "{}"}
    W._insert(j, row("old", "OPEN", -20))                                      # 20 days old against the rule's 10
    W._insert(j, row("unfilled", "WAITING", -1))
    daily = lambda jj, c: bars                                                 # noqa: E731
    W.run(j, watches=["RANDOM_10D"], coins=["AAA"], daily_fn=daily, live_trades=False)
    assert j.db.execute("SELECT status FROM evidence_trades WHERE id='old'").fetchone()[0] == "OPEN", "left out of the watches, it was left out of the exits too"
    W.run(j, watches=["RANDOM_10D"], coins=["AAA"], daily_fn=daily, live_trades=False, manage=["H07", "RANDOM_10D"])
    status, exit_day = j.db.execute("SELECT status, exit_day FROM evidence_trades WHERE id='old'").fetchone()
    assert status == "CLOSED" and exit_day <= W._day(bars[-10][0]), "closed by its own rule, on the rule's day, not today"
    assert j.db.execute("SELECT status FROM evidence_trades WHERE id='unfilled'").fetchone()[0] == "WAITING"   # a parked book fills nothing new


def test_the_book_check_watches_the_cash_the_value_and_the_notes_dial(tmp_path):
    from jarvis import selfcheck
    from jarvis.service import ndax_book, officer
    j = _j_with_fills(tmp_path, FILLS[2:3] + FILLS[4:5])                       # one Bitcoin buy and its sale
    officer._table(j)
    cash = 500 - (0.000563 * 113719.86 + 0.128) + (0.000563 * 108815.09 - 0.122)
    ndax_book._put(j, "state", {"cash": cash, "value": round(cash, 2), "pos": {}})
    j.db.execute("INSERT INTO officer_notes VALUES (?,?,?,?,?)", ("2026-11-10", 0, "n", json.dumps({"dial": {"candle": "2026-11-09", "book_stepped_on": "2026-11-09"}}), 0.0))
    j.db.commit()
    db = tmp_path / "jarvis.sqlite"
    assert selfcheck._book500(db) == []
    ndax_book._put(j, "state", {"cash": cash - 27.26, "value": round(cash, 2), "pos": {}})
    j.db.execute("UPDATE officer_notes SET facts=?", (json.dumps({"dial": {"candle": "2026-11-08", "book_stepped_on": "2026-11-09"}}),))
    j.db.commit()
    whats = [x["what"] for x in selfcheck._book500(db)]
    assert any("cash is C$" in w and "its trades add up to" in w for w in whats), whats
    assert any("value is C$" in w and "cash and holdings add up to" in w for w in whats), whats
    assert any("read the dial from the 2026-11-08 candle, but the book stepped on 2026-11-09" in w for w in whats), whats


def test_the_screens_after_the_review(monkeypatch, tmp_path):
    from jarvis.service import missed, ndax_book
    j = _fake_today(monkeypatch, tmp_path, book={**BOOK, "value_cad": 467.55, "cash_cad": 467.55, "return_pct": -6.5,
                                                 "graduation": {"passed": 3, "of": 10, "verdict": "NOT READY", "closed_trades": 9}})
    ndax_book._put(j, "state", {"repairs": [{"day": "2026-11-10", "what": "a sale recorded late", "cash_added": 28.06}]})
    note = next(c for c in S.today(j)["cards"] if c["kind"] == "note")
    assert note["points"][0] == "Corrected after this note was written: the account is C$467.55 (−6.5%), not the figure in the note"
    m = S.money(j)
    assert m["dial_block"]["graduation"] is None and "stop on NDAX" not in json.dumps(m) and "a real loss can be larger" in m["holdings_note"]
    monkeypatch.setattr(missed, "recent", lambda j, days: {"counts": {"CAUGHT": 11, "SEEN": 17, "MISSED": 1, "CAUGHT_TRADE_OK": 2},
                                                             "moves": [{"miss_class": "INTENTIONAL"}] * 9 + [{"miss_class": None}] * 20})
    p = S.proof(j)
    assert p["missed"]["words"] == ("In 7 days your ten main coins made 29 big moves. A paper book was in 11 of them (2 by a book allowed to trade, the rest by "
                                    "measuring books only); 17 were seen and not traded; 1 missed. 9 were held back on purpose while buying was off.")
    assert [c["name"] for c in p["clocks"]] == ["The evidence window (Rule A and B)", "Round trips in the $500 book"]
    assert S._pace(9, 50, "2026-10-11", dt.date(2026, 11, 10)) == "about Mar 2027 at this pace" and S._pace(0, 50, "2026-10-11", dt.date(2026, 11, 10)) == ""


def test_like_for_like_is_bitcoin_at_the_books_first_price(monkeypatch, tmp_path):
    from jarvis.service import ndax_book, officer
    j = _j_with_fills(tmp_path, FILLS[2:3])                                    # the book's first Bitcoin buy, at 113,719.86
    officer._table(j)
    for day, value, cash in (("2026-10-29", 500.0, 300.0), ("2026-10-30", 400.0, 400.0)):
        j.db.execute("INSERT INTO officer_notes VALUES (?,?,?,?,?)", (day, 0, "n", json.dumps({"account": {"value_cad": value, "cash_cad": cash}}), 0.0))
    monkeypatch.setattr(ndax_book, "instruments", lambda get=None: {"BTC": {"id": 1}})
    monkeypatch.setattr(ndax_book, "quote", lambda coin, inst, get=None: {"bid": 105000.0, "ask": 105300.0})
    S._LFL.update(t=0.0, words="")
    said = S.like_for_like(j)
    S._LFL.update(t=0.0, words="")
    assert said == ("Like for like (Bitcoin bought at the book's first price on NDAX and just held, in Canadian dollars): −7.9%. "
                    "The book had about 20% in coins on an average night. ")
