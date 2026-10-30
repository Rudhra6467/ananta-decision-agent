"""The India answer spoken in pieces (Madhav, 27 Oct: "the time gap for replying in voice has become a new issue now"): the first sentence
is made first and plays while the rest is made, in order, in the same voice; only a phone that says it plays pieces gets a stream; a failed
piece is reported (the phone says the rest in its own voice); the model's facts are cached as a second system part."""
import base64
import json

import pytest
import requests

from jarvis.india import ask as ia, voice as iv

TEXT = ("Sir, my read: wait. The Nifty closed at about 22,750 on 27 Oct, under both its 50- and 200-day averages, and only 39% of the liquid "
        "stocks are above their 200-day. On paper, Ananta's plan is to wait. It makes no new buys for your account today, and in a downtrend it "
        "keeps at least 20% in cash. I would change my mind if the Nifty climbs back above its averages. So as a beginner, wait.")


class FakeVoice:
    def __init__(self, fail_at=None):
        self.calls, self.fail_at = [], fail_at

    def __call__(self, url, body):
        assert url.endswith("/speak")
        self.calls.append(body)
        if self.fail_at is not None and len(self.calls) - 1 in self.fail_at:
            raise requests.ConnectionError("voice server down")
        n = len(body["sentences"])
        return {"audio_b64": base64.b64encode(b"MP3" + json.dumps(body["sentences"]).encode()).decode(), "mime": "audio/mpeg",
                "offsets": [i * 1.0 for i in range(n)], "duration": float(n), "ms": 5}


@pytest.fixture(autouse=True)
def clean():
    iv._streams.clear()
    yield
    iv._streams.clear()


def test_pieces_start_small_then_about_200_characters():
    s = iv.sentences([TEXT])
    p = iv.pieces(s)
    assert p[0] == [0]                                     # "Sir, my read: wait." alone: the next sentence is long (143 characters)
    assert [i for g in p for i in g] == list(range(len(s)))
    assert all(len(g) <= 3 for g in p) and len(p) >= 3
    assert iv.pieces(["Yes, sir.", "A stop-loss sells at your price.", "That limits a loss."])[0] == [0, 1]   # a very short first sentence takes the next
    assert iv.pieces(["One long first sentence that is well over forty characters long."]) == [[0]]


def test_the_first_piece_is_a_whole_sentence_and_the_next_pieces_ramp_up():
    """30 Oct (Madhav: "voice cuts after the first 4-5 words in every answer"): the opening-clause cut is off. A 4-word clause was 2 s of audio
    and the next piece took 3.5-8 s to make on a busy GPU, so the voice went silent mid-sentence. Now piece 0 is the whole first sentence,
    piece 1 is small (about 110 characters), piece 2 about 160, then about 200."""
    long0 = ("A stop-loss order is an instruction to your broker to sell automatically, once the price falls to a level you set in "
             "advance, so one bad trade cannot grow.")
    rest = ["For example, buy at 100 and set the stop at 93.", "It limits damage; it does not raise returns.", "Sir, that is the whole idea of it.",
            "A trailing stop moves up with the price.", "Ananta's tests found the fixed stop did better.", "So use a fixed one.", "Nothing is placed from chat."]
    p = iv.plan([long0] + rest)
    assert p[0] == [(0, long0)]                                           # no clause cut: sentence 0 is one piece
    assert [i for g in p for i, _ in g] == list(range(1 + len(rest)))     # nothing lost, nothing repeated
    assert sum(len(t) for _, t in p[1]) <= iv.STREAM_RAMP[0] + 60 and len(p[1]) <= 3      # small second piece
    fake = FakeVoice()
    key = iv.start_stream([" ".join([long0] + rest)], 1.0, fake, background=False)
    assert fake.calls[0]["sentences"] == [long0] and fake.calls[0]["tail"] == iv.STREAM_TAIL_S
    m = iv.answer_meta(key)
    assert m["segments"][1]["first"] == 1


def test_a_slow_first_piece_is_held_for_the_second(monkeypatch):
    """When the GPU made piece 0 slower than it plays, the stream's meta (what the phone waits for) also waits, bounded, for piece 1."""
    import threading
    key = iv.start_stream([TEXT], 1.0, FakeVoice(), background=False)
    s = iv._streams[key]
    s["segs"][0]["ms"], s["segs"][0]["duration"] = 4000, 2.0           # 4 s to make 2 s of audio: busy
    s["events"][1].clear()
    waited = []
    orig = s["events"][1].wait
    monkeypatch.setattr(s["events"][1], "wait", lambda t=None: (waited.append(t), orig(0))[1])
    iv.stream_meta(key)
    assert waited and 0 < waited[0] <= iv.STREAM_HOLD_S
    s["segs"][0]["ms"], s["segs"][0]["duration"] = 500, 6.0            # idle: no hold
    waited.clear()
    iv.stream_meta(key)
    assert not waited


def test_stream_meta_audio_and_pieces_in_order_same_voice():
    fake = FakeVoice()
    key = iv.start_stream([TEXT], 1.0, fake, background=False)
    assert key.startswith("s") and all(c["voice"] == iv.INDIA_VOICE for c in fake.calls)
    assert [c.get("tail", 0) for c in fake.calls][:-1] == [iv.STREAM_TAIL_S] * (len(fake.calls) - 1) and "tail" not in fake.calls[-1]
    m = iv.answer_meta(key)
    assert m["stream"] and m["segments"][0]["id"] == key + ".0" and m["sentences"] == len(iv.sentences([TEXT]))
    firsts = [g["first"] for g in m["segments"]]
    assert firsts == sorted(firsts) and firsts[0] == 0
    audio, mime = iv.answer_audio(key)                      # the stream's own id plays the first piece
    assert audio.startswith(b"MP3") and mime == "audio/mpeg" and b"my read" in audio
    seg1 = iv.answer_meta(m["segments"][1]["id"])
    assert seg1["first"] == m["segments"][1]["first"] and seg1["count"] == m["segments"][1]["count"]
    assert iv.answer_audio(m["segments"][-1]["id"])[0].startswith(b"MP3")
    assert iv.start_stream([TEXT], 1.0, fake, background=False) == key and len(fake.calls) == len(m["segments"])   # made once


