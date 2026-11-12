"""12 Nov 2026, the keen outside audit (G-08; open-list flag 118): the morning view spoke the folded-away account twin as the paper account
(Rs 167,641 in 13 stocks) while Home's paper account is the managed book (Rs 1,64,725, 11 stocks). The morning view now names the managed
book, at the close it is marked at."""
import json

from india import kite
from india import morningview as mv


def _files(tmp_path, managed: dict | None):
    (tmp_path / "paper" / "account").mkdir(parents=True)
    (tmp_path / "paper" / "account" / "view.json").write_text(json.dumps({"words": "₹167,641 on paper: ₹90,756 in 13 stocks, ₹50,000 set aside "
                                                                                    "for options, ₹26,885 cash. 10 paper trades so far."}))
    if managed is not None:
        (tmp_path / "paper" / "managed").mkdir(parents=True)
        (tmp_path / "paper" / "managed" / "view.json").write_text(json.dumps(managed))


def test_the_morning_views_paper_account_is_the_managed_book(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(kite, "_read_token", lambda: None)                    # never the real sign-in file
    _files(tmp_path, {"value_inr": 164725, "stocks_inr": 87111, "options_inr": 50000, "cash_inr": 27614, "positions": 11, "day": "2026-11-09",
                      "start_day": "2026-10-30", "return_pct": 2.63, "plan": {}})
    w = mv.plan_today("2026-11-11", {"data_through": "2026-11-09"})["account_words"]
    assert w.startswith("The paper account (the managed book): ₹164,725 at the 9 Nov close")
    assert "11 stocks" in w and "+2.63% since 30 Oct" in w
    assert "167,641" not in w and "13 stocks" not in w and "trades so far" not in w


def test_with_no_managed_value_it_says_so_and_never_borrows_the_twins_words(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(kite, "_read_token", lambda: None)
    _files(tmp_path, None)
    w = mv.plan_today("2026-11-11", {"data_through": "2026-11-09"})["account_words"]
    assert w == "The managed book, the paper account, has no value yet."
