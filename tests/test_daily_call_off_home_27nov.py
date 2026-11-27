"""27 Nov 2026 (flag 236; Madhav's yes in the app, 24 Nov 07:08 Toronto): the daily call is off the Home screen (the decision card and the
account's 'why' lines); it is still recorded and scored in the background, so the read model keeps it."""
from jarvis.india import views

RM = {"data_through": "2026-11-26", "next_session": "2026-11-27", "market": {"trend_state": "above_both", "nifty_close": 26000, "data_through": "2026-11-26"},
      "call": {"call": "BULLISH", "data_through": "2026-11-26", "hits": 8, "scored": 23, "null_hits": 14}, "sp1": {"status": "ok"}}


def test_the_home_card_does_not_speak_the_call():
    assert not any("call" in x.lower() or "coin flip" in x.lower() for x in views.plain_brief(RM))


def test_the_account_why_lines_do_not_speak_the_call():
    a = views._account_sp1(RM)
    assert not any("call" in str(x).lower() for x in a["dial"]["why"])
    assert "call" not in a["note"]["note"].lower()


def test_the_call_is_still_recorded():
    assert RM["call"]["scored"] == 23            # nothing here deletes or rewrites the record; only the screens stop reading it
