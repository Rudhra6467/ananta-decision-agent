"""Speaker recognition: is this voice Madhav's? (Madhav, 27 Oct 2026: "Yes for speaker recognition model".)

A small local service (no cloud, no cost) beside the voice server:
    ~/ananta_venvs/speaker/bin/python -m uvicorn jarvis.voice.speaker:app --host 127.0.0.1 --port 8215   (launchd com.ananta.speaker)

Model: SpeechBrain ECAPA-TDNN trained on VoxCeleb (Hugging Face "speechbrain/spkrec-ecapa-voxceleb", licence Apache-2.0). It turns a clip into a
192-number voice print; two prints of the same person point the same way (cosine similarity near 1), different people do not.

What is stored: ONLY Madhav's averaged voice print (192 numbers), how many clips made it, the date, the model id and the thresholds, in
~/ananta_data/voice/speaker_profile.json (mode 600). No audio is kept. During enrolment the single prints of the clips so far are held in memory
only (a restart mid-enrolment means starting the six sentences again).

Verdict per clip (the voice server calls /score with the speech part of each clip, after its silence trim):
    score >= accept  -> "madhav"
    score <  reject  -> "not_madhav"
    in between, under MIN_SPEECH_S of speech, or no profile -> "unknown"
Thresholds: provisional until enrolment (ECAPA's VoxCeleb equal-error point is a cosine of about 0.25; accept 0.55, reject 0.30). When enrolment
finishes they are recalibrated from his own clips (leave-one-out: each clip against the average of the others sets the accept line) and from
synthetic "not Madhav" voices (the Mac's own 'say' voices, prints made once and kept as NEG_FILE: they are not his voice) setting the reject line.
"""
from __future__ import annotations

import base64
import datetime as dt
import json
import os
import threading
import time
from pathlib import Path

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

SR = 16000
MODEL_ID = "speechbrain/spkrec-ecapa-voxceleb"
HOME = Path(os.getenv("ANANTA_VOICE_DATA", os.path.expanduser("~/ananta_data/voice")))
PROFILE = HOME / "speaker_profile.json"
NEG_FILE = HOME / "speaker_negatives.json"          # prints of synthetic 'say' voices (not Madhav), for the reject line
MODEL_DIR = HOME / "models" / "ecapa"
MIN_SPEECH_S = 1.5
MIN_CLIPS, MAX_CLIPS = 5, 8
PROVISIONAL = {"accept": 0.55, "reject": 0.30, "provisional": True,
               "basis": "ECAPA VoxCeleb equal-error point about 0.25 cosine; on the Mac's synthetic voices (27 Oct) the same voice scored 0.76-0.92 "
                        "and different voices mostly under 0.35, but two pairs built on the same synthesiser reached 0.52-0.64; so a wide "
                        "'unknown' band until his own clips recalibrate it"}

app = FastAPI(title="Ananta speaker recognition")
_lock = threading.Lock()
_model = None
_pending: list[list[float]] = []                    # this enrolment's single prints, memory only


def model():
    global _model
    if _model is None:
        from speechbrain.inference.speaker import EncoderClassifier
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        _model = EncoderClassifier.from_hparams(source=MODEL_ID, savedir=str(MODEL_DIR), run_opts={"device": "cpu"})
    return _model


def embed(pcm: np.ndarray) -> np.ndarray:
    """The 192-number voice print of 16 kHz mono float audio, unit length."""
    import torch
    with _lock, torch.no_grad():
        e = model().encode_batch(torch.from_numpy(np.ascontiguousarray(pcm, dtype=np.float32))[None, :]).squeeze().cpu().numpy()
    return e / (np.linalg.norm(e) + 1e-9)


def cos(a, b) -> float:
    a, b = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    return float(a @ b / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9))


def load_profile() -> dict | None:
    try:
        return json.loads(PROFILE.read_text())
    except (OSError, ValueError):
        return None


def save_profile(p: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    tmp = PROFILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(p))
    os.chmod(tmp, 0o600)
    tmp.replace(PROFILE)
    os.chmod(PROFILE, 0o600)


def negatives() -> list[list[float]]:
    try:
        return json.loads(NEG_FILE.read_text()).get("prints") or []
    except (OSError, ValueError):
        return []


def verdict(score: float | None, speech_s: float, prof: dict | None) -> str:
    if prof is None or score is None or speech_s < MIN_SPEECH_S:
        return "unknown"
    th = prof.get("thresholds") or PROVISIONAL
    if score >= th["accept"]:
        return "madhav"
    if score < th["reject"]:
        return "not_madhav"
    return "unknown"


def calibrate(prints: list[np.ndarray], negs: list[list[float]]) -> dict:
    """Accept line from his own clips (leave-one-out), reject line from the synthetic other voices; provisional if they don't separate."""
    loo = []
    for i, e in enumerate(prints):
        rest = [p for j, p in enumerate(prints) if j != i]
        m = np.mean(rest, axis=0)
        loo.append(cos(e, m))
    avg = np.mean(prints, axis=0)
    neg = [cos(n, avg) for n in negs]
    lo_self = float(np.min(loo)) if loo else None
    hi_neg = float(np.max(neg)) if neg else None
    accept = PROVISIONAL["accept"] if lo_self is None else float(np.clip(lo_self - 0.08, 0.45, 0.75))
    reject = PROVISIONAL["reject"] if hi_neg is None else float(np.clip(hi_neg + 0.05, 0.15, 0.45))
    provisional = lo_self is None or hi_neg is None
    overlap = lo_self is not None and hi_neg is not None and hi_neg + 0.05 >= lo_self - 0.08   # an other voice scores like his own clips
    if overlap or reject >= accept - 0.05:          # too close to separate: keep a wide unknown band, and say it is provisional
        accept, reject, provisional = max(accept, min(0.75, reject + 0.10)), min(reject, accept - 0.10), True
    return {"accept": round(accept, 3), "reject": round(reject, 3), "provisional": provisional,
            "self_loo": [round(x, 3) for x in loo], "neg_scores": [round(x, 3) for x in neg],
            "basis": "accept = his weakest leave-one-out clip minus 0.08 (0.45-0.75); reject = the closest synthetic other voice plus 0.05 (0.15-0.45)"}


