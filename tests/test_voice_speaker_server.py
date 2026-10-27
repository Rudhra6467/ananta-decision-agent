"""The voice server's side of speaker recognition (27 Oct): every transcript carries a speaker field, and a missing or broken speaker service
never blocks the words ("unknown"). Runs in the voice venv; skipped where the voice server can't be imported."""
import numpy as np
import pytest

srv = pytest.importorskip("jarvis.voice.server")


def test_speaker_service_down_means_unknown(monkeypatch, tmp_path):
    monkeypatch.setattr(srv, "SPEAKER_URL", "http://127.0.0.1:9")            # nothing listens there
    monkeypatch.setattr(srv, "SPEAKER_LOG", str(tmp_path / "log.jsonl"))
    out = srv.speaker_of(np.zeros(32000, dtype=np.float32), 2.0)
    assert out["speaker"] == "unknown" and "speaker service" in out["why"]
    assert (tmp_path / "log.jsonl").read_text().count('"unknown"') == 1        # logged: verdict only, no audio


def test_no_audio_means_unknown():
    assert srv.speaker_of(None, 0)["speaker"] == "unknown"


def test_verdicts_pass_through(monkeypatch, tmp_path):
    monkeypatch.setattr(srv, "SPEAKER_LOG", str(tmp_path / "log.jsonl"))
    monkeypatch.setattr(srv, "_spk_post", lambda path, body=None, timeout=2.0: {"speaker": "madhav", "score": 0.8, "enrolled": True})
    assert srv.speaker_of(np.ones(32000, dtype=np.float32) * 0.1, 2.0)["speaker"] == "madhav"
