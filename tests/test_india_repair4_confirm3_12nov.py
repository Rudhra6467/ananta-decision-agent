"""12 Nov 2026, audit repair 4's third confirm check (~/ananta_runs/keen_audit/recheck/pkg4_confirm3.md), the records half:
E1, a trade that closes at its stop or its time exit (ATRSTOP, ORSTOP) was never tried again after a score with no option price or a
    short-day note, while its note and every sentence naming it promised a score;
E3, a trade scored with no option price counted among the book's trades while every total said it was not in its figures;
E5, the morning view said "2 left out until scored" when one of the two options had already expired.
Each check failed against the code before (4e66f80). No Kite, no live data: the candles, the plan and the ledgers are made here."""
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from india import morningview, ocstudy, readmodel, sp1paper  # noqa: E402
from tests.test_india_repair4_confirm_12nov import W3, W4, W5, _candles  # noqa: E402
from tests.test_india_sp1_scored_late_12nov import OPT, TOK, _world  # noqa: E402

FIRST = dt.date(2026, 11, 2)
FULL = range(ocstudy.NMIN)


def _decide_stop(root, tmp_path, monkeypatch, day: dt.date, prev: dt.date):
    """A long Bank Nifty trade at the open that closes the same day by its ATR stop or its time exit (action 6, ATRSTOP)."""
    (root / "decisions.jsonl").unlink()
    plan = tmp_path / f"plan_{day}.json"
    plan.write_text(json.dumps({"prev_date": prev.isoformat(), "index_tokens": TOK, "overnight": {"BANKNIFTY": {"atr14_prev": 600.0}},
                                "contracts": {"NIFTY": {"lot": 75}, "BANKNIFTY": {"lot": 35}}}))
    monkeypatch.setattr(sp1paper, "_plan_path", lambda d: plan)
    return sp1paper._append(root / "decisions.jsonl", {
        "kind": "decision", "date": day.isoformat(), "index": "BANKNIFTY", "point": "D0", "tradable": True, "entry_bar": 1, "fill_next_bar": 2,
        "decided_at": f"{day}T09:15:09+05:30", "choice": {"action": 6, "exit": "ATRSTOP", "dir": 1, "pred_net": 5.0},
        "contracts": {"option": dict(OPT)}})


def _no_price_first(tmp_path, monkeypatch):
    """A stop-exit trade on Tue 3 Nov, first scored that evening when Kite had no candles yet for its option."""
    root, _ = _world(tmp_path, monkeypatch, noted=False)
    whole = _candles({FIRST: FULL, W3: FULL, W4: FULL, W5: FULL}, FIRST)

    def no_option_on_w3(k, token, interval, a, b):
        df = whole(k, token, interval, a, b)
        return df[df["date"] != W3] if token == OPT["token"] else df
    monkeypatch.setattr(sp1paper, "_candles", lambda *a: no_option_on_w3(*a))
    _decide_stop(root, tmp_path, monkeypatch, W3, FIRST)
    sp1paper.score(day=W3, log=lambda s: None)
    rows = sp1paper._rows(root / "outcomes.jsonl")
    assert len(rows) == 1 and rows[0]["exit"] == "ATRSTOP" and "net_rs_realistic" not in rows[0]["legs"]["option"]
    monkeypatch.setattr(readmodel, "_today_ist", lambda: "2026-11-04", raising=False)
    return root, whole


def test_while_it_waits_for_its_option_price_a_trade_is_in_no_figure_of_the_book(tmp_path, monkeypatch):
    # E3 (S5): 13 trades and "not in these figures: 1 trade" read as 14
    root, _ = _no_price_first(tmp_path, monkeypatch)
    book = json.loads((root / "book.json").read_text())["by_index"]["BANKNIFTY"]
    assert book["trades"] == 0 and book["index_proxy_sum_bps"] == 0
    assert "Not in these figures: 1 trade with no result yet (BANKNIFTY Tue 3 Nov)" in readmodel.sp1("2026-11-03")["words"]


