"""5 Nov 2026 (Madhav's yes to all; the last of the nine fixes): the crypto voice speaks while the answer is still being written, as India's
has since this morning. Each round of the model's reply streams; every finished sentence of its "answer" is said at once in the crypto voice
he chose (India's live stream, jarvis/india/voice.py live_*, with the crypto spoken form), and the whole checked answer reaches the screen
while the voice is speaking (GET /v3/voice/turn/{id})."""
import json
import threading
import time

import pytest

from jarvis.india import voice as iv
from jarvis.service import ask
from tests.test_ask_ananta import _jarvis


class _Resp:
    def __init__(self, status, lines, text=""):
        self.status_code, self._lines, self.text = status, lines, text

    def iter_lines(self, decode_unicode=True):
        yield from self._lines

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _sse(events):
    out = []
    for e in events:
        out += [f"event: {e['type']}", "data: " + json.dumps(e), ""]
    return out


def _fake_speak(made):
    def speak(sents, speed=1.0, post=None, tail=0.0, voice=None, say=None):
        made.append({"sents": [say(x) if say else x for x in sents], "voice": voice})
        return {"audio": b"ID3", "mime": "audio/mpeg", "offsets": [0.0] * len(sents), "duration": 1.0, "engine": "kokoro", "voice": voice, "ms": 5}
    return speak


def _drain(key, wait=8.0):
    t0 = time.time()
    while time.time() - t0 < wait:
        m = iv.live_more(key, 0, wait=1.0)
        if m["done"]:
            return m
    raise AssertionError("the live stream never finished")


def _ask(j, providers, monkeypatch):
    A = ask.Ask(j, providers=providers)
    monkeypatch.setattr(A, "transcribe", lambda *a, **k: "explain the momentum setup simply")
    monkeypatch.setattr(A, "_quick", lambda *a, **k: None)
    monkeypatch.setattr(A, "_people_route", lambda *a, **k: None)
    return A


LIVE = {"tts": {"voice": "Calm", "speed": 1.0, "stream": True, "live": True}}


def test_a_streamed_round_is_rebuilt_as_the_whole_reply_and_hands_on_its_words(monkeypatch):
    import requests

    ev = [
        {"type": "message_start", "message": {"usage": {"input_tokens": 12, "cache_read_input_tokens": 3, "output_tokens": 1}}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": "", "signature": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "Look up BTC."}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "signature_delta", "signature": "sig1"}},
        {"type": "content_block_stop", "index": 0},
        {"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": "Checking "}},
        {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": "the price."}},
        {"type": "content_block_stop", "index": 1},
        {"type": "content_block_start", "index": 2, "content_block": {"type": "tool_use", "id": "t1", "name": "market", "input": {}}},
        {"type": "content_block_delta", "index": 2, "delta": {"type": "input_json_delta", "partial_json": '{"coin": '}},
        {"type": "content_block_delta", "index": 2, "delta": {"type": "input_json_delta", "partial_json": '"BTC"}'}},
        {"type": "content_block_stop", "index": 2},
        {"type": "message_delta", "delta": {"stop_reason": "tool_use"}, "usage": {"output_tokens": 40}},
        {"type": "message_stop"},
    ]
    sent = {}

    def fake_post(url, headers=None, json=None, timeout=None, stream=False):
        sent.update(body=json, stream=stream)
        return _Resp(200, _sse(ev))

    monkeypatch.setattr(requests, "post", fake_post)
    words = []
    r = ask._claude_round_stream("https://api.anthropic.com/v1/messages", {}, {"model": "m"}, words.append)
    assert sent["body"]["stream"] is True and sent["stream"] is True
    assert words == ["Checking ", "the price."]
    assert r["content"][0] == {"type": "thinking", "thinking": "Look up BTC.", "signature": "sig1"}, "thinking goes back with its signature"
    assert r["content"][1] == {"type": "text", "text": "Checking the price."}
    assert r["content"][2]["input"] == {"coin": "BTC"} and r["content"][2]["id"] == "t1" and r["content"][2]["name"] == "market"
    assert r["usage"]["input_tokens"] == 12 and r["usage"]["output_tokens"] == 40 and r["stop_reason"] == "tool_use"
    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp(400, [], '{"error": {"message": "Your credit balance is too low"}}'))
    with pytest.raises(RuntimeError, match=r"^400: .*credit balance"):
        ask._claude_round_stream("https://api.anthropic.com/v1/messages", {}, {}, words.append)


