"""3 Nov 2026 (Madhav: "Yes for all", the Map's change 5): one daily call instead of five forecasters in the morning view's chances."""
from india import morningview as mv


def test_the_chances_speak_only_the_daily_call():
    rec = {"rule": {"n": 9, "hits": 4}, "reviewer": {"n": 5, "hits": 2}, "chronos": {"n": 5, "hits": 0}, "shadow": {"n": 1, "hits": 1}}
    w = mv._chances_words(rec, {"scored": 10, "hits": 4, "coin_flip_hits": 5}, {"BRK": {"closed": 3, "realised_inr": -1200}}, 7)
    # 24 Nov 2026 (Madhav, in the app, flag 236): the daily call itself is now off the morning view too; it is recorded in the background
    assert w.startswith("The research book has closed 3 practice trades")
    for gone in ("rule forecast", "reviewer", "Chronos", "shadow trader", "daily call"):
        assert gone not in w
    assert "options line has 7 sessions" in w and "not an edge" in w
    assert mv._chances_words(rec, {}, {}, 1).startswith("The options line has 1 session on record")


def test_the_morning_view_says_what_it_cannot_see_overnight():
    # 3 Nov (outside trader grade): no GIFT Nifty, a day-old US close, lagging crude and rupee
    w = mv.blind_spots("2026-11-02")
    assert "US close on file is for 2026-11-02" in w and "GIFT Nifty could not be read" in w and "09:09 IST pre-open read" in w
    # 9 Nov: with GIFT Nifty read, the view no longer says it has no overnight read
    g = mv.blind_spots("2026-11-09", {"words": "GIFT Nifty ... is up 0.4%"})
    assert "could not be read" not in g and "GIFT Nifty above" in g and "no live Asian markets" in g
