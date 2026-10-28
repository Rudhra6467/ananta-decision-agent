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
# 25 Oct (India voice refinement): India's voice was heard with the crypto prompt above ("Bitcoin, Solana, Hunter ..."), so Whisper leaned toward
# crypto words while Madhav talked about the Nifty, Zerodha and his holdings. India sends context "india" and gets its own words.
STT_PROMPT_INDIA = ("Madhav talking to Ananta, an Indian stock market trading assistant. Hey Ananta. Walk me through it. Nifty, Nifty 50, Bank Nifty, "
                    "Sensex, NSE, BSE, Zerodha, Kite, India VIX, F and O, options, straddle, expiry, lot, rupees, lakh, crore, pullback, breakout, "
                    "reversal, portfolio, holdings, morning view, reconstruction, flag it, fix one, fix two, fix three. Reliance, Tata Power, "
                    "Jio Financial, HDFC Bank, Infosys, ICICI Bank, Tata Motors.")

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


def stt_prompt(names: str = "", context: str = "") -> str:
    """The English prompt plus the names to expect (request #35: 'Madhav' came out as 'Mahider'); at most 12 names, letters only.
    context "india" uses India's words (Nifty, Zerodha ...) instead of crypto's."""
    ns = [n.strip() for n in (names or "").split(",") if n.strip() and all(c.isalpha() or c in " '-&" for c in n.strip())][:12]
    return (STT_PROMPT_INDIA if context == "india" else STT_PROMPT) + (" Names: " + ", ".join(ns) + "." if ns else "")


LOOP_MIN = 6           # a word or 2-3 word phrase repeated this often, making up half the transcript, is a Whisper loop, not speech
SR = 16000


def is_loop(text: str) -> bool:
    """27 Oct: "TATAPOWER, TATAPOWER, TATAPOWER, ..." twice in one morning: on a noisy or half-heard clip Whisper repeats its prompt's names."""
    from collections import Counter
    import re
    words = re.findall(r"[a-z0-9']+", (text or "").lower())
    if len(words) < 8:
        return False
    for k in (1, 2, 3):
        grams = [" ".join(words[i:i + k]) for i in range(0, len(words) - k + 1)]
        g, c = Counter(grams).most_common(1)[0]
        if c >= LOOP_MIN and c * k >= 0.5 * len(words):
            return True
    return False


def _keep(seg: dict) -> bool:
    """Whisper's own guards: a segment it rates as probably no speech (and not confidently decoded), or one that compresses like a loop, is dropped."""
    if (seg.get("no_speech_prob") or 0) > 0.6 and (seg.get("avg_logprob") or 0) < -1.0:
        return False
    return (seg.get("compression_ratio") or 0) <= 2.4


def _decode(audio, language, prompt):
    import mlx_whisper
    with _lock:
        r = mlx_whisper.transcribe(audio, path_or_hf_repo=STT_MODEL, language=language, initial_prompt=prompt,
                                   condition_on_previous_text=False, temperature=0.0)
    segs = r.get("segments") or []
    raw = (r.get("text") or "").strip()
    kept = " ".join((x.get("text") or "").strip() for x in segs if _keep(x)).strip() if segs else raw
    return kept, raw