def test_run_claude_streams_a_spoken_answer_and_falls_back_quietly(monkeypatch):
    j, _ = _jarvis()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    final = json.dumps({"kind": "answer", "answer": "Bitcoin is flat today. Nothing needs doing."})
    calls = []

    def post(url, headers, body, timeout=60):
        calls.append(body)
        return {"content": [{"type": "text", "text": final}], "usage": {}}

    got = []
    txt, u = ask.run_claude("sys", [], "q", ask.Lookups(j), [], post=post, model="m", on_text=got.append)
    assert txt == final and len(calls) == 1 and "stream" not in calls[0] and not got, "a test stand-in never streams"
    rounds = []

    def stream(url, headers, body, on_text):
        rounds.append(body)
        on_text(final)
        return {"content": [{"type": "text", "text": final}], "usage": {"input_tokens": 5, "output_tokens": 9}, "stop_reason": "end_turn"}

    monkeypatch.setattr(ask, "_claude_round_stream", stream)
    txt, u = ask.run_claude("sys", [], "how is btc", ask.Lookups(j), [], model="m", on_text=got.append)
    assert txt == final and got == [final] and u.get("streamed") and u["out"] == 9 and len(rounds) == 1

    def broken(url, headers, body, on_text):
        raise RuntimeError("529: overloaded")

    monkeypatch.setattr(ask, "_claude_round_stream", broken)
    monkeypatch.setattr(ask, "_post_opt", lambda post, url, h, body, *a: {"content": [{"type": "text", "text": final}], "usage": {}})
    txt, u = ask.run_claude("sys", [], "how is btc", ask.Lookups(j), [], model="m", on_text=got.append)
    assert txt == final and not u.get("streamed"), "trouble on the stream: the round is asked again the old way"

    def no_credit(url, headers, body, on_text):
        raise RuntimeError("400: Your credit balance is too low to access the Anthropic API.")

    monkeypatch.setattr(ask, "_claude_round_stream", no_credit)
    with pytest.raises(RuntimeError, match="credit balance"):          # so the Ask answers with Gemini, as before
        ask.run_claude("sys", [], "q", ask.Lookups(j), [], model="m", on_text=got.append)


def test_each_spoken_sentence_keeps_the_whole_answers_rules():
    j, _ = _jarvis()
    A = ask.Ask(j)
    said = []
    sink = ask.LiveSink(said.append)
    A._live_say("Good morning, Madhav.", "o", sink, [])
    A._live_say("I've opened the Bitcoin chart for you.", "o", sink, [])     # what the screen did is decided by the finished answer
    A._live_say("Your card is waiting for your Face ID.", "o", sink, [])      # no card was made this turn
    A._live_say("Bitcoin is up about two percent today.", "o", sink, [])
    assert said == ["Good morning, sir.", "Bitcoin is up about two percent today."] and sink.words == 10
    A._live_say("Your card is waiting for your Face ID.", "o", sink, [{"id": "a1"}])
    assert said[-1].startswith("Your card"), "a card made this turn is said"
    A._live_say(" ".join(["word"] * 50) + ".", "o", sink, [])
    A._live_say("Short one.", "o", sink, [])
    assert sink.full and said[-1].startswith("Your card"), "past about 60 words the rest stays on screen, as speak_text"
    g = ask.LiveSink(said.append)
    A._live_say("Sure, sir, here it is.", "guest:ravi@x.com", g, [])
    assert said[-1] == "Sure, here it is.", "only Madhav is sir"
    te = ask.LiveSink(said.append)
    A._live_say("Meeru adigina coin gurinchi cheppandi, chala baaga undi.", "o", te, [])
    A._live_say("Bitcoin is flat.", "o", te, [])
    assert te.off and te.words == 0, "a Telugu answer keeps its own voice, spoken once it is written"