def test_a_failed_piece_is_retried_then_reported():
    fake = FakeVoice(fail_at={1, 2})                        # piece 1 fails twice (calls 1 and 2), the rest are made
    key = iv.start_stream([TEXT], 1.0, fake, background=False)
    m = iv.answer_meta(key)
    with pytest.raises(requests.ConnectionError):
        iv.answer_audio(m["segments"][1]["id"])
    assert iv.answer_audio(m["segments"][2]["id"])[0].startswith(b"MP3")
    with pytest.raises(KeyError):
        iv.answer_meta(key + ".99")
    with pytest.raises(KeyError):
        iv.answer_meta("snotthere")


def test_only_a_phone_that_plays_pieces_gets_a_stream(monkeypatch):
    started = []
    monkeypatch.setattr(iv, "start_stream", lambda texts, speed=1.0, post=None, background=True: started.append((texts, speed)) or "sabc")
    out = iv.attach_stream({"answer": TEXT, "kind": "answer"}, {"tts": {"voice": "Calm", "speed": 1.15, "stream": True}})
    assert out["voice_id"] == "sabc" and out["speak"] == TEXT and started == [([TEXT], 1.15)]
    for ctx, o in (({"tts": {"voice": "Calm", "speed": 1.0}}, {"answer": TEXT}), (None, {"answer": TEXT}),
                   ({"tts": {"stream": True}}, {"answer": "Which one?", "kind": "clarify"}), ({"tts": {"stream": True}}, {"error": "x", "answer": ""})):
        assert "voice_id" not in iv.attach_stream(dict(o), ctx)


def test_turn_starts_the_first_piece_before_returning(monkeypatch):
    monkeypatch.setattr(iv, "transcribe_full", lambda a, m, post=None: ("What is a stop-loss order?", {"speaker": "madhav", "score": 0.9}))
    monkeypatch.setattr(iv, "start_stream", lambda texts, speed=1.0, post=None, background=True: "s123")
    out = iv.turn("madhav", "AAA", "audio/webm", "t1", None, {"tts": {"voice": "Calm", "speed": 1.0, "stream": True}},
                  lambda *a, **k: {"answer": "A stop-loss sells automatically at your price.", "kind": "answer"})
    assert out["voice_id"] == "s123" and out["speak"].startswith("A stop-loss") and out["speaker"]["speaker"] == "madhav"


def test_prepare_answer_stream_flag_waits_only_for_the_first_piece():
    fake = FakeVoice()
    m = iv.prepare_answer([TEXT], 1.0, fake, stream=True)       # background worker; the meta waits for piece 0 only
    assert m["stream"] and len(m["segments"]) >= 3 and m["id"].startswith("s")
    assert iv.prepare_answer([TEXT], 1.0, fake)["id"][0] != "s"  # without the flag: one file, as before (old phones, crypto-style)


def test_claude_caches_the_facts_as_a_second_system_part(monkeypatch):
    monkeypatch.setattr(ia, "_load_env_key", lambda: "k")
    seen = {}

    def post(url, headers, body):
        seen.update(body)
        return {"content": [{"type": "text", "text": "{}"}], "usage": {"input_tokens": 150, "output_tokens": 9, "cache_read_input_tokens": 50000}}

    text, u = ia._claude("SYS", [{"role": "user", "text": "hi"}, {"role": "assistant", "text": "{}"}], "OLD USER WITH FACTS", post=post,
                         cached=("FACTS BLOCK", "QUESTION ONLY"))
    assert [p["text"] for p in seen["system"]] == ["SYS", "FACTS BLOCK"] and all(p.get("cache_control") for p in seen["system"])
    assert seen["messages"][-1]["content"] == "QUESTION ONLY" and u["cache_read"] == 50000
    # a stand-in without the new argument still gets the old single user turn (facts included)
    got = []
    monkeypatch.setattr(ia, "_claude", lambda system, history, user, post=None: got.append(user) or ("{}", {"model": "fake"}))
    ia._call("SYS", [], "OLD USER WITH FACTS", cached=("FACTS BLOCK", "QUESTION ONLY"))
    assert got == ["OLD USER WITH FACTS"]


def test_the_voice_says_company_names_but_the_screen_keeps_the_ticker():
    """30 Oct (Madhav: "it's about you pronouncing them"): tickers are spoken as company names; the shown text and the sentence count are unchanged."""
    fake = FakeVoice()
    text = "Sell half of JIOFIN (about Rs 12,200) and trim TATAPOWER. IEX and IDEA are tiny. KOTAKBANK's RSI is 69."
    key = iv.start_stream([text], 1.0, fake, background=False)
    said = [x for c in fake.calls for x in c["sentences"]]
    assert said[0].startswith("Sell half of Jio Financial (about Rs 12,200) and trim Tata Power.")
    assert "I E X and Vodafone Idea are tiny." in said and "Kotak Bank's RSI is 69." in said
    assert len(said) == len(iv.sentences([text])) == 3
    assert iv._streams[key]["sents"][0].startswith("Sell half of JIOFIN")            # the shown sentences keep the tickers
    assert iv.say_names("The Nifty and Bank Nifty closed up; MARICO held.") == "The Nifty and Bank Nifty closed up; Marico held."
