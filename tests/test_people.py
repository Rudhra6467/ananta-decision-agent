"""Madhav's people, introduce mode, the Telugu voice switch, the research desk's rules (Oct 10, 2026)."""
import json

from tests.test_universe_live import J

PEOPLE = {"rules": ["Paper only."], "telugu_guide": {"respect": "meeru, andi, garu", "mix": "mix", "words": {"andi": "polite"}},
          "people": [{"id": "mom", "names": ["Lakshmi", "Mom"], "relation": "mother", "group": "family", "tz": "Asia/Kolkata",
                      "language": "telugu", "call": "Lakshmi garu", "opener": "Hello andi Lakshmi garu.. namaskaram.", "relations": ["mother", "mom", "amma"]},
                     {"id": "dad", "names": ["Prasad", "Dad"], "relation": "father", "language": "telugu", "opener": "Good {part} sir.", "relations": ["father", "nanna"]},
                     {"id": "kid", "names": ["Chintu"], "relation": "nephew", "group": "family_kid", "language": "mix", "opener": "Hey Chintu", "relations": ["sister's son", "nephew"]},
                     {"id": "sis", "names": ["Sita"], "relation": "sister", "language": "english", "opener": "Hello Sita", "relations": ["sister", "akka"]},
                     {"id": "bil", "names": ["Ravi Kumar"], "relation": "brother-in-law", "language": "english", "opener": "Hello", "relations": ["bava", "brother-in-law"]},
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


def test_handovers_are_caught_by_code(tmp_path, monkeypatch):
    """The Oct 10 log, replayed: each message goes to the right person, by code, before any AI."""
    from jarvis.service import people

    _file(tmp_path, monkeypatch)
    j = J(tmp_path)
    cases = [("Hey here my mom is talking. Can you talk to my mom? Kanesha on do.", "handover", "mom"),
             ("Nah. Hey, talk to my dad.", "handover", "dad"),
             ("Talk to Chintu. Talk to Chintu, my sister's son.", "handover", "kid"),
             ("Hey Ananta, talk to my sister Sita. Like I'm introducing you to my Sita here.", "handover", "sis"),
             ("My mother wants to ask you something.", "handover", "mom"),
             ("Ananta, my mother is asking about Canada's weather.", "relay", "mom"),
             ("amma tho matladu", "handover", "mom"),
             ("say hi to bava", "handover", "bil")]
    for text, kind, pid in cases:
        r = people.route(j, "t1", text)
        assert r and r["kind"] == kind and r["person"]["id"] == pid, (text, r)
    assert people.route(j, "t1", "this is great") is None
    assert people.route(j, "t1", "How is bitcoin today?") is None
    assert people.route(j, "t1", "I'm back") is None                   # nobody introduced: nothing to come back from
    people.set_speaker(j, "t1", people.find("Prasad"))
    assert people.route(j, "t1", "it's me again, thanks")["kind"] == "back"
    assert people.route(j, "t1", "talk to my dad")["same"] is True      # already talking with him: no second greeting


def test_my_sisters_son_is_not_my_sister(tmp_path, monkeypatch):
    from jarvis.service import people

    _file(tmp_path, monkeypatch)
    assert people.resolve("my sister's son")["id"] == "kid"
    assert people.resolve("my sister")["id"] == "sis"
    assert people.resolve("Prasad")["id"] == "dad" and people.resolve("Ravi Kumar")["id"] == "bil"


def test_coming_back_in_english_and_new_person_by_example(tmp_path, monkeypatch):
    """Oct 11: Madhav said 'it's me' and asked about trades in English while Ananta kept talking Telugu to his mother; and 'Kamala Pinni,
    talk to her like my mother' greeted his mother instead."""
    from jarvis.service import people
    from jarvis.service.ask import _degenerate

    _file(tmp_path, monkeypatch)
    j = J(tmp_path)
    people.introduce(j, "t1", "mom")
    assert people.route(j, "t1", "It's not my mother, it's me")["kind"] == "back"
    people.introduce(j, "t1", "mom")
    assert people.route(j, "t1", "How are my trades doing in the portfolio today?")["kind"] == "back"   # English, about the account
    assert people.route(j, "t1", "ఈ రోజు మార్కెట్ ఎలా ఉంది") is None                                  # Telugu: still his mother
    r = people.route(j, "t2", "Kamala Pinni is in the house. Talk to her like my mother. Her name is Kamala Pinni, my mother's sister.")
    assert r["kind"] == "handover" and r["person"]["names"][0] == "Kamala Pinni" and r["person"]["language"] == "telugu"
    assert "Kamala Pinni garu" in r["person"]["opener"] and people.find("Kamala Pinni")                 # remembered in the private note
    assert _degenerate("కాని కాని కాని కాని కాని కాని కాని") and not _degenerate("Nenu baagunnanu andi meeru ela unnaru ee roju")


def test_named_person_beats_the_model_relation(tmp_path, monkeypatch):
    from jarvis.service import people

    _file(tmp_path, monkeypatch)
    j = J(tmp_path)
    people.route(j, "t3", "Kamala Pinni is in the house. Talk to her like my mother. Her name is Kamala Pinni.")       # created once
    r = people.route(j, "t4", "Kamala Pinni is here, talk to her like my mother.")
    assert r["kind"] == "handover" and r["person"]["names"][0] == "Kamala Pinni"
    assert people.route(j, "t5", "Talk to my mom")["person"]["id"] == "mom"
