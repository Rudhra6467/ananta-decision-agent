"""Flag 233 (audit 23 Nov, S2/S3): the practice book's open trades were said three ways (141, 227, 258), and IA79 said "141 open trades ...
which counts the 4 new ones" while the Rs -5,411 of the 4 picks bought at the open was added on top. The facts name each count once, and the
practice_today words say the picks are apart from the held trades."""
import json

from jarvis.india import ask
from jarvis.india import livesession as L
from tests.test_india_livesession import AT_0608_TORONTO, _quote_stub

SB = {"open_positions": 258,
      "closed_vs_open": {"total": {"closed": {"n": 107}, "open": {"n": 227}}, "by_family": {"CTL": {"open": {"n": 86}}, "BRK": {"open": {"n": 58}}}}}


def test_each_count_is_named_once():
    c = ask.open_counts(SB)
    assert (c["all_positions"], c["reference_exit_open"], c["reference_exit_own_picks"], c["reference_exit_random_picks"]) == (258, 227, 141, 86)
    w = c["words"]
    assert "258 open positions in all" in w and "227 open on the reference exit (hold 20 days): 141 of Ananta's own picks and 86 random" in w
    assert "never add two counts" in c["say_it"] and "inside the held count" in c["say_it"]
    assert not any(ch.isdigit() for ch in c["say_it"])          # no example number that the number check could take for a fact


def test_counts_missing_say_nothing():
    assert ask.open_counts({})["words"] is None


def test_practice_today_keeps_the_picks_apart(tmp_path):
    (tmp_path / "decisions").mkdir()
    st = {"trades": {"a": {"book": "exec", "policy": "hold_20d", "status": "open", "campaign": "BRK", "symbol": "TCS", "entry_adj": 2900.0,
                           "last_close_adj": 3000.0, "last_date": "2026-10-30", "notional": 50000.0}},
          "decisions": {"2026-10-30": {"status": "pending"}}}
    (tmp_path / "state.json").write_text(json.dumps(st))
    (tmp_path / "decisions" / "2026-10-30.json").write_text(json.dumps({"signals": [{"symbol": "TCS", "campaign": "PULL"}]}))
    p = L.practice_today(L.clock("2026-10-30", AT_0608_TORONTO), _quote_stub, path=tmp_path / "state.json")
    w = p["words"]
    assert "its 1 open trades from earlier sessions" in w
    assert "(the 1 picks are not among the 1 trades from earlier sessions; the two moves add to the total)" in w
    total = p["held_move_inr"] + p["picks_move_inr"]
    assert f"about Rs {abs(total):,}" in w
