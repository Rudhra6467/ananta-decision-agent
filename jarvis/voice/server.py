"""Ananta's local voice, on the Mac (Apple Silicon, MLX). Free and unlimited, nothing leaves the machine.

    ~/ananta_venvs/voice/bin/python -m uvicorn jarvis.voice.server:app --host 127.0.0.1 --port 8200

POST /tts   {"text", "voice": "Calm|Friendly|Deep|Bright|British", "speed": 0.8-1.3}  -> audio/wav (Kokoro 82M)
POST /speak {"sentences", "voice", "speed"} -> {"audio_b64" (mp3), "offsets", "duration"}: a whole answer in one file
POST /stt  {"audio_b64", "mime"}                                       -> {"text", "ms"} (Whisper large-v3-turbo)
GET  /health
Only the Jarvis service on this Mac talks to it (bound to 127.0.0.1).
"""
from __future__ import annotations

import base64
import io
import os
import shutil
import subprocess
import tempfile
import threading
import time

import numpy as np
import soundfile as sf
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

TTS_MODEL = os.getenv("VOICE_TTS_MODEL", "mlx-community/Kokoro-82M-bf16")
STT_MODEL = os.getenv("VOICE_STT_MODEL", "mlx-community/whisper-large-v3-turbo")
VOICES = {"Calm": "af_heart", "Friendly": "af_bella", "Deep": "am_michael", "Bright": "bf_emma", "British": "bm_george"}
STT_PROMPT = ("Madhav talking to Ananta, a crypto trading assistant. Hey there. Hey Jarvis. Walk me through it. Bitcoin, Ethereum, Solana, "
              "Cardano, Dogecoin, Avalanche, Bitcoin Cash, Chainlink, Litecoin, XRP. Hunter, Squeeze, Explorer, trend portfolio, T3, zones, "
              "stop loss, the short dip trade, setup, scan, portfolio, mandate, evidence, repair shop.")

app = FastAPI(title="Ananta voice", docs_url=None, redoc_url=None, openapi_url=None)
_lock = threading.Lock()          # MLX: one job at a time
_tts = None


def tts_model():
    global _tts
    if _tts is None:
        from mlx_audio.tts.utils import load

        _tts = load(TTS_MODEL)
    return _tts


@app.on_event("startup")
def _warm() -> None:
    def go():
        try:
            synth("Ready.", "Calm", 1.0)
            stt_file(None)
        except Exception as exc:  # noqa: BLE001
            print("warm-up:", exc)
    threading.Thread(target=go, daemon=True).start()