def _pcm(b64: str) -> np.ndarray:
    raw = base64.b64decode(b64)
    if len(raw) > 16000 * 4 * 40:
        raise HTTPException(400, "clip too long (40 s max)")
    return np.frombuffer(raw, dtype="<f4")


class PcmReq(BaseModel):
    pcm_b64: str                      # 16 kHz mono float32 little-endian, the speech part of the clip
    speech_s: float | None = None


@app.on_event("startup")
def _warm() -> None:
    def go():
        try:
            embed(np.zeros(SR, dtype=np.float32) + 1e-4)
        except Exception:  # noqa: BLE001 - the first real call loads it
            pass
    threading.Thread(target=go, daemon=True).start()


@app.get("/health")
def health() -> dict:
    p = load_profile()
    return {"ok": True, "model": MODEL_ID, "loaded": _model is not None, "enrolled": bool(p), "pending": len(_pending)}


@app.post("/score")
def score(b: PcmReq) -> dict:
    t0 = time.time()
    pcm = _pcm(b.pcm_b64)
    speech_s = float(b.speech_s if b.speech_s is not None else pcm.size / SR)
    prof = load_profile()
    if prof is None:
        return {"speaker": "unknown", "score": None, "enrolled": False, "speech_s": round(speech_s, 2), "ms": int(1000 * (time.time() - t0))}
    if speech_s < MIN_SPEECH_S or pcm.size < SR // 2:
        return {"speaker": "unknown", "score": None, "enrolled": True, "speech_s": round(speech_s, 2), "why": "too little speech",
                "ms": int(1000 * (time.time() - t0))}
    s = cos(embed(pcm), prof["print"])
    return {"speaker": verdict(s, speech_s, prof), "score": round(s, 3), "enrolled": True, "speech_s": round(speech_s, 2),
            "thresholds": {k: prof["thresholds"][k] for k in ("accept", "reject", "provisional")}, "ms": int(1000 * (time.time() - t0))}


@app.post("/enrol")
def enrol(b: PcmReq) -> dict:
    """Add one read sentence. After MIN_CLIPS the profile is (re)built; up to MAX_CLIPS are used."""
    pcm = _pcm(b.pcm_b64)
    speech_s = float(b.speech_s if b.speech_s is not None else pcm.size / SR)
    if speech_s < MIN_SPEECH_S:
        return {"ok": False, "why": f"only {speech_s:.1f} s of speech: please read the whole sentence", "count": len(_pending), "need": MIN_CLIPS}
    if len(_pending) >= MAX_CLIPS:
        _pending.pop(0)
    _pending.append(embed(pcm).tolist())
    out = {"ok": True, "count": len(_pending), "need": MIN_CLIPS, "done": False}
    if len(_pending) >= MIN_CLIPS:
        prints = [np.asarray(p, dtype=np.float32) for p in _pending]
        avg = np.mean(prints, axis=0)
        avg = avg / (np.linalg.norm(avg) + 1e-9)
        th = calibrate(prints, negatives())
        save_profile({"print": [round(float(x), 6) for x in avg], "count": len(prints), "model": MODEL_ID,
                      "enrolled_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "thresholds": th})
        out.update({"done": True, "thresholds": {k: th[k] for k in ("accept", "reject", "provisional")}, "self_scores": th["self_loo"]})
    return out


@app.get("/enrol/status")
def enrol_status() -> dict:
    p = load_profile()
    return {"enrolled": bool(p), "pending": len(_pending), "need": MIN_CLIPS,
            **({"count": p.get("count"), "enrolled_at": p.get("enrolled_at"), "model": p.get("model"),
                "thresholds": {k: p["thresholds"][k] for k in ("accept", "reject", "provisional")}} if p else {})}


@app.post("/enrol/reset")
def enrol_reset() -> dict:
    _pending.clear()
    try:
        PROFILE.unlink()
    except FileNotFoundError:
        pass
    return {"ok": True, "enrolled": False}


@app.post("/enrol/start")
def enrol_start() -> dict:
    """A fresh enrolment (the old profile stays in use until the new one has MIN_CLIPS clips)."""
    _pending.clear()
    return {"ok": True, "pending": 0, "need": MIN_CLIPS}


@app.post("/negatives")
def set_negatives(b: dict) -> dict:
    """Store prints of synthetic other voices (built by make_negatives in the voice server, from the Mac's 'say' voices)."""
    prints = []
    for x in b.get("pcm_b64") or []:
        pcm = _pcm(x)
        if pcm.size >= SR:
            prints.append([round(float(v), 6) for v in embed(pcm)])
    HOME.mkdir(parents=True, exist_ok=True)
    NEG_FILE.write_text(json.dumps({"prints": prints, "voices": b.get("voices") or [], "model": MODEL_ID,
                                    "made_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}))
    return {"ok": True, "n": len(prints)}
