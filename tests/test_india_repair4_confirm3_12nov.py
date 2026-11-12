"""12 Nov 2026, audit repair 4's third confirm check (~/ananta_runs/keen_audit/recheck/pkg4_confirm3.md), the India app's side:
E2, a trade noted because its own day's minute bars were short was told, in the live session's words, that its next session was a
    special one;
E4, Account and Markets said "one trade left out" whatever the count, beside an Options page that said 2.
Each check failed against the code before (e9b81de). No live data: the files are made here."""
import json

from jarvis import placekit as K
from jarvis.india import places as IP
from jarvis.india import surfaces as IS
from tests.test_india_repair4_confirm_12nov import _folder
from tests import test_places_india as _places_india  # the places fixture: fixed inputs, no live data
india = _places_india.india          # 12 Nov: taken from the module, so the India firewall reads no import of the india package

_FIXTURES = (india,)

SHORT = {"kind": "outcome", "date": "2026-11-06", "index": "BANKNIFTY", "point": "D0", "action": 10,
         "note": "the day's minute bars are not complete on Kite; it is tried again while its contract trades"}


def test_a_trade_noted_for_a_short_day_is_given_that_reason(tmp_path, monkeypatch):
    # E2 (S5)
    from jarvis.india import livesession
    _folder(tmp_path)
    (tmp_path / "paper" / "sp1" / "outcomes.jsonl").write_text(json.dumps(SHORT) + "\n")
    (tmp_path / "paper" / "sp1" / "decisions.jsonl").write_text(json.dumps(
        {"kind": "decision", "date": "2026-11-06", "index": "BANKNIFTY", "point": "D0", "decided_at": "2026-11-06T09:15:09+05:30", "entry_estimate": 57400.0,
         "choice": {"dir": -1, "exit": "ATRSTOP"}, "contracts": {"option": {"expiry": "2026-11-23", "strike": 57500, "type": "PE", "lot": 35,
                                                                           "tradingsymbol": "BANKNIFTY26NOV57500PE"}}}) + "\n")
    monkeypatch.setattr(livesession, "DATA", tmp_path)
    monkeypatch.setattr(IS, "DATA", tmp_path)
    monkeypatch.setattr(livesession, "quotes", lambda symbols, fetch=None: {"rows": {}})
    monkeypatch.setattr(IS, "_today_ist", lambda: "2026-11-13", raising=False)
    clk = {"latest_session": "2026-11-06", "state": "closed", "today_india": "2026-11-13", "latest_session_words": "Fri 6 Nov"}
    x = livesession.options_today(clk)["taken"][0]
    assert "its own day's minute bars were not complete on Kite" in x["unscored"] and "special one" not in x["unscored"]


def test_account_and_markets_say_how_many_trades_are_left_out(india, monkeypatch):
    # E4 (S5)
    two = [{"kind": "outcome", "date": "2026-11-06", "index": "BANKNIFTY", "note": "not defined"},
           {"kind": "outcome", "date": "2026-11-10", "index": "NIFTY", "note": "not defined"}]
    monkeypatch.setattr(IS, "_sp1_unscored", lambda: [dict(r) for r in two])
    acc, mk = IP.account(), IP.markets()
    assert "2 trades left out" in str(acc) and "2 trades left out" in str(mk) and "one trade left out" not in str(acc) + str(mk)
    assert K.problems("account", acc) == [] and K.problems("markets", mk) == []
    monkeypatch.setattr(IS, "_sp1_unscored", lambda: [dict(two[0])])
    assert "one trade left out" in str(IP.account()) and "one trade left out" in str(IP.markets())
