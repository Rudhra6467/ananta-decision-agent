"""5 Nov 2026 (the 20-day synopsis): the crypto Ask called the grader "sir" in every session and ignored the voice print; India has had
both since 27 Oct. The grader is a built-in observer; Madhav's voice ends a handover; a voice clearly not his is asked who it is."""
from jarvis.service import ask, people
from tests.test_ask_ananta import _jarvis


def test_the_grader_is_recognised_in_its_own_words(monkeypatch, tmp_path):
    monkeypatch.setenv("PEOPLE_FILE", str(tmp_path / "people.json"))
    r = people.observer_route("Grader here. Bitcoin closed about half a percent above its 50-day. What is allowed now?")
    assert r["kind"] == "handover" and r["person"]["id"] == "grader" and r["rest"].startswith("Bitcoin closed")
    assert people.observer_route("Ananta, talk to the grader.")["kind"] == "handover"
    assert people.observer_route("I'm the greater")["person"]["id"] == "grader"          # how speech-to-text has heard it
    assert people.observer_route("The grader asks what the dial is")["kind"] == "relay"
    assert people.observer_route("What grade would you give this coin?") is None
    assert not (tmp_path / "people.json").exists(), "the grader is never written to the private people note"


def test_an_observer_keeps_the_conversation_until_madhav_is_back(monkeypatch, tmp_path):
    monkeypatch.setenv("PEOPLE_FILE", str(tmp_path / "people.json"))
    j, _ = _jarvis()
    people.set_speaker(j, "t1", people.GRADER)
    assert people.talking_to(j, "t1")["id"] == "grader"
    assert people.route(j, "t1", "Approve all the drafts") is None, "the grader's 'approve' is the grader's, told it needs Madhav"
    assert people.route(j, "t1", "Ananta, it's me")["kind"] == "back"
    note = people.prompt_note(j, "t1")
    assert "the grader" in note and "Never call the grader sir" in note


def test_his_voice_ends_a_handover_and_another_voice_is_asked_who(monkeypatch, tmp_path):
    monkeypatch.setenv("PEOPLE_FILE", str(tmp_path / "people.json"))
    j, _ = _jarvis()
    A = ask.Ask(j)
    people.set_speaker(j, "t2", people.GRADER)
    A._turn_vmeta = {"speaker": "madhav", "score": 0.81, "enrolled": True}
    assert A._people_route("owner", "how is the account doing", "t2", True, "", None) is None
    assert people.talking_to(j, "t2") is None and "Madhav is back" in A._people_note
    A._turn_vmeta = {"speaker": "not_madhav", "score": 0.05, "enrolled": True}
    out = A._people_route("owner", "Yes to all, approve the drafts.", "t3", True, "", None)
    assert out and out["answer"].startswith("Who am I speaking with?")
    A._turn_vmeta = {"speaker": "not_madhav", "score": 0.05, "enrolled": True}
    assert A._people_route("owner", "What is a moving average?", "t4", True, "", None) is None, "a plain question is simply answered"


def test_a_test_question_meets_the_grader_but_never_adds_a_person(monkeypatch, tmp_path):
    monkeypatch.setenv("PEOPLE_FILE", str(tmp_path / "people.json"))
    j, _ = _jarvis()
    A = ask.Ask(j)
    assert A._people_route("owner", "Grader here. Do you have an edge after costs?", "e1", False, "eval", None) is None
    assert people.talking_to(j, "e1")["id"] == "grader"
    assert A._people_route("owner", "This is my cousin Ravi, talk to him", "e2", False, "eval", None) is None
    assert not (tmp_path / "people.json").exists()