def voiced(a: np.ndarray, rate: int = SR, thr: float = 0.01) -> tuple[np.ndarray, float]:
    """The clip with leading and trailing near-silence cut (a quarter second kept each side) and how many seconds are clearly above it
    (20 ms frames over about -40 dBFS). Works on any format, since the audio comes decoded from ffmpeg."""
    n = max(1, int(rate * 0.02))
    if a.size < n:
        return a, 0.0
    frames = a[: a.size // n * n].reshape(-1, n)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    idx = np.flatnonzero(rms > thr)
    if not idx.size:
        return a[:0], 0.0
    pad = int(0.25 * rate)
    return a[max(0, idx[0] * n - pad): min(a.size, (idx[-1] + 1) * n + pad)], float(idx.size * 0.02)


def stt_file(path: str | None, language: str | None = "en", names: str = "", context: str = "", info: dict | None = None) -> str:
    """language "en" for Madhav; None lets Whisper detect it (Telugu conversations with his family, Oct 11).
    27 Oct: silence trimmed first (a clip with almost no speech returns ""), Whisper's no-speech and loop guards applied per segment, and a
    transcript that is still a repetition loop is decoded once more without any prompt before giving up ("" = "please say it again")."""
    from mlx_whisper.audio import load_audio

    info = info if info is not None else {}
    if path is None:                       # warm-up: load the model with a second of silence
        path = os.path.join(tempfile.gettempdir(), "ananta_silence.wav")
        sf.write(path, np.zeros(16000, dtype=np.float32), 16000)
        _decode(path, language, None)
        return ""
    try:
        a = load_audio(path)
        a, secs = voiced(a)
    except Exception as exc:  # noqa: BLE001 - can't decode here: let Whisper read the file as before
        a, secs = path, None
        info["decode_error"] = str(exc)[:80]
    info["voiced_s"] = secs
    if secs is not None and not isinstance(a, str):
        info["_pcm"] = a                   # 27 Oct: the speech part, for speaker recognition (never stored)
    if secs is not None and secs < 0.25:
        info["dropped"] = "no speech"
        return ""
    prompt = stt_prompt(names, context) if language == "en" else None
    text, raw = _decode(a, language, prompt)
    if is_loop(raw) or is_loop(text) or (raw and not text):
        info["retry"] = "loop or guard: decoded again without the prompt"
        text, raw = _decode(a, language, None)
        if is_loop(text):
            info["dropped"] = "repetition loop"
            return ""
    return text


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
    tail: float = 0.0          # 27 Oct: seconds of silence after the last sentence (a piece of a streamed answer, so pieces join like sentences)


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
            if i < len(sents) - 1 or b.tail > 0:
                g = pause_after(x, base_gap) if i < len(sents) - 1 else max(0.0, min(1.0, b.tail))
                gap = np.zeros(int(rate * g), dtype=np.float32)
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
    language: str = "en"
    names: str = ""
    context: str = ""


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
    info: dict = {}
    try:
        lang = getattr(b, 'language', 'en') or 'en'
        text = stt_file(p, None if lang == 'auto' else lang, getattr(b, 'names', '') or '', getattr(b, 'context', '') or '', info)
        vs = info.get("voiced_s")
        vs = voiced_seconds(p) if vs is None else vs
    finally:
        os.unlink(p)
    # Whisper sometimes "hears" its prompt or stock phrases in near-silence. Drop those only when there was almost no
    # real speech in the clip, so a real "thank you" from Madhav still gets an answer.
    stock = text.lower().strip(" .!") in ("", "thank you", "thanks for watching", "you", "bye", "transcription by castingwords")
    if text.startswith("Madhav talking to Ananta") or text.startswith("Names:") or (stock and vs < 0.35):
        text = ""
    spk = speaker_of(info.get("_pcm"), vs) if text else {"speaker": "unknown", "score": None, "why": "no words"}
    return {"text": text, "ms": int(1000 * (time.time() - t0)), "speaker": spk,
            **({"note": info.get("dropped") or info.get("retry")} if (info.get("dropped") or info.get("retry")) else {})}


# ---- speaker recognition (Madhav, 27 Oct: "Yes for speaker recognition model"): the local service jarvis/voice/speaker.py on 8215 -------------
SPEAKER_URL = os.getenv("ANANTA_SPEAKER_URL", "http://127.0.0.1:8215")
SPEAKER_LOG = os.path.expanduser("~/ananta_data/voice/speaker_log.jsonl")


def _spk_post(path: str, body: dict | None = None, timeout: float = 2.0) -> dict:
    import json as _json
    import urllib.request
    data = None if body is None else _json.dumps(body).encode()
    req = urllib.request.Request(SPEAKER_URL + path, data=data, headers={"content-type": "application/json"}, method="GET" if body is None else "POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return _json.loads(r.read())


def _pcm_b64(a: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(a, dtype="<f4").tobytes()).decode()


def speaker_of(pcm, speech_s) -> dict:
    """Who is speaking: {"speaker": "madhav" | "not_madhav" | "unknown", "score", "enrolled"}; "unknown" whenever the service can't say.
    Logged (verdict, score, seconds; no audio) in ~/ananta_data/voice/speaker_log.jsonl."""
    if pcm is None or not hasattr(pcm, "size") or pcm.size == 0:
        return {"speaker": "unknown", "score": None, "why": "no audio to score"}
    try:
        out = _spk_post("/score", {"pcm_b64": _pcm_b64(pcm), "speech_s": float(speech_s or 0)})
    except Exception as exc:  # noqa: BLE001 - never block a transcript on it
        out = {"speaker": "unknown", "score": None, "why": f"speaker service: {str(exc)[:60]}"}
    try:
        import json as _json
        os.makedirs(os.path.dirname(SPEAKER_LOG), exist_ok=True)
        with open(SPEAKER_LOG, "a") as fh:
            fh.write(_json.dumps({"t": int(time.time()), **{k: out.get(k) for k in ("speaker", "score", "enrolled", "speech_s", "why")}}) + "\n")
    except OSError:
        pass
    return out


def _audio_pcm(audio_b64: str, mime: str) -> tuple[np.ndarray, float]:
    from mlx_whisper.audio import load_audio
    raw = base64.b64decode(audio_b64)
    if len(raw) > 12_000_000:
        raise HTTPException(400, "audio too long")
    ext = (".m4a" if "m4a" in mime or "mp4" in mime else ".webm" if "webm" in mime else ".ogg" if "ogg" in mime else ".wav")
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(raw)
        p = f.name
    try:
        return voiced(load_audio(p))
    finally:
        os.unlink(p)


class AudioReq(BaseModel):
    audio_b64: str
    mime: str = "audio/wav"


def _spk_call(fn):
    try:
        return fn()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"the speaker service did not answer ({str(exc)[:80]})") from exc


@app.post("/speaker/start")
def speaker_start() -> dict:
    return _spk_call(lambda: _spk_post("/enrol/start", {}))


@app.post("/speaker/enrol")
def speaker_enrol(b: AudioReq) -> dict:
    """One read sentence of 'Teach Ananta my voice'."""
    a, secs = _audio_pcm(b.audio_b64, b.mime)
    return _spk_call(lambda: _spk_post("/enrol", {"pcm_b64": _pcm_b64(a), "speech_s": secs}, timeout=10))


@app.get("/speaker/status")
def speaker_status() -> dict:
    return _spk_call(lambda: _spk_post("/enrol/status"))


@app.post("/speaker/reset")
def speaker_reset() -> dict:
    return _spk_call(lambda: _spk_post("/enrol/reset", {}))


@app.post("/speaker/test")
def speaker_test(b: AudioReq) -> dict:
    """'Test my voice': the score and verdict of one clip (nothing is stored)."""
    a, secs = _audio_pcm(b.audio_b64, b.mime)
    return {**speaker_of(a, secs), "speech_s": round(secs, 2)}


NEG_VOICES = ["Aman", "Rishi", "Daniel", "Fred", "Ralph", "Karen", "Moira", "Eddy (English (US))", "Grandpa (English (US))"]
NEG_TEXT = ["Ananta, how did the Nifty close today?", "Show me my holdings and the practice book.", "Yes to all your recommendations."]


@app.post("/speaker/negatives")
def speaker_negatives() -> dict:
    """Prints of the Mac's own synthetic voices ('not Madhav'), with a little room noise mixed into half, for the reject line."""
    clips, used = [], []
    rng = np.random.default_rng(7)
    with tempfile.TemporaryDirectory() as d:
        for i, v in enumerate(NEG_VOICES):
            try:
                aiff, wav = os.path.join(d, f"n{i}.aiff"), os.path.join(d, f"n{i}.wav")
                subprocess.run(["say", "-v", v, "-o", aiff, " ".join(NEG_TEXT)], check=True, timeout=60)
                subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", aiff, wav], check=True, timeout=60)
                x, _ = sf.read(wav, dtype="float32")
                clips.append(_pcm_b64(x))
                clips.append(_pcm_b64(x + rng.normal(0, 0.01, x.size).astype(np.float32)))
                used.append(v)
            except Exception:  # noqa: BLE001 - a voice not installed on this Mac
                continue
    return _spk_call(lambda: {**_spk_post("/negatives", {"pcm_b64": clips, "voices": used}, timeout=60), "voices": used})