def test_a_stop_exit_trade_with_no_option_price_is_tried_again_and_scored_late(tmp_path, monkeypatch):
    # E1 (S4): only a next-open trade was tried again
    root, whole = _no_price_first(tmp_path, monkeypatch)
    monkeypatch.setattr(sp1paper, "_candles", lambda *a: whole(*a))                 # the next evening Kite has them
    sp1paper.score(day=W4, log=lambda s: None)
    rows = sp1paper._rows(root / "outcomes.jsonl")
    assert len(rows) == 2 and rows[1]["scored_late"] is True and "net_rs_realistic" in rows[1]["legs"]["option"]
    assert rows[1]["exit_day"] == "2026-11-03" and rows[1]["late_why"].startswith("Kite had no price for its option at the exit")
    book = json.loads((root / "book.json").read_text())["by_index"]["BANKNIFTY"]
    assert book["trades"] == 1 and book["scored_late"] == 1
    assert "Not in these figures" not in readmodel.sp1("2026-11-03")["words"]
    sp1paper.score(day=W5, log=lambda s: None)                                       # scored once: nothing more
    assert len(sp1paper._rows(root / "outcomes.jsonl")) == 2


def test_a_stop_exit_trade_noted_for_a_short_day_is_tried_again_once_its_day_is_whole(tmp_path, monkeypatch):
    # E1 (S4): the note says "it is tried again while its contract trades"; for a stop exit it never was
    root, _ = _world(tmp_path, monkeypatch, noted=False)
    short = [m for m in FULL if not 100 <= m < 135]
    monkeypatch.setattr(sp1paper, "_candles", lambda *a: _candles({FIRST: FULL, W3: short, W4: FULL, W5: FULL}, FIRST)(*a))
    _decide_stop(root, tmp_path, monkeypatch, W3, FIRST)
    sp1paper.score(day=dt.date(2026, 11, 6), log=lambda s: None)                    # three days on: noted once
    rows = sp1paper._rows(root / "outcomes.jsonl")
    assert len(rows) == 1 and rows[0]["note"] == "the day's minute bars are not complete on Kite; it is tried again while its contract trades"
    monkeypatch.setattr(sp1paper, "_candles", lambda *a: _candles({FIRST: FULL, W3: FULL, W4: FULL, W5: FULL}, FIRST)(*a))
    sp1paper.score(day=dt.date(2026, 11, 9), log=lambda s: None)                    # Kite has the whole day now
    rows = sp1paper._rows(root / "outcomes.jsonl")
    assert len(rows) == 2 and rows[1]["scored_late"] is True and rows[1]["exit"] == "ATRSTOP"
    assert rows[1]["late_why"].startswith("Its own day's minute bars were not complete on Kite when it was first scored")


def test_a_stop_exit_trade_noted_not_defined_is_still_not_tried_again(tmp_path, monkeypatch):
    # what stays as it was: only the next open can turn a 'not defined' note into a result (no Kite read for it)
    root, calls = _world(tmp_path, monkeypatch, noted=False)
    dec = _decide_stop(root, tmp_path, monkeypatch, W3, FIRST)
    sp1paper._append(root / "outcomes.jsonl", {"kind": "outcome", "date": "2026-11-03", "index": "BANKNIFTY", "point": "D0", "action": 6,
                                               "note": "the study's outcome is not defined for this day", "decision_hash": dec["hash"]})
    sp1paper.score(day=W5, log=lambda s: None)
    assert calls == [] and len(sp1paper._rows(root / "outcomes.jsonl")) == 1


def test_the_morning_view_says_which_left_out_trade_can_still_be_scored():
    # E5 (S5): on 20 Nov the 6 Nov trade (expiry 23 Nov) can still be scored and the 10 Nov trade (expiry 17 Nov) never can
    import unittest.mock as um
    mb = {"options_value_inr": 50000, "options_inr": 50000, "options_result_inr": 0, "options_trades": 0,
          "options_left_out": [{"date": "2026-11-06", "index": "BANKNIFTY", "expiry": "2026-11-23"},
                               {"date": "2026-11-10", "index": "NIFTY", "expiry": "2026-11-17"}]}
    with um.patch.object(morningview, "_today_ist", lambda: "2026-11-20"):
        assert morningview._options_words(mb).endswith("; 2 options trades left out: 1 until scored, 1 never scored, its option expired)")
    with um.patch.object(morningview, "_today_ist", lambda: "2026-11-13"):
        assert morningview._options_words(mb).endswith("; 2 options trades left out until scored)")
