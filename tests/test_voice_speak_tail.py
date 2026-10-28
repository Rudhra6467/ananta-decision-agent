"""/speak tail (27 Oct, streamed India answers): a piece of an answer ends with the pause a sentence would have, so pieces join naturally;
the default (one whole answer, crypto) is unchanged. Runs in the voice venv; skipped where the voice server can't be imported."""
import numpy as np
import pytest

srv = pytest.importorskip("jarvis.voice.server")


class _R:
    def __init__(self, n):
        self.audio = np.full(n, 0.5, dtype=np.float32)


class _Model:
    def generate(self, text, voice, speed, lang_code):
        yield _R(24000)                                    # one second of "speech" per sentence


def test_tail_adds_a_pause_after_the_last_sentence(monkeypatch):
    monkeypatch.setattr(srv, "tts_model", lambda: _Model())
    monkeypatch.setattr(srv, "encode_mp3", lambda audio, rate=24000: (b"x" * len(audio), "audio/mpeg"))
    plain = srv.speak(srv.SpeakReq(sentences=["One.", "Two."], voice="bm_lewis"))
    piece = srv.speak(srv.SpeakReq(sentences=["One.", "Two."], voice="bm_lewis", tail=0.32))
    assert piece["duration"] == pytest.approx(plain["duration"] + 0.32, abs=0.01)
    assert piece["offsets"] == plain["offsets"] and plain["voice"] == piece["voice"] == "bm_lewis"
