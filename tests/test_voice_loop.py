"""27 Oct: the India voice heard "TATAPOWER, TATAPOWER, ..." twice in one morning. Whisper repeated the ticker names it was told to expect. The
names list is now Madhav only. Near-silence is cut before decoding, and Whisper's no-speech and loop guards drop bad segments. A transcript
that is still a loop is decoded once more without the prompt before the app asks him to say it again."""
import sys

import numpy as np
import pytest

from jarvis.india import voice as V


def test_india_names_are_madhav_only():
    assert V.expected_names() == "Madhav"


srv = pytest.importorskip("jarvis.voice.server")


def test_loops_are_spotted_and_speech_is_not():
    assert srv.is_loop("RECOVER, TATAPOWER, TATAPOWER, TATAPOWER, TATAPOWER, TATAPOWER, TATAPOWER, TATAPOWER, TATAPOWER")
    assert srv.is_loop("Nifty, Nifty, Nifty, Nifty, Nifty, Nifty, Nifty, Nifty, Nifty, Nifty")
    assert srv.is_loop("fix one fix one fix one fix one fix one fix one fix one")
    assert not srv.is_loop("What is a golden cross and what does it usually signal?")
    assert not srv.is_loop("Nifty, Bank Nifty and the Nifty midcap: how did the Nifty do against Bank Nifty today?")


def test_whisper_guards_drop_no_speech_and_looping_segments():
    assert srv._keep({"no_speech_prob": 0.1, "avg_logprob": -0.3, "compression_ratio": 1.4})
    assert not srv._keep({"no_speech_prob": 0.9, "avg_logprob": -1.5, "compression_ratio": 1.0})
    assert not srv._keep({"no_speech_prob": 0.1, "avg_logprob": -0.2, "compression_ratio": 3.1})
    assert srv._keep({"no_speech_prob": 0.9, "avg_logprob": -0.2, "compression_ratio": 1.2})       # confidently decoded: kept


def test_silence_is_trimmed_and_measured():
    a = np.concatenate([np.zeros(16000 * 2), 0.2 * np.ones(16000), np.zeros(16000 * 3)]).astype(np.float32)
    cut, secs = srv.voiced(a)
    assert 0.95 <= secs <= 1.05 and 16000 * 1.4 <= cut.size <= 16000 * 1.6
    assert srv.voiced(np.zeros(16000 * 4, dtype=np.float32))[1] == 0.0


def test_a_loop_is_decoded_again_without_the_prompt(monkeypatch, tmp_path):
    calls = []
    outs = iter([("TATAPOWER, " * 12, "TATAPOWER, " * 12), ("What is a hammer candle?", "What is a hammer candle?")])

    def fake(audio, language, prompt):
        calls.append(prompt)
        return next(outs)
    monkeypatch.setattr(srv, "_decode", fake)
    fake_audio = type(sys)("mlx_whisper.audio")
    fake_audio.load_audio = lambda p: np.concatenate([np.zeros(8000), 0.2 * np.ones(16000)]).astype(np.float32)
    monkeypatch.setitem(sys.modules, "mlx_whisper", type(sys)("mlx_whisper"))
    monkeypatch.setitem(sys.modules, "mlx_whisper.audio", fake_audio)
    info = {}
    assert srv.stt_file(str(tmp_path / "x.wav"), "en", "Madhav", "india", info) == "What is a hammer candle?"
    assert calls[0] and "Nifty" in calls[0] and calls[1] is None and "retry" in info


def test_still_a_loop_or_no_speech_gives_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(srv, "_decode", lambda audio, language, prompt: ("Nifty, " * 20, "Nifty, " * 20))
    fake_audio = type(sys)("mlx_whisper.audio")
    fake_audio.load_audio = lambda p: (0.2 * np.ones(16000)).astype(np.float32)
    monkeypatch.setitem(sys.modules, "mlx_whisper", type(sys)("mlx_whisper"))
    monkeypatch.setitem(sys.modules, "mlx_whisper.audio", fake_audio)
    info = {}
    assert srv.stt_file(str(tmp_path / "x.wav"), "en", "Madhav", "india", info) == "" and info["dropped"] == "repetition loop"
    fake_audio.load_audio = lambda p: np.zeros(16000 * 3, dtype=np.float32)
    info = {}
    assert srv.stt_file(str(tmp_path / "x.wav"), "en", "Madhav", "india", info) == "" and info["dropped"] == "no speech"
