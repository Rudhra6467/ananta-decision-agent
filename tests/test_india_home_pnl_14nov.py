"""14 Nov 2026 (Madhav: "where is the profit or loss number? We want to see how we made in stocks and options"): Home's second box carries
four pages (In stocks, Options, Stocks P&L, Options P&L); the two P&L figures add up to the hero's change; a trade scored after the last
close is said apart and is not in the figure; a guest sees neither."""
from jarvis import placekit as K
from jarvis.india import places as P
from jarvis.india import surfaces as IS


def _trade(date, net, scored):
    return {"date": date, "index": "NIFTY", "scored_at": scored + "T10:00:00+05:30", "legs": {"option": {"net_rs_realistic": net}}}


BOOK = {"day": "2026-11-13", "start_day": "2026-10-30", "start_inr": 160000, "value_inr": 171000, "stocks_inr": 90000, "cash_inr": 21000,
        "options_inr": 50000, "options_result_inr": 10000, "options_value_inr": 60000, "costs_inr": 200.0, "positions": 3, "holdings": []}
TRADES = [_trade("2026-10-29", 5000, "2026-10-30"),            # decided before the book started: not counted
          _trade("2026-11-02", 13000, "2026-11-03"), _trade("2026-11-05", -3000, "2026-11-06"),
          _trade("2026-11-06", 9000, "2026-11-14")]            # scored after the 13 Nov close: joins at the next close


def _patch(monkeypatch, book=BOOK):
    monkeypatch.setattr(IS, "_managed", lambda: dict(book))
    monkeypatch.setattr(IS, "_sp1_outcomes", lambda: list(TRADES))
    monkeypatch.setattr(P, "stock_return", lambda values=None: [("2026-10-30", 0.0), ("2026-11-13", 1.2)])


def test_the_two_parts_add_up_to_the_change(monkeypatch):
    _patch(monkeypatch)
    p = P.pnl_now()
    assert p["counted"] and p["options"] == 10000 and p["stocks"] == 1000
    assert p["stocks"] + p["options"] == p["total"] == 11000


def test_the_window_and_the_late_trade(monkeypatch):
    _patch(monkeypatch)
    counted, later = P.option_pnl_trades()
    assert [r["date"] for r in counted] == ["2026-11-02", "2026-11-05"]
    assert [r["date"] for r in later] == ["2026-11-06"]
    assert P.option_pnl_points() == [("2026-10-30", 0.0), ("2026-11-03", 13000), ("2026-11-06", 10000)]


def test_not_counted_yet_is_worked_out_and_said(monkeypatch):
    book = {k: v for k, v in BOOK.items() if k not in ("options_result_inr", "options_value_inr")}
    _patch(monkeypatch, book)
    p = P.pnl_now()
    assert not p["counted"] and p["options"] == 10000 and p["stocks"] == 11000


def test_pages_keep_the_rules_and_have_ask(monkeypatch):
    _patch(monkeypatch)
    for name in ("stocks_pnl", "options_pnl"):
        pg = P.PLACES[name](full=True)
        assert K.problems(name, pg) == []
        assert (pg.get("pinned") or {}).get("ask")
    lines = [x.get("text") for x in P.options_pnl_page()["parts"] if x.get("t") == "line"]
    assert any("joins at the next close" in str(t) for t in lines)


def test_guest_cannot_open_them():
    assert "stocks_pnl" not in P.GUEST_PLACES and "options_pnl" not in P.GUEST_PLACES
