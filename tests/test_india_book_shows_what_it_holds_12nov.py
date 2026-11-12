"""12 Nov 2026, the keen outside audit, audit repair 4 (open-list flag 120). G-06: 'Your stocks' and Account headed with the paper book
(11 stocks) and listed the 14 real holdings under it (Jio Financial Rs 27,370 for the real 119 shares, where the book holds 14 shares,
Rs 3,220); the book's own positions were shown nowhere. G-17 (Madhav's yes of 12 Nov 01:52): a holding with no price study is "not
graded", said in words, never as a grade letter. Each check failed against the code before."""
from jarvis import placekit as K
from jarvis.india import places as IP
from jarvis.india import surfaces as IS
from tests.test_places_india import india  # noqa: F401  (the places fixture: fixed inputs, no live data)

OWN = [{"symbol": "TATAPOWER", "qty": 48, "last": 380.0, "value_inr": 18240, "source": "from the account", "pnl_pct": 24.0},
       {"symbol": "JIOFIN", "qty": 14, "last": 230.0, "value_inr": 3220, "source": "from the account", "pnl_pct": -11.5},
       {"symbol": "AJANTPHARM", "qty": 3, "last": 2600.0, "value_inr": 7800, "source": "replacement", "pnl_pct": 1.2}]
MARK = {"for_session": "2026-11-02", "symbol": "JIOFIN", "side": "SELL", "mark": "This sale was sized from your real account's 119 shares, not "
        "the book's 73: it sold 59 (81%) under halving it. Cuts are now sized from the book's own shares."}


def _book(monkeypatch):
    monkeypatch.setattr(IS, "_managed", lambda: {"start_inr": 160499, "start_day": "2026-10-30", "positions": 3, "day": "2026-11-11",
                                                 "holdings": [dict(x) for x in OWN], "marks": [dict(MARK)]})


def _rows(page, title):
    return next((p for p in page["parts"] if p.get("t") == "rows" and p.get("title") == title), None)


def test_the_account_lists_the_books_own_positions_under_its_own_total(india, monkeypatch):
    _book(monkeypatch)
    page = IP.account()
    mine = _rows(page, "In the managed book")
    assert mine and mine["count"] == 3 and [r["title"] for r in mine["rows"]][0] == IP._name("TATAPOWER")
    assert any(r["right"] == IP._rs(3220) and "14 shares" in r["sub"] for r in [IP.book_row(x) for x in OWN])
    split = next(p for p in page["parts"] if p.get("t") == "split")
    assert split["parts"][0]["label"] == "Stocks · 3"                       # one count: the book's own positions
    real = _rows(page, "Your Zerodha holdings")
    assert real is None or "as you have them" in real["sub"]                # the real holdings are labelled as his, apart
    assert _rows(page, "Your holdings") is None
    assert K.problems("account", page) == []


def test_your_stocks_shows_the_book_under_the_books_total_and_the_real_holdings_one_tap_away(india, monkeypatch):
    _book(monkeypatch)
    page = IP.stocks_page()
    mine = _rows(page, "In the managed book")
    assert mine and mine["count"] == 3
    assert _rows(page, "Your holdings") is None
    book = IP.book_page(OWN, [MARK])
    assert any(p.get("t") == "points" and "59 (81%)" in str(p) for p in book["parts"])   # the old wrong-size sale is said beside the rows
    assert K.problems("stocks", page) == []


def test_a_holding_not_graded_is_said_in_words_never_as_a_grade_letter():
    h = {"symbol": "KARURVYSYA", "grade": "not graded", "action": "HOLD", "value_inr": 3185, "pnl_pct": 386.0, "weight_pct": 2.7,
         "why": "Not graded: it is not among the 250 most-traded stocks, so Ananta has no price study on it and does not cut it.", "suggest_inr": 0}
    row = IP.holding_row(h)
    assert "grade" not in row and row["sub"].startswith("Not graded")
    page = IP.holding_page(h)
    pill = next(p for p in page["parts"] if p.get("t") == "pill")
    assert "NOT GRADED" not in str(page) and pill["text"].startswith("Not graded") and "why it is not graded" in page["pinned"]["ask"]
    assert IP.holding_row({**h, "grade": "B", "action": "HOLD"})["grade"] == "B"    # a graded holding keeps its letter


def test_a_holding_the_book_started_with_says_it_has_no_stop_and_leaves_by_its_grade():
    """G-21 (Madhav's yes: plainer words now; a stop rule waits for the review): each card printed 'Ananta is wrong if it closes under
    Rs X', which reads as a stop, while the eight holdings the book started with have none."""
    h = {"symbol": "LICI", "grade": "D", "action": "REDUCE", "value_inr": 20000, "weight_pct": 12.0, "suggest_inr": 10000,
         "why": "Weak (36/100): 6% below its long-term average.", "wrong_if": "it closes above Rs 940 on good volume"}
    pts = [p for p in IP.holding_page(h)["parts"] if p.get("t") == "points"]
    said = str(pts)
    assert "Ananta is wrong if" not in said and "not a stop" in said and "leaves only through its grade" in said
    assert IP.book_row(OWN[0])["sub"].endswith("no stop, leaves by its grade") and IP.book_row(OWN[2])["sub"].endswith("with a stop")


def test_every_options_total_says_the_trade_it_leaves_out(india, monkeypatch):
    """G-01 (Madhav's yes: score the 6 Nov Bank Nifty trade at the next regular open, marked scored late; until then the total says 'one
    trade left out'): the Options hero and 'By index' carried no caveat; only Proof's clock did."""
    monkeypatch.setattr(IS, "_sp1_unscored", lambda: [{"kind": "outcome", "date": "2026-11-06", "index": "BANKNIFTY", "note": "not defined"}])
    page = IP.options_page()
    hero = next(p for p in page["parts"] if p.get("t") == "hero")
    kv = next(p for p in page["parts"] if p.get("t") == "kv" and p.get("title") == "By index")
    assert "1 trade left out: Fri 6 Nov Bank Nifty, not scored yet" in hero["since"] and kv["foot"].startswith("1 trade left out")
    assert "one trade left out" in str(IP.account()) and "one trade left out" in str(IP.markets())
    monkeypatch.setattr(IS, "_sp1_unscored", lambda: [])
    assert "left out" not in str(IP.options_page())                                      # once it is scored, nothing is said
