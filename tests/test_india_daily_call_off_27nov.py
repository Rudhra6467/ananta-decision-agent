"""27 Nov 2026 (flag 236; Madhav's yes in the app, 24 Nov): the daily call is off the read model's brief and the morning view's words;
it is still recorded and scored (the read model's "call" section and the morning view's scorecard keep it)."""
from india import morningview as mv
from india import readmodel as R


def _rm():
    return {"market": {"status": "ok", "data_through": "2026-11-26", "nifty_close": 26000.0, "words": "an uptrend"},
            "call": {"status": "ok", "call": "BULLISH", "words": "Daily call for the next session: BULLISH (mechanical rule x); so far 8 of 23 calls right"},
            "stock_book": {"status": "missing"}, "decisions_today": {"status": "missing"}, "sp1": {"status": "missing"}, "learning": {}, "missing": []}


def test_the_brief_does_not_speak_the_call():
    rm = _rm()
    b = R.brief(rm)
    assert b and b[0].startswith("Through 2026-11-26")
    assert not any("Daily call" in x for x in b)
    assert rm["call"]["call"] == "BULLISH"


def test_the_morning_view_chances_and_lessons_leave_it_out():
    w = mv._chances_words({}, {"scored": 23, "hits": 8, "coin_flip_hits": 14}, {}, 22)
    assert "daily call" not in w.lower() and w.startswith("The options line has 22 sessions on record")
    sc = {"forecasts": {"rule": {"n": 0, "hits": 0}}, "daily_call": {"scored": 23, "hits": 8, "coin_flip_hits": 14}, "options_sessions": 22}
    les = mv.lessons_for_writer(sc, {"lessons": []})
    assert les[0].startswith("Do not mention the daily call") and not any("behind the coin flip" in x for x in les)
