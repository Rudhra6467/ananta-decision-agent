"""27 Nov 2026 (flag 231, the 23 Nov audit): the managed book's trial line leads with stocks and cash against the Nifty 500, keeps the
options lot apart, and names the parts of its record split at managed-v2 and managed-v3; its 60-session clock is unchanged."""
import datetime as dt

from india import trials

MB = {"start_day": "2026-10-30", "day": "2026-11-26", "value_inr": 283301, "return_pct": 76.51,
      "split": {"stocks_cash_inr": 2615, "stocks_cash_pct": 2.07, "options_inr": 120187, "market_pct": 10.0, "words": "x"},
      "clock": {"sessions": 6, "words": "Session 6 of 60 for the managed book; nothing is read into its result before session 60."},
      "plan": {"words": "No change for Friday 27 Nov."}}
DAYS = [dt.date(2026, 11, d) for d in (16, 17, 18, 20, 23, 25, 26)]


def test_lead_with_stocks_and_cash_and_name_the_parts():
    mb = dict(MB, start_day="2026-11-16")
    w = trials.managed_words(mb, DAYS, splits=[("managed-v2", "2026-11-17"), ("managed-v3", "2026-11-21")])
    assert w.startswith("Stocks and cash +2.1% (₹+2,615) against the Nifty 500 +10.0% over the same sessions; the options lot apart, +₹120,187;")
    assert "Its record is in 3 parts, split at each rule change: managed-v1 0 sessions; managed-v2 3 sessions from Tue 17 Nov; managed-v3 3 sessions from Mon 23 Nov." in w
    assert "Session 6 of 60" in w and w.endswith("No change for Friday 27 Nov.")


def test_the_splits_come_from_the_pins():
    s = dict(trials.managed_splits())
    assert s.get("managed-v2") == "2026-11-17" and s.get("managed-v3") == "2026-11-21"


def test_counts_left_out_when_they_do_not_add_up():
    w = trials.managed_words(dict(MB, clock={"sessions": 99, "words": ""}), DAYS, splits=[("managed-v3", "2026-11-21")])
    assert "split at each rule change: managed-v1; managed-v3 from Mon 23 Nov." in w


def test_no_split_words_keeps_the_book_words():
    assert trials.managed_words({"words": "old"}, DAYS) == "old"
