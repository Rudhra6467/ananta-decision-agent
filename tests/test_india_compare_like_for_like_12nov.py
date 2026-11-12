"""12 Nov 2026, the keen outside audit, audit repair 4 (open-list flag 120), G-12: 'How it compares' was not like for like twice over. The
first benchmark row, labelled 29 Oct, was written after the 30 Oct close and holds that close's prices (the managed book's own start),
while its Nifty 500 runs to 29 Oct; the foot said all three start at the 29 Oct close. And books that are about half and two thirds in
stocks were set against an index that is all stocks, so your untouched holdings looked behind when, stock for stock, they were ahead.
The rows here are shaped like the real ones. Each check failed against the code before."""
import json

from jarvis import placekit as K
from jarvis.india import compare
from jarvis.india import places as IP
from jarvis.india import surfaces as IS
from tests.test_places_india import MONEY, india  # noqa: F401  (the places fixture: fixed inputs, no live data)

ROWS = [{"day": "2026-10-29", "frozen_inr": 160536, "twin_inr": 160499, "nifty500_ret_pct": 1.13},
        {"day": "2026-10-30", "frozen_inr": 163076, "managed_inr": 160558, "managed_ret_pct": 0.04, "nifty500_ret_pct": 0.92},
        {"day": "2026-11-11", "frozen_inr": 170014, "managed_inr": 165234, "managed_ret_pct": 2.95, "nifty500_ret_pct": 9.6, "managed_sessions": 8}]


def _data(tmp_path):
    (tmp_path / "paper" / "account").mkdir(parents=True, exist_ok=True)
    (tmp_path / "paper" / "managed").mkdir(parents=True, exist_ok=True)
    (tmp_path / "paper" / "account" / "view.json").write_text(json.dumps({"benchmark": {"managed_start_day": "2026-10-30", "managed_sessions": 8}}))
    (tmp_path / "paper" / "account" / "benchmark.jsonl").write_text("".join(json.dumps(r) + "\n" for r in ROWS))
    (tmp_path / "paper" / "account" / "frozen.json").write_text(json.dumps({"day": "2026-10-22", "cash_inr": 17500.0, "options_inr": 34000.0}))
    (tmp_path / "paper" / "managed" / "view.json").write_text(json.dumps({"stocks_inr": 87111, "value_inr": 165234}))
    return tmp_path


def test_all_three_lines_count_from_the_managed_books_start_close_and_say_how_much_is_in_stocks(tmp_path):
    sw = compare.same_window(_data(tmp_path))
    assert sw["since"] == "2026-10-30" and sw["since_words"] == "30 Oct"                  # it said the 29 Oct close
    assert sw["nifty500_pct"] == round(((1 + 9.6 / 100) / (1 + 0.92 / 100) - 1) * 100, 2)  # the index from the 30 Oct close, not 29 Oct
    assert sw["yours_pct"] == round((170014 / 160536 - 1) * 100, 2)                       # the holdings' 30 Oct prices, as before
    e = sw["exposure"]
    assert e["managed_stock_pct"] == 53 and e["yours_stock_pct"] == round(100 * (170014 - 51500) / 170014)
    assert e["yours_stock_for_stock_pct"] == round(((170014 - 51500) / (160536 - 51500) - 1) * 100, 2)
    assert "Not equally in stocks" in sw["words"] and "stock for stock" in sw["exposure_words"]
    assert K.nwords(sw["exposure_words"]) <= K.MAX["page_line"]                           # it goes on the Account page as a line


def test_the_account_page_says_it_under_how_it_compares(india, monkeypatch):
    sw = compare.same_window(_data(india))
    mo = json.loads(json.dumps(MONEY))
    mo.update({"books_exposure": sw["exposure_words"], "clock": {"sessions": 8, "of": 60, "words": "Session 8 of 60", "since": sw["since"]}})
    monkeypatch.setattr(IS, "money", lambda full=True: json.loads(json.dumps(mo)))
    page = IP.account()
    kv = next(p for p in page["parts"] if p.get("t") == "kv" and p.get("title") == "How it compares")
    assert kv["foot"].startswith("All from the Fri 30 Oct close.")
    assert any(p.get("t") == "line" and p.get("text") == sw["exposure_words"] for p in page["parts"])
    assert K.problems("account", page) == []
