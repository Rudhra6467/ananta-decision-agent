"""5 Nov 2026 (Madhav: "the real fix is to have Ananta start speaking while it's still writing the answer ... do it please"): the model's
answer is read sentence by sentence while it is written, each sentence is checked and turned into audio at once, and the phone plays the
pieces as they come."""
import json
import time

from jarvis.india import ask, voice


def test_answer_tap_hands_on_each_finished_sentence_while_the_json_arrives():
    got = []
    tap = ask.AnswerTap(got.append)
    raw = json.dumps({"kind": "answer", "stage": "outcome", "answer": "Sir, the Nifty closed at 24,537 (+2.4%). Bank Nifty rose \"3.3%\".\n"
                      "Paid Rs. 478 for it vs. 771 before. Done", "breakdown": ["x. Y"]})
    for i in range(0, len(raw), 7):                     # the stream comes in small pieces
        tap.feed(raw[i:i + 7])
    tap.close()
    assert got == ["Sir, the Nifty closed at 24,537 (+2.4%).", "Bank Nifty rose \"3.3%\".", "Paid Rs. 478 for it vs. 771 before.", "Done"]


def test_the_first_sentence_is_out_before_the_answer_ends():
    got = []
    tap = ask.AnswerTap(got.append)
    tap.feed('{"kind":"answer","stage":"observation","answer":"First sentence here. Second one is still being wri')
    assert got == ["First sentence here."]


def test_live_finish_adds_only_what_is_new_and_never_a_second_telling():
    key = voice.live_start(1.0, post=lambda url, body: {"audio_b64": "", "offsets": [0], "duration": 1.0})
    for s in ["Noted as flag 61, sir.", "Nifty closed at 24,537.", "The options trade lost Rs 8,782 on paper."]:
        voice.live_add(key, s)
    n = voice.live_finish(key, "Noted as flag 61, sir. Nifty closed at 24,537 today. The options trade lost Rs 8,782 on paper. "
                               "One more thing, sir: 3 drafts wait for your yes.")
    assert n == 1
    voice.live_end(key)
    m = voice.live_more(key, 0, wait=5)
    deadline = time.time() + 5
    while not m["done"] and time.time() < deadline:
        m = voice.live_more(key, len(m["segments"]), wait=1)
    text = " ".join(s["text"] for s in m["segments"])
    assert text.count("Nifty closed") == 1 and text.endswith("3 drafts wait for your yes.")
    assert m["segments"][0]["text"] == "Noted as flag 61, sir.", "the first piece is the first sentence alone, so it starts at once"


def test_a_rewritten_answer_is_not_spoken_again():
    key = voice.live_start(1.0, post=lambda url, body: {"audio_b64": "", "offsets": [0], "duration": 1.0})
    voice.live_add(key, "The market rose sharply today on broad buying.")
    assert voice.live_finish(key, "Completely different words about another matter entirely.") == 0
    voice.live_end(key)


def test_a_live_turn_replies_at_the_first_sentence_and_gives_the_whole_answer_after():
    def fake_ask(who, text, thread=None, mode=None, context=None, voice=False, speak_live=None):
        speak_live("Sir, the first sentence.")
        time.sleep(0.6)                                  # the rest is still being written
        speak_live("And the second.")
        return {"answer": "Sir, the first sentence. And the second.", "thread": thread, "kind": "answer"}
    post = lambda url, body: {"audio_b64": "", "offsets": [0], "duration": 1.0}  # noqa: E731
    t0 = time.time()
    r = voice._turn_live("owner", "how did it go?", {"speaker": "madhav"}, None, None, {}, {"tts": {"stream": True, "live": True}}, fake_ask, post, 1.0)
    assert time.time() - t0 < 0.5 and r["streaming"] and r["pending"] and r["voice_id"].startswith("sL") and r["thread"]
    whole = voice.turn_result(r["pending"], wait=5)
    assert whole["answer"] == "Sir, the first sentence. And the second." and whole["voice_id"] == r["voice_id"]


def test_a_code_answer_still_comes_whole():
    def code_ask(who, text, thread=None, mode=None, context=None, voice=False, speak_live=None):
        return {"answer": "Your flags, sir: none.", "thread": thread, "kind": "answer"}
    r = voice._turn_live("owner", "my flags", {"speaker": "madhav"}, "t1", None, {}, {"tts": {}}, code_ask, None, 1.0)
    assert r["answer"] == "Your flags, sir: none." and not r.get("pending")
