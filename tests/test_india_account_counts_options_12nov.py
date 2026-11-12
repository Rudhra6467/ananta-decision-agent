"""12 Nov 2026, the keen outside audit, audit repair 4 (open-list flag 120), G-11 (Madhav's yes of 12 Nov 01:52): India's account total
counted the options money at the flat Rs 50,000 set aside, so the options line's result was in no account figure and no screen said so.
The managed book (the account on paper) now counts it at the line's own value: the money set aside plus the line's result on the trades
it decided after the book started (one row per trade), with a sentence; the benchmark rows written before are corrected once, marked,
so the chart does not jump. Each check failed against the code before. No live data: the book and the ledger are made here."""
import json

from india import account, managed as m

ROWS = [  # the options line's outcomes ledger: one trade before the book, one after, a note then its late score, one after the view's day
    {"kind": "outcome", "date": "2026-10-29", "index": "NIFTY", "index_proxy": {}, "legs": {"option": {"net_rs_realistic": 1000.0}}},
    {"kind": "outcome", "date": "2026-11-02", "index": "NIFTY", "index_proxy": {}, "legs": {"option": {"net_rs_realistic": 3000.0}}},
    {"kind": "outcome", "date": "2026-11-06", "index": "BANKNIFTY", "note": "the study's outcome is not defined for this day"},
    {"kind": "outcome", "date": "2026-11-06", "index": "BANKNIFTY", "index_proxy": {}, "scored_late": True, "legs": {"option": {"net_rs_realistic": 30000.0}}},
    {"kind": "outcome", "date": "2026-11-11", "index": "NIFTY", "index_proxy": {}, "legs": {"option": {"net_rs_realistic": -500.0}}}]
BOOK = {"start_day": "2026-10-30", "start_inr": 160000.0, "positions": {"TATAPOWER": {"qty": 100, "avg": 380.0, "last": 400.0, "source": "twin", "entered": "2026-10-22"}},
        "cash_inr": 70000.0, "options_inr": 50000.0, "trades": [], "costs_inr": 0.0}
C = {"judge_after_sessions": 60, "version": "managed-v1"}


def _world(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    (tmp_path / "paper" / "sp1").mkdir(parents=True)
    (tmp_path / "paper" / "sp1" / "outcomes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in ROWS))
    monkeypatch.setattr(m, "holidays", lambda: set())


def test_the_account_counts_the_options_line_at_its_own_value_and_says_so(tmp_path, monkeypatch):
    _world(tmp_path, monkeypatch)
    v = m.view(json.loads(json.dumps(BOOK)), "2026-11-10", None, [], C)
    assert v["options_result_inr"] == 33000 and v["options_trades"] == 2          # after the start, up to the view's day, the late score once
    assert v["value_inr"] == 40000 + 70000 + 50000 + 33000 and v["options_value_inr"] == 83000
    assert v["return_pct"] == round(100 * ((40000 + 70000 + 50000 + 33000) / 160000 - 1), 2)
    assert v["options_counted"] == "Options count at ₹50,000 set aside and +₹33,000 from 2 trades since the book began (30 Oct)."
    assert len(v["options_counted"].split()) <= 22                                       # a screen's line
    assert v["options_counted"] in v["words"] and m.OPEN_LOT in v["words"] and v["options_inr"] == 50000   # set aside, still said apart
    assert v["options_left_out"] == []


# ---- 12 Nov 2026, the outside check of repair 4 (N4, N5, N7): one meaning, the lot open at the start, a row counts what was known ----
SCORED = [  # as the live ledger writes them: each scored row carries the moment it was scored (IST), the evening of its exit
    {"kind": "outcome", "date": "2026-10-29", "index": "BANKNIFTY", "scored_at": "2026-10-30T16:30:00+05:30", "index_proxy": {"next_day": True},
     "legs": {"option": {"net_rs_realistic": -2000.0}}},                                  # closed at the 30 Oct open: before the book
    {"kind": "outcome", "date": "2026-10-30", "index": "BANKNIFTY", "scored_at": "2026-11-02T17:30:00+05:30", "index_proxy": {"next_day": True},
     "legs": {"option": {"net_rs_realistic": 429.0}}},                                    # open at the book's first close, sold at the 2 Nov open
    {"kind": "outcome", "date": "2026-11-02", "index": "NIFTY", "scored_at": "2026-11-03T17:30:00+05:30", "index_proxy": {"next_day": True},
     "legs": {"option": {"net_rs_realistic": 5000.0}}},                                   # decided 2 Nov, its result known on 3 Nov
    {"kind": "outcome", "date": "2026-11-06", "index": "BANKNIFTY", "note": "the study's outcome is not defined for this day"}]


def test_the_lot_open_at_the_start_counts_whole_and_a_row_counts_what_was_known_that_day(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    (tmp_path / "paper" / "sp1").mkdir(parents=True)
    (tmp_path / "paper" / "sp1" / "outcomes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in SCORED))
    ol = m.options_line("2026-10-30")
    assert ol["result_inr"] == 5429 and ol["trades"] == 2                              # the 30 Oct lot counts; the 29 Oct trade does not
    assert m.options_line("2026-10-30", "2026-11-02")["result_inr"] == 429              # 2 Nov's row: the 2 Nov trade was not known yet
    assert m.options_line("2026-10-30", "2026-11-03")["result_inr"] == 5429
    assert ol["left_out"] == [{"date": "2026-11-06", "index": "BANKNIFTY"}]
    words = m.options_words(50000.0, ol, "2026-10-30")
    assert words == "Options count at ₹50,000 set aside and +₹5,429 from 2 trades since the book began (30 Oct); 1 trade left out."
    assert len(words.split()) <= 22
    rows = [{"day": "2026-11-02", "managed_inr": 159000, "managed_start_day": "2026-10-30", "start_inr": 160499, "frozen_inr": 158000}]
    account.count_options(rows, 160000.0)
    assert rows[0]["managed_options_inr"] == 429                                         # counted the way a row written that night counts it
    from india import morningview
    mb = {"options_value_inr": 55429, "options_inr": 50000, "options_result_inr": 5429, "options_trades": 2, "options_left_out": ol["left_out"]}
    assert morningview._options_words(mb) == ("₹55,429 in options at the options line's own value (₹50,000 set aside and +₹5,429 from 2 trades "
                                              "since the book began; 1 options trade left out until scored)")


def test_the_benchmark_rows_written_before_count_it_once_marked(tmp_path, monkeypatch):
    _world(tmp_path, monkeypatch)
    rows = [{"day": "2026-11-02", "managed_inr": 159000, "managed_start_day": "2026-10-30", "start_inr": 160499, "frozen_inr": 158000},
            {"day": "2026-11-09", "managed_inr": 161000, "managed_start_day": "2026-10-30", "start_inr": 160499, "frozen_inr": 158500},
            {"day": "2026-11-10", "managed_inr": 194000, "managed_options_inr": 33000, "managed_start_day": "2026-10-30", "start_inr": 160499}]
    assert account.count_options(rows, 160000.0) == 2
    assert [r["managed_inr"] for r in rows] == [159000 + 3000, 161000 + 33000, 194000]       # each through its own day; the new row as it is
    assert rows[1]["managed_options_inr"] == 33000 and "G-11" in rows[1]["managed_options_note"]
    assert rows[1]["managed_ret_pct"] == round(100 * (194000 / 160000 - 1), 2)
    assert rows[1]["managed_minus_frozen_pct"] == round(100 * (194000 - 158500) / 160499, 2)
    assert account.count_options(rows, 160000.0) == 0 and rows[0]["managed_inr"] == 162000   # once
