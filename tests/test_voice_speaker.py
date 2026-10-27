"""Speaker recognition (Madhav, 27 Oct: "Yes for speaker recognition model"): a local ECAPA voice print says whether a clip is Madhav's.
Runs in the speaker venv (~/ananta_venvs/speaker, SpeechBrain); skipped where SpeechBrain is not installed. Synthetic speakers: the Mac's own
'say' voices (one voice enrolled as "Madhav", others as other people)."""
import importlib
import json
import os
import shutil
import stat
import subprocess
import sys

import numpy as np
import pytest

pytest.importorskip("speechbrain")
if sys.platform != "darwin" or not shutil.which("say"):
    pytest.skip("needs the Mac's 'say' voices", allow_module_level=True)

SENT = ["Ananta, how did the Nifty close today?", "Show me my holdings and the practice book.", "Yes to all your recommendations.",
        "What is the rupee doing against the dollar?", "Flag this: the options card is not loading.", "Ananta, it's me, Madhav.",
        "What is the RSI on Bank Nifty and where is its support?", "Should I trim Tata Power this week?"]


def _say(text, voice, d, k):
    import soundfile as sf
    a, w = os.path.join(d, f"{k}.aiff"), os.path.join(d, f"{k}.wav")
    subprocess.run(["say", "-v", voice, "-o", a, text], check=True, timeout=60)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", a, w], check=True, timeout=60)
    x, _ = sf.read(w, dtype="float32")
    return x


@pytest.fixture(scope="module")
def S(tmp_path_factory):
    home = tmp_path_factory.mktemp("voice")
    real = os.path.expanduser("~/ananta_data/voice/models")          # reuse the downloaded model, never the real profile
    os.makedirs(home / "models", exist_ok=True)
    if os.path.isdir(real + "/ecapa") and not (home / "models" / "ecapa").exists():
        os.symlink(real + "/ecapa", home / "models" / "ecapa")
    os.environ["ANANTA_VOICE_DATA"] = str(home)
    from jarvis.voice import speaker
    mod = importlib.reload(speaker)
    yield mod
    os.environ.pop("ANANTA_VOICE_DATA", None)


@pytest.fixture(scope="module")
def clips(tmp_path_factory):
    d = str(tmp_path_factory.mktemp("say"))
    return {v: [_say(s, v, d, f"{v}{i}") for i, s in enumerate(SENT)] for v in ("Aman", "Daniel", "Karen")}


def _b64(x):
    import base64
    return base64.b64encode(np.ascontiguousarray(x, dtype="<f4").tobytes()).decode()


def test_enrol_one_voice_then_it_scores_above_the_others(S, clips):
    from fastapi.testclient import TestClient
    c = TestClient(S.app)
    assert c.get("/enrol/status").json()["enrolled"] is False
    r0 = c.post("/score", json={"pcm_b64": _b64(clips["Aman"][6])}).json()
    assert r0["speaker"] == "unknown" and r0["enrolled"] is False                # nobody is "Madhav" before enrolment
    neg = [_b64(clips[v][0]) for v in ("Daniel", "Karen")]
    assert c.post("/negatives", json={"pcm_b64": neg, "voices": ["Daniel", "Karen"]}).json()["n"] == 2
    c.post("/enrol/start", json={})
    for i in range(6):
        r = c.post("/enrol", json={"pcm_b64": _b64(clips["Aman"][i])}).json()
        assert r["ok"] and r["count"] == i + 1
    assert r["done"] and set(r["thresholds"]) == {"accept", "reject", "provisional"}
    p = S.load_profile()
    assert len(p["print"]) == 192 and p["count"] == 6 and p["model"] == S.MODEL_ID
    assert stat.S_IMODE(os.stat(S.PROFILE).st_mode) == 0o600                   # only the voice print, private
    assert set(p) == {"print", "count", "model", "enrolled_at", "thresholds"}    # no audio, no single prints kept
    same = [c.post("/score", json={"pcm_b64": _b64(x)}).json() for x in clips["Aman"][6:]]
    other = [c.post("/score", json={"pcm_b64": _b64(x)}).json() for v in ("Daniel", "Karen") for x in clips[v][6:]]
    assert min(s["score"] for s in same) > max(o["score"] for o in other) + 0.3
    assert all(s["speaker"] == "madhav" for s in same), same
    assert all(o["speaker"] == "not_madhav" for o in other), other
    assert all(s["ms"] < 1500 for s in same)


def test_short_clips_are_unknown_and_reset_forgets(S, clips):
    from fastapi.testclient import TestClient
    c = TestClient(S.app)
    short = c.post("/score", json={"pcm_b64": _b64(clips["Aman"][7][:16000]), "speech_s": 0.9}).json()
    assert short["speaker"] == "unknown" and short["why"] == "too little speech"
    assert c.post("/enrol", json={"pcm_b64": _b64(clips["Aman"][7][:8000]), "speech_s": 0.5}).json()["ok"] is False
    assert c.post("/enrol/reset", json={}).json()["enrolled"] is False and not S.PROFILE.exists()


def test_calibration_keeps_an_unknown_band_when_voices_overlap(S):
    a = np.ones(192, dtype=np.float32) / np.sqrt(192)
    near = (a + np.random.default_rng(1).normal(0, 0.02, 192)).astype(np.float32)
    th = S.calibrate([a, near, a, near, a], [near.tolist()])             # a "negative" that sounds just like him
    assert th["provisional"] is True and th["reject"] < th["accept"]
    assert S.verdict(0.99, 3.0, {"thresholds": th}) == "madhav" and S.verdict(None, 3.0, {"thresholds": th}) == "unknown"
    assert S.verdict(0.99, 1.0, {"thresholds": th}) == "unknown"                # under MIN_SPEECH_S