def synth(text: str, voice: str, speed: float) -> bytes:
    with _lock:
        m = tts_model()
        parts = [np.array(r.audio).reshape(-1) for r in m.generate(text=text, voice=VOICES.get(voice, voice if "_" in voice else "af_heart"),
                                                                   speed=speed, lang_code=VOICES.get(voice, "a_")[0])]
    audio = np.concatenate(parts) if parts else np.zeros(1, dtype=np.float32)
    buf = io.BytesIO()
    sf.write(buf, audio, 24000, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def stt_file(path: str | None) -> str:
    import mlx_whisper

    if path is None:                       # warm-up: load the model with a second of silence
        path = os.path.join(tempfile.gettempdir(), "ananta_silence.wav")
        sf.write(path, np.zeros(16000, dtype=np.float32), 16000)
    with _lock:
        r = mlx_whisper.transcribe(path, path_or_hf_repo=STT_MODEL, language="en", initial_prompt=STT_PROMPT,
                                   condition_on_previous_text=False, temperature=0.0)
    return (r.get("text") or "").strip()


def encode_mp3(audio: np.ndarray, rate: int = 24000) -> tuple[bytes, str]:
    """Small MP3 for the phone (about 10x smaller than WAV); WAV if ffmpeg is missing."""
    buf = io.BytesIO()
    sf.write(buf, audio, rate, format="WAV", subtype="PCM_16")
    wav = buf.getvalue()
    ff = shutil.which("ffmpeg") or ("/opt/homebrew/bin/ffmpeg" if os.path.exists("/opt/homebrew/bin/ffmpeg") else None)
    if not ff:
        return wav, "audio/wav"
    try:
        out = subprocess.run([ff, "-loglevel", "error", "-f", "wav", "-i", "pipe:0", "-ac", "1", "-codec:a", "libmp3lame", "-b:a", "64k", "-f", "mp3", "pipe:1"],
                             input=wav, capture_output=True, timeout=20).stdout
        return (out, "audio/mpeg") if len(out) > 200 else (wav, "audio/wav")
    except Exception:  # noqa: BLE001
        return wav, "audio/wav"


class SpeakReq(BaseModel):
    sentences: list[str]
    voice: str = "Calm"
    speed: float = 1.0
    gap: float = 0.26


def trim(a: np.ndarray, rate: int = 24000, lead: float = 0.03, tail: float = 0.06) -> np.ndarray:
    """Cut the model's own silence at both ends of a sentence, keeping a breath of it, so the pauses between sentences are
    the ones we choose (fixed padding made every answer sound like a list being read out)."""
    if a.size == 0:
        return a
    loud = np.flatnonzero(np.abs(a) > 0.012)
    if loud.size == 0:
        return a
    s = max(0, int(loud[0] - lead * rate))
    e = min(a.size, int(loud[-1] + tail * rate))
    return a[s:e]


def pause_after(sentence: str, base: float) -> float:
    """A person pauses longer after a question, shorter after a short phrase; a little variation so it never sounds metronomic."""
    s = sentence.strip()
    words = len(s.split())
    f = 1.5 if s.endswith("?") else 1.15 if s.endswith("!") else 0.8 if s.endswith((":", ";", ",")) else 1.0
    if words <= 4:
        f *= 0.7
    jitter = 0.9 + 0.2 * ((sum(map(ord, s)) % 97) / 96)            # deterministic per sentence: same text, same audio
    return max(0.08, min(0.7, base * f * jitter))


@app.post("/speak")
def speak(b: SpeakReq) -> dict:
    """A whole answer as ONE audio file in ONE voice, plus where each sentence starts (seconds), so the phone can
    highlight in step with the voice. Loudness is evened out so every answer plays at the same level."""
    sents = [x.strip()[:600] for x in b.sentences if x and x.strip()][:40]
    if not sents:
        raise HTTPException(400, "no text")
    t0 = time.time()
    rate = 24000
    vid = VOICES.get(b.voice, b.voice if "_" in b.voice else "af_heart")
    speed = max(0.6, min(1.5, b.speed))
    base_gap = max(0.0, min(1.0, b.gap))
    chunks, offsets, t = [], [], 0.0
    with _lock:
        m = tts_model()
        for i, x in enumerate(sents):
            parts = [np.array(r.audio, dtype=np.float32).reshape(-1) for r in m.generate(text=x, voice=vid, speed=speed, lang_code=vid[0])]
            a = trim(np.concatenate(parts)) if parts else np.zeros(int(rate * 0.2), dtype=np.float32)
            offsets.append(round(t, 3))
            chunks.append(a)
            t += len(a) / rate
            if i < len(sents) - 1:
                gap = np.zeros(int(rate * pause_after(x, base_gap)), dtype=np.float32)
                chunks.append(gap)
                t += len(gap) / rate
    audio = np.concatenate(chunks).astype(np.float32)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 1e-4:
        audio = audio * min(4.0, 0.89 / peak)
    data, mime = encode_mp3(audio, rate)
    return {"audio_b64": base64.b64encode(data).decode(), "mime": mime, "offsets": offsets, "duration": round(t, 3),
            "voice": vid, "ms": int(1000 * (time.time() - t0))}


def voiced_seconds(path: str) -> float:
    """Seconds of the clip that are clearly louder than near-silence (20 ms frames above about -35 dBFS)."""
    try:
        a, rate = sf.read(path, dtype="float32", always_2d=False)
        if a.ndim > 1:
            a = a.mean(axis=1)
        n = max(1, int(rate * 0.02))
        frames = a[: len(a) // n * n].reshape(-1, n)
        rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
        return float((rms > 0.0178).sum() * 0.02)
    except Exception:  # noqa: BLE001
        return 1.0                                       # can't tell: don't drop anything


class TTSReq(BaseModel):
    text: str
    voice: str = "Calm"
    speed: float = 0.95


class STTReq(BaseModel):
    audio_b64: str
    mime: str = "audio/wav"


@app.get("/health")
def health() -> dict:
    return {"ok": True, "tts": TTS_MODEL, "stt": STT_MODEL, "tts_loaded": _tts is not None, "voices": list(VOICES)}


@app.post("/tts")
def tts(b: TTSReq):
    t = (b.text or "").strip()[:800]
    if not t:
        raise HTTPException(400, "no text")
    t0 = time.time()
    wav = synth(t, b.voice, max(0.6, min(1.5, b.speed)))
    return Response(content=wav, media_type="audio/wav", headers={"X-Gen-Ms": str(int(1000 * (time.time() - t0)))})


@app.post("/stt")
def stt(b: STTReq) -> dict:
    raw = base64.b64decode(b.audio_b64)
    if len(raw) > 12_000_000:
        raise HTTPException(400, "audio too long")
    ext = (".m4a" if "m4a" in b.mime or "mp4" in b.mime else ".webm" if "webm" in b.mime else ".ogg" if "ogg" in b.mime
           else ".wav")                                   # the website records WebM (Chrome) or MP4 (Safari); ffmpeg reads them all
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(raw)
        p = f.name
    t0 = time.time()
    try:
        voiced = voiced_seconds(p)
        text = stt_file(p)
    finally:
        os.unlink(p)
    # Whisper sometimes "hears" its prompt or stock phrases in near-silence. Drop those only when there was almost no
    # real speech in the clip, so a real "thank you" from Madhav still gets an answer.
    stock = text.lower().strip(" .!") in ("", "thank you", "thanks for watching", "you", "bye")
    if text.startswith("Madhav talking to Ananta") or (stock and voiced < 0.35):
        text = ""
    return {"text": text, "ms": int(1000 * (time.time() - t0))}
