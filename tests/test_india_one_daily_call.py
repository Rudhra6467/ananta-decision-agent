"""3 Nov 2026 (Madhav: "Yes for all", the Map's change 5): one daily call instead of five forecasters in the morning view's chances."""
from india import morningview as mv


def test_the_chances_speak_only_the_daily_call():
    rec = {"rule": {"n": 9, "hits": 4}, "reviewer": {"n": 5, "hits": 2}, "chronos": {"n": 5, "hits": 0}, "shadow": {"n": 1, "hits": 1}}
    w = mv._chances_words(rec, {"scored": 10, "hits": 4, "coin_flip_hits": 5}, {"BRK": {"closed": 3, "realised_inr": -1200}}, 7)
    assert w.startswith("The daily call has been right 4 of 10 sessions against 5 for a coin flip")
    for gone in ("rule forecast", "reviewer", "Chronos", "shadow trader"):
        assert gone not in w
    assert "options line has 7 sessions" in w and "not an edge" in w
    assert mv._chances_words(rec, {}, {}, 1).startswith("The daily call has no scored session yet")