def test_a_spoken_question_is_answered_aloud_while_it_is_written(monkeypatch):
    j, _ = _jarvis()
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    made = []
    monkeypatch.setattr(iv, "_speak", _fake_speak(made))
    pre = []
    monkeypatch.setattr(ask, "_pre_voice", lambda context, text: pre.append(text))
    gate = threading.Event()
    answer = {"kind": "answer", "stage": "observation", "breakdown": [], "evidence": [], "follow_ups": [],
              "answer": "Bitcoin is about $84,700, Madhav. It is up 2.5% today. Nothing needs doing."}
    raw = json.dumps(answer)
    cut = raw.index("It is up") + 2
    seen = {}

    def provider(s, h, u, t, log, on_text=None):
        seen["streamed"] = on_text is not None
        on_text(raw[:cut])                      # the first sentence is written ...
        assert gate.wait(10), "the phone got its reply before the answer was finished"
        on_text(raw[cut:])                      # ... and the rest only after the phone is already speaking
        return raw, {"in": 1, "out": 1, "model": "m"}

    A = _ask(j, {"sonnet": provider}, monkeypatch)
    r = A.voice_turn("o@x.com", "AAAA", "audio/m4a", None, "deep", LIVE)
    assert seen["streamed"] and r["streaming"] and r["voice_id"].startswith("sL") and r["pending"].startswith("t"), r
    assert r["heard"] == "explain the momentum setup simply" and r["thread"]
    gate.set()
    whole = ask.live_turn_result(r["pending"], wait=10)
    assert whole["answer"].startswith("Bitcoin is about $84,700, sir.") and whole["voice_id"] == r["voice_id"]
    assert whole["thread"] == r["thread"] and whole["heard"] == r["heard"] and whole["streaming"] is True
    assert not pre, "spoken live: no second audio is made"
    m = _drain(r["voice_id"])
    assert " ".join(s["text"] for s in m["segments"]) == "Bitcoin is about $84,700, sir. It is up 2.5% today. Nothing needs doing."
    assert m["segments"][0]["count"] == 1, "the first piece is the first sentence alone"
    assert made and all(x["voice"] == "Calm" for x in made), "the crypto voice he chose, not India's"
    assert any("2.5 percent" in s for x in made for s in x["sents"]), "said the crypto way (for_ear), not with India's ticker names"


def test_a_model_that_cannot_stream_answers_as_before(monkeypatch):
    j, _ = _jarvis()
    monkeypatch.setattr(ask, "_pre_voice", lambda context, text: "pv1")

    def gem(s, h, u, t, log):
        return json.dumps({"kind": "answer", "answer": "Bitcoin is flat today."}), {"in": 1, "out": 1}

    A = _ask(j, {"gemini": gem}, monkeypatch)
    r = A.voice_turn("o@x.com", "AAAA", "audio/m4a", None, "everyday", LIVE)
    assert r["answer"] == "Bitcoin is flat today." and r["voice_id"] == "pv1" and not r.get("streaming") and "pending" not in r
    monkeypatch.setenv("ASK_LIVE_VOICE", "0")                        # the switch: every answer is spoken once it is written
    seen = {}

    def claude(s, h, u, t, log, on_text=None):
        seen["on_text"] = on_text
        return json.dumps({"kind": "answer", "answer": "Bitcoin is flat today."}), {"in": 1, "out": 1}

    A = _ask(j, {"sonnet": claude}, monkeypatch)
    r = A.voice_turn("o@x.com", "AAAA", "audio/m4a", None, "deep", LIVE)
    assert seen["on_text"] is None and r["voice_id"] == "pv1" and not r.get("streaming")


def test_the_phone_reaches_a_live_answer_on_the_crypto_service(monkeypatch):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from jarvis.service import app as appmod

    j, _ = _jarvis()
    monkeypatch.setattr(appmod, "_J", j)
    monkeypatch.setattr(appmod, "_JG", {})
    monkeypatch.setattr(appmod, "_A", {})
    made = []
    monkeypatch.setattr(iv, "_speak", _fake_speak(made))
    c = TestClient(appmod.app)
    h = {"Authorization": f"Bearer {j.login('o@x.com', 'pw pw pw pw 1')}"}
    key = iv.live_start(1.0, voice="Calm", say=lambda x: x)
    iv.live_add(key, "Bitcoin is flat today. Nothing needs doing.")
    iv.live_end(key)
    meta = c.get(f"/v3/voice/answer/{key}", headers=h)
    assert meta.status_code == 200 and meta.json()["live"] is True, meta.text
    assert c.get(f"/v3/voice/answer/{key}.0/audio", headers=h).content == b"ID3"
    for _ in range(40):
        more = c.get(f"/v3/voice/answer/{key}/more", params={"have": 0}, headers=h).json()
        if more["done"]:
            break
    assert more["done"] and " ".join(s["text"] for s in more["segments"]) == "Bitcoin is flat today. Nothing needs doing."
    assert c.get("/v3/voice/turn/tnope", headers=h).status_code == 404
    assert c.get("/v3/voice/answer/sLnope", headers=h).status_code == 404
    assert c.get(f"/v3/voice/answer/{key}").status_code == 401, "signed in only"
    box = {"event": threading.Event(), "out": {"answer": "Done.", "thread": "x"}, "said": 1, "key": key}
    box["event"].set()
    with ask._LIVE_LOCK:
        ask._LIVE_TURNS["tdone"] = box
    got = c.get("/v3/voice/turn/tdone", headers=h).json()
    assert got["answer"] == "Done." and got["voice_id"] == key and got["streaming"] is True
