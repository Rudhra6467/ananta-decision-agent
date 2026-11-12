"""12 Nov 2026, the keen outside audit, audit repair 4 (open-list flag 120), G-01 (Madhav's yes of 12 Nov 01:52): the options line's 6 Nov
Bank Nifty trade is scored late at the next regular open and included. The ledger is append-only, so the trade then has two rows (its
note, then its late score): every reader takes one row per trade, says it was scored late, and stops saying it is left out. Each check
failed against the code before."""
import datetime as dt
import json

from jarvis.india import desk, livesession, views
from jarvis.india import places as IP
from jarvis.india import surfaces as IS
from tests.test_places_india import india  # noqa: F401  (the places fixture: fixed inputs, no live data)

DAY = (dt.date.today() - dt.timedelta(days=2)).isoformat()              # inside Activity's three weeks
OLD = (dt.date.today() - dt.timedelta(days=3)).isoformat()
SCORED = {"kind": "outcome", "date": OLD, "index": "BANKNIFTY", "point": "D2", "dir": -1, "exit": "ATRSTOP", "index_proxy": {"net_bps": -9.0},
          "legs": {"option": {"tradingsymbol": "BANKNIFTY26NOV59100PE", "lot": 30.0, "entry_realistic": 797.6, "exit": 602.4, "net_rs_realistic": -6053.6}}}
NOTE = {"kind": "outcome", "date": DAY, "index": "BANKNIFTY", "point": "D0", "action": 10,
        "note": "the study's outcome is not defined for this day (e.g. NEXTOPEN with no usable next session)"}
LATE = {"kind": "outcome", "date": DAY, "index": "BANKNIFTY", "point": "D0", "action": 10, "exit": "NEXTOPEN", "dir": 1, "scored_late": True,
        "late_why": "Its next open fell on Sun 8 Nov, which is no regular session, so it was first left without a result; it is scored at the "
                    "next regular open (Mon 9 Nov) and included, by Madhav's decision of 12 Nov 2026.",
        "index_proxy": {"net_bps": 80.0, "next_day": True},
        "legs": {"option": {"tradingsymbol": "BANKNIFTY26NOV57500CE", "lot": 35.0, "entry_realistic": 300.0, "exit": 1300.0, "net_rs_realistic": 34500.0,
                            "exit_rule": "next regular session's 09:16 open (Mon 9 Nov; Sun 8 Nov is no regular session)"}}}


def _ledger(india, rows):
    (india / "paper" / "sp1" / "outcomes.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_a_trade_scored_late_is_one_trade_marked_scored_late_and_no_longer_left_out(india, monkeypatch):
    _ledger(india, [SCORED, NOTE])
    assert [r["date"] for r in IS._sp1_unscored()] == [DAY]                              # before the late score: left out, and said
    _ledger(india, [SCORED, NOTE, LATE])
    assert IS._sp1_unscored() == []                                                       # it said "left out" beside a scored trade
    assert [r.get("scored_late", False) for r in IS._sp1_outcomes()] == [False, True]     # one row per trade
    page = IP.options_page()
    rows = next(p for p in page["parts"] if p.get("t") == "rows" and p.get("title") == "Trades on paper")
    assert rows["count"] == 2 and any("scored late" in str(r.get("sub")) for r in rows["rows"])     # it listed three, one "No result"
    assert "left out" not in json.dumps(page)
    monkeypatch.setattr(views, "options", lambda: {"capital_inr": 50000})
    pts = IP.option_points()
    assert pts[-1][1] == round(50000 - 6053.6 + 34500.0)                                 # counted once, at its own date
    did = json.dumps(IP.activity(), ensure_ascii=False)
    assert "Closed on paper, scored late" in did and "At the next regular open, scored late" in did


def test_the_voice_says_the_trade_left_out_and_then_its_late_score(india, monkeypatch):
    _ledger(india, [SCORED, NOTE])
    monkeypatch.setattr(views, "sp1_live", lambda rm=None: {"book": {"sessions": 12, "by_index": {}}})
    monkeypatch.setattr(views, "readmodel", lambda: {})
    card = desk.scorecard({}, {})
    assert "NOT in these figures: 1 trade left out" in card["options_line"]["note"]      # the voice's scorecard said nothing of it
    monkeypatch.setattr(livesession, "DATA", india)
    _ledger(india, [SCORED, NOTE, LATE])
    assert desk.scorecard({}, {})["options_line"]["note"].endswith("(the open trades are marked separately)")
    assert livesession._scored(DAY)[("BANKNIFTY", "D0")].get("scored_late") is True       # the score is said, not the note before it
