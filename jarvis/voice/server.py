"""Ananta's local voice, on the Mac (Apple Silicon, MLX). Free and unlimited, nothing leaves the machine.

    ~/ananta_venvs/voice/bin/python -m uvicorn jarvis.voice.server:app --host 127.0.0.1 --port 8200

POST /tts  {"text", "voice": "Calm|Friendly|Deep|Bright", "speed": 0.8-1.3}  -> audio/wav (Kokoro 82M)
POST /stt  {"audio_b64", "mime"}                                       -> {"text", "ms"} (Whisper large-v3-turbo)
GET  /health
Only the Jarvis service on this Mac talks to it (bound to 127.0.0.1).
"""
from __future__ import annotations

import base64
import io
import os
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
VOICES = {"Calm": "af_heart", "Friendly": "af_bella", "Deep": "am_michael", "Bright": "bf_emma"}
STT_PROMPT = ("Madhav talking to Ananta, a crypto trading assistant. Bitcoin, Ethereum, Solana, Cardano, Dogecoin, Avalanche, "
              "Bitcoin Cash, Chainlink, Litecoin, XRP. Hunter, Squeeze, Explorer, setup, scan, portfolio, mandate, evidence, repair shop.")

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
    ext = ".m4a" if "m4a" in b.mime or "mp4" in b.mime else ".wav"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(raw)
        p = f.name
    t0 = time.time()
    try:
        text = stt_file(p)
    finally:
        os.unlink(p)
    # Whisper sometimes "hears" its prompt or stock phrases in silence: treat those as nothing said
    if text.lower().strip(" .") in ("", "thank you", "thanks for watching", "you") or text.startswith("Madhav talking to Ananta"):
        text = ""
    return {"text": text, "ms": int(1000 * (time.time() - t0))}
