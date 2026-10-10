"""Madhav's people, introduce mode, the Telugu voice switch, the research desk's rules (Oct 10, 2026)."""
import json

from tests.test_universe_live import J

PEOPLE = {"rules": ["Paper only."], "telugu_guide": {"respect": "meeru, andi, garu", "mix": "mix", "words": {"andi": "polite"}},
          "people": [{"id": "mom", "names": ["Lakshmi", "Mom"], "relation": "mother", "group": "family", "tz": "Asia/Kolkata",
                      "language": "telugu", "call": "Lakshmi garu", "opener": "Hello andi Lakshmi garu.. namaskaram."},
                     {"id": "dad", "names": ["Prasad", "Dad"], "relation": "father", "language": "telugu", "opener": "Good {part} sir."},
                     {"id": "bil", "names": ["Ravi Kumar"], "relation": "brother-in-law", "language": "english", "opener": "Hello"},
                     {"id": "anu", "names": ["Anu", "Anuu"], "relation": "niece", "group": "family_kid", "language": "mix", "opener": "Hey cutie pie."},
                     {"id": "sam", "names": ["Sam", "Sammy"], "relation": "friend", "language": "english", "opener": "Hey Sam"}]}


def _file(tmp_path, monkeypatch):
    from jarvis.service import people

    f = tmp_path / "people.json"
    f.write_text(json.dumps(PEOPLE))
    monkeypatch.setenv("PEOPLE_FILE", str(f))
    people._CACHE.update(m=None, v={})


def test_find_by_any_name_and_exact_first(tmp_path, monkeypatch):
    from jarvis.service import people

    _file(tmp_path, monkeypatch)
    assert people.find("mom")["id"] == "mom"
    assert people.find("Prasad")["id"] == "dad"
    assert people.find("Ravi Kumar")["id"] == "bil"
    assert people.find("Sammy")["id"] == "sam" and people.find("Anuu")["id"] == "anu"
    assert people.find("nobody") is None


def test_introduce_then_back(tmp_path, monkeypatch):
    from jarvis.service import people

    _file(tmp_path, monkeypatch)
    j = J(tmp_path)
    assert "TALKING TO" not in people.prompt_note(j, "t1") and "introduce" in people.prompt_note(j, "t1")
    r = people.introduce(j, "t1", "Mom")
    assert r["now_talking_to"] == "Lakshmi" and "namaskaram" in r["opener"]
    note = people.prompt_note(j, "t1")
    assert note.startswith("[TALKING TO") and "Telugu guide" in note and "Lakshmi garu" in note
    assert people.voice_language(j, "t1") == "te"
    assert people.talking_to(j, "t2") is None                    # only that conversation
    people.back(j, "t1")
    assert people.talking_to(j, "t1") is None and people.voice_language(j, "t1") == "en"


def test_a_child_gets_child_rules(tmp_path, monkeypatch):
    from jarvis.service import people

    _file(tmp_path, monkeypatch)
    j = J(tmp_path)
    assert "child" in people.introduce(j, "t1", "Anu")["do_now"]
    assert "no money, trading or investing" in people.prompt_note(j, "t1")


def test_unknown_person_and_missing_file(tmp_path, monkeypatch):
    from jarvis.service import people

    _file(tmp_path, monkeypatch)
    assert "error" in people.introduce(J(tmp_path), "t1", "Stranger")
    monkeypatch.setenv("PEOPLE_FILE", str(tmp_path / "none.json"))
    people._CACHE.update(m=None, v={})
    assert people.load() == {} and people.prompt_note(J(tmp_path), "t1") == ""


def test_telugu_answers_use_the_telugu_voice():
    from jarvis.service import speech

    assert speech.is_telugu(["Hello andi Lakshmi garu.. namaskaram.", "Nenu mee trading assistant ni."])
    assert speech.is_telugu(["నమస్కారం అండి"])
    assert not speech.is_telugu(["Sir, the dial is open and Bitcoin is above both averages."])
    assert not speech.is_telugu(["Hello Sita, good evening. I am a trading assistant built by Madhav."])


def test_market_check_can_only_add_caution(monkeypatch):
    from jarvis.service import weblook

    def fake(facts, unlock="no"):
        body = json.dumps({"facts": facts, "unlock_next_30d": unlock, "mood": "calm"})
        return lambda url, h, b, timeout=40: {"candidates": [{"content": {"parts": [{"text": body}]}}]}

    monkeypatch.setenv("GEMINI_API_KEY", "x")
    weblook._MC.clear()
    good = weblook.market_check(J("/tmp"), "SOL", post=fake([{"kind": "news", "fact": "ETF approved", "effect": "safer"}]), cache_s=0)
    assert good["verdict"].startswith("NO RED FLAGS") and "never adds a reason to buy" in good["verdict"]
    weblook._MC.clear()
    bad = weblook.market_check(J("/tmp"), "SOL", post=fake([], unlock="yes"), cache_s=0)
    assert bad["verdict"].startswith("CAUTION")
