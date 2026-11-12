"""12 Nov 2026, the keen outside audit, audit repair 4 (open-list flag 120), G-11 (Madhav's yes of 12 Nov 01:52): the India account total
counts the options money at the options line's own value, with a sentence. The managed book's view works the number out (records
india/managed.py, one place); here the screens: the parts of "Where it sits" make the total, Home's Options box shows the same, and the
sentence is on Account and Options. Each check failed against the code before."""
import json

from jarvis import placekit as K
from jarvis.india import places as IP
from jarvis.india import surfaces as IS
from tests.test_places_india import MONEY, india  # noqa: F401  (the places fixture: fixed inputs, no live data)

_FIXTURES = (india,)                                                                     # the places fixture, used by name below

SAID = "Options count at ₹50,000 set aside and +₹33,000 from 2 trades since the book began (30 Oct)."


def _money(monkeypatch):
    mo = json.loads(json.dumps(MONEY))
    mo.update({"value_inr": 87111 + 83000 + 27614, "options_value_inr": 83000, "options_result_inr": 33000, "options_counted": SAID})
    monkeypatch.setattr(IS, "money", lambda full=True: json.loads(json.dumps(mo)))
    return mo


def test_where_it_sits_makes_the_total_with_the_options_line_at_its_own_value(india, monkeypatch):
    mo = _money(monkeypatch)
    page = IP.account()
    split = next(p for p in page["parts"] if p.get("t") == "split")["parts"]
    assert split[1]["label"] == "Options, since the book began" and split[1]["value"] == IP._rs(83000)       # it said "set aside", ₹50,000
    hero = next(p for p in page["parts"] if p.get("t") == "hero")
    assert hero["value"] == IP._rs(mo["value_inr"]) == IP._rs(87111 + 83000 + 27614)                       # the three parts make it
    assert any(p.get("t") == "line" and p.get("text") == SAID for p in page["parts"])
    home = IP.home()
    box = next(p for p in home["parts"] if p.get("t") == "boxes")["items"][1]["pages"][1]
    assert box["value"] == IP._rs(83000) and box["caption"] == "Since the book began"
    assert any(p.get("t") == "line" and p.get("text") == SAID for p in IP.options_page()["parts"])
    assert K.problems("account", page) == [] and K.problems("home", home) == [] and K.problems("options", IP.options_page()) == []
