"""3 Nov 2026: the trader's desk (india/desk.py), from Madhav's chat and the outside trader's grade."""
import datetime as dt
import gzip
import json

from india import desk


def test_dates_in_the_filing_text():
    t = "The meeting of the Board is scheduled on Wednesday, November 04, 2026 to consider the results for the quarter ended 30th September 2026"
    assert desk.dates_in(t) == {dt.date(2026, 11, 4), dt.date(2026, 9, 30)}
    assert dt.date(2026, 11, 5) in desk.dates_in("board meeting will be held on 05-11-2026")


def test_kinds():
    assert desk.kind_of("Outcome of Board Meeting", "approved the financial results for the quarter") == "results"
    assert desk.kind_of("Analysts/Institutional Investor Meet/Con. Call Updates", "audio recording of the earnings conference call") == "analyst_call"
    assert desk.kind_of("Dividend", "declared interim dividend") == "corporate_action"


def test_news_and_results_ahead_from_the_feed(tmp_path):
    rows = [{"symbol": "MARICO", "desc": "General Updates", "an_dt": "02-Nov-2026 15:43:00",
             "attchmntText": "earnings presentation on the financial results of the Company, enclosed"},
            {"symbol": "PETRONET", "desc": "Board Meeting Intimation", "an_dt": "28-Oct-2026 10:00:00",
             "attchmntText": "A meeting of the Board is scheduled to be held on November 4, 2026 to consider and approve the financial results for the quarter ended September 30, 2026"},
            {"symbol": "X", "desc": "Outcome of Board Meeting", "an_dt": "26-Oct-2026 16:00:00", "attchmntText": "meeting held today, i.e. on October 26, 2026, approved the financial results"}]
    f = tmp_path / "20261102.json.gz"
    f.write_bytes(gzip.compress(json.dumps(rows).encode()))
    news, meets = desk.news([f])
    assert news["MARICO"][0]["kind"] == "results" and news["MARICO"][0]["at"] == "2026-11-02 15:43"
    assert meets["PETRONET"] == ["2026-11-04"]                      # the quarter's end date is not a meeting date
    assert "X" not in meets                                        # an outcome is not a meeting ahead


def test_movers_explain_with_a_filing_or_say_none():
    qb = {"as_of": "2026-11-02", "quotes": {"A": {"symbol": "A", "chg_1d": 0.12, "avg_turnover_20d_cr": 50, "kind": "stock"},
                                            "B": {"symbol": "B", "chg_1d": -0.08, "avg_turnover_20d_cr": 50, "kind": "stock"},
                                            "C": {"symbol": "C", "chg_1d": 0.30, "avg_turnover_20d_cr": 1, "kind": "stock"}}}
    m = desk.movers(qb, {"A": [{"at": "2026-11-02 15:00", "kind": "order", "what": "Order", "text": "won an order"}]}, n=2)
    assert [r["symbol"] for r in m["up"]][:1] == ["A"] and m["up"][0]["why"].startswith("Order")
    assert m["down"][0]["symbol"] == "B" and m["down"][0]["why"].startswith("no company filing")
    assert all(r["symbol"] != "C" for r in m["up"])                # illiquid names are left out
