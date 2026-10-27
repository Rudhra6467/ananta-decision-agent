"""Who is speaking, from the voice (Madhav, 27 Oct: "Yes for speaker recognition model"): the voice server's speaker verdict travels with
the transcript to the India Ask as context["voice_id"], and jarvis/india/voiceid.py turns it into one word. Typed messages are unaffected."""
from jarvis.india import voice as V
from jarvis.india import voiceid


def test_identify_maps_the_voice_server_verdict():
    assert voiceid.identify({"speaker": "madhav", "score": 0.81, "enrolled": True}) == "madhav"
    assert voiceid.identify({"speaker": "not_madhav", "score": 0.08, "enrolled": True}) == "other"
    assert voiceid.identify({"speaker": "unknown", "score": 0.4, "enrolled": True}) == "unknown"
    assert voiceid.identify({"speaker": "madhav", "enrolled": False}) == "unknown"          # never trusted before enrolment
    assert voiceid.identify(None) == "unknown" and voiceid.identify("madhav") == "unknown"


def test_a_strange_voice_asking_for_owner_things_needs_a_check():
    other = {"speaker": "not_madhav", "score": 0.05, "enrolled": True}
    assert voiceid.needs_owner_check("Yes to all your recommendations", other, guest_active=False)
    assert voiceid.needs_owner_check("flag this: the chart is wrong", other, guest_active=False)
    assert not voiceid.needs_owner_check("What is RSI?", other, guest_active=False)
    assert not voiceid.needs_owner_check("Yes to all", other, guest_active=True)              # the guest is already known
    assert not voiceid.needs_owner_check("Yes to all", {"speaker": "madhav", "enrolled": True}, guest_active=False)


def test_the_turn_carries_the_voice_verdict_to_the_ask():
    seen = {}

    def post(url, body):
        assert url.endswith("/stt")
        return {"text": "How did the Nifty close today?", "speaker": {"speaker": "madhav", "score": 0.77, "enrolled": True}}

    def ask_fn(who, text, **k):
        seen.update(k)
        return {"answer": "ok", "thread": "t1"}

    out = V.turn("owner", "AAAA", "audio/wav", "t1", None, {"screen": "home"}, ask_fn, post=post)
    assert out["voice_id"]["speaker"] == "madhav" and out["answer"] == "ok"
    assert seen["context"] == {"screen": "home", "voice_id": {"speaker": "madhav", "score": 0.77, "enrolled": True}} and seen["voice"] is True
    assert V.transcribe("AAAA", "audio/wav", post=post) == "How did the Nifty close today?"     # old callers still get text only


def test_an_old_voice_server_without_the_field_reads_as_unknown():
    text, spk = V.transcribe_full("AAAA", "audio/wav", post=lambda u, b: {"text": "hello Ananta"})
    assert text == "hello Ananta" and spk["speaker"] == "unknown"


def test_enrolment_calls_go_to_the_voice_server():
    calls = []
    V.speaker_call("enrol", {"audio_b64": "AAAA", "mime": "audio/wav"}, post=lambda u, b: calls.append((u, b)) or {"ok": True})
    assert calls[0][0].endswith("/speaker/enrol") and calls[0][1]["mime"] == "audio/wav"


def test_the_voice_id_screen_is_a_place_ananta_can_open():
    from jarvis.india import appmap
    assert "voiceid" in appmap.PLACES and appmap.ALIASES["teach ananta my voice"] == "voiceid"
