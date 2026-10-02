"""Natural voice for Ananta.

Current path (the app uses this): ONE audio file per answer, in ONE voice, made by Kokoro on this Mac (free, unlimited),
with the start time of every sentence, so the phone highlights things exactly as each sentence is spoken.
  prepare_answer()  starts making it (also called the moment an answer is written, so it is usually ready before the phone asks)
  answer_meta()     waits for it: id, sentence start times, length
  answer_audio()    the MP3
If the Mac's voice server is not running, this fails and the phone uses its own voice for the whole answer: never a mix of
voices inside one answer.

Older per-sentence clips (prepare / audio, with Gemini text-to-speech as a backup) are kept for compatibility only.
Audio is kept in memory only (a short cache), never stored on disk.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import struct
import threading
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor

# (model, takes a spoken style hint). Tested 2026-10-02: 2.5 follows "Say ...: <line>" and speaks only the line;
# the 3.8 models read such a hint out loud, so they get the plain line.
MODELS = [("gemini-2.5-flash-preview-tts", True), ("gemini-3.8-flash-tts", False), ("gemini-3.8-flash-lite-tts", False)]
VOICES = {"Calm": "Sulafat", "Friendly": "Achird", "Deep": "Charon", "Bright": "Aoede"}
DEFAULT_VOICE = "Calm"
STYLE = "Say in a calm, warm, relaxed and unhurried voice, like a friendly assistant talking to a friend: "

_pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix="tts")
_cache: "OrderedDict[str, Future]" = OrderedDict()
_lock = threading.Lock()
_cool: dict[str, float] = {}           # model -> time it may be tried again


def sentences(text: str) -> list[str]:
    return [x.strip() for x in re.split(r"(?<=[.!?])\s+", text or "") if x.strip()]


def _wav(pcm: bytes, rate: int = 24000) -> bytes:
    head = b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
    return head + b"data" + struct.pack("<I", len(pcm)) + pcm


LOCAL = os.getenv("ANANTA_VOICE_URL", "http://127.0.0.1:8200")


def _local(text: str, voice: str) -> bytes | None:
    """Kokoro on this Mac: free, unlimited, ~0.3 s a sentence. None when the local voice server is not running."""
    if os.getenv("ANANTA_VOICE_LOCAL", "1") != "1":
        return None
    try:
        req = urllib.request.Request(LOCAL + "/tts", data=json.dumps({"text": text, "voice": voice, "speed": 0.95}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=20) as r:
            wav = r.read()
        return wav if wav[:4] == b"RIFF" else None
    except Exception:  # noqa: BLE001
        return None


def _speak(text: str, voice: str, post=None) -> bytes:
    if post is None:
        wav = _local(text, voice)
        if wav:
            return wav
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    err = "no voice model available"
    for m, styled in MODELS:
        if _cool.get(m, 0) > time.time():
            continue
        body = {"contents": [{"parts": [{"text": (STYLE + text) if styled else text}]}],
                "generationConfig": {"responseModalities": ["AUDIO"],
                                     "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICES.get(voice, VOICES[DEFAULT_VOICE])}}}}}
        try:
            if post:
                r = post(m, body)
            else:
                req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                                             data=json.dumps(body).encode(), headers={"Content-Type": "application/json", "x-goog-api-key": key})
                r = json.load(urllib.request.urlopen(req, timeout=25))
            part = next(p["inlineData"] for p in r["candidates"][0]["content"]["parts"] if p.get("inlineData"))
            raw = base64.b64decode(part["data"])
            mime = part.get("mimeType", "").lower()
            if "wav" in mime or raw[:4] == b"RIFF":
                wav = raw
            else:
                wav = _wav(raw, int((re.search(r"rate=(\d+)", mime) or [None, 24000])[1]))
            if duration_s(wav) > 2.5 + 0.8 * len(text.split()):      # it read more than the line (e.g. the style hint): don't play it
                _cool[m] = time.time() + 600
                err = f"{m}: spoke extra words"
                continue
            return wav
        except urllib.error.HTTPError as e:
            err = f"{m}: HTTP {e.code}"
            _cool[m] = time.time() + (3600 if e.code == 429 else 60)
        except Exception as e:  # noqa: BLE001
            err = f"{m}: {type(e).__name__}"
            _cool[m] = time.time() + 30
    raise RuntimeError(err)


FFMPEG = next((p for p in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/usr/bin/ffmpeg") if os.path.exists(p)), None)


def to_mp3(wav: bytes) -> tuple[bytes, str]:
    """Phones get small MP3s (about 10x smaller than WAV), so each sentence arrives quickly over the tunnel."""
    if not FFMPEG:
        return wav, "audio/wav"
    import subprocess

    try:
        out = subprocess.run([FFMPEG, "-loglevel", "error", "-f", "wav", "-i", "pipe:0", "-ac", "1", "-codec:a", "libmp3lame", "-b:a", "64k", "-f", "mp3", "pipe:1"],
                             input=wav, capture_output=True, timeout=15).stdout
        return (out, "audio/mpeg") if len(out) > 200 else (wav, "audio/wav")
    except Exception:  # noqa: BLE001
        return wav, "audio/wav"


def _speak_mp3(text: str, voice: str, post=None) -> tuple[bytes, str]:
    wav = _speak(text, voice, post)
    return to_mp3(wav) if post is None else (wav, "audio/wav")


def clip_id(text: str, voice: str) -> str:
    return hashlib.sha1(f"{voice}|{text}".encode()).hexdigest()[:20]


def prepare(texts: list[str], voice: str = DEFAULT_VOICE, post=None) -> list[str]:
    """Start making a clip for each sentence (in parallel); returns their ids right away."""
    ids = []
    with _lock:
        for t in texts[:30]:
            t = t.strip()[:600]
            if not t:
                continue
            cid = clip_id(t, voice)
            if cid not in _cache:
                _cache[cid] = _pool.submit(_speak_mp3, t, voice, post)
            _cache.move_to_end(cid)
            ids.append(cid)
        while len(_cache) > 300:
            _cache.popitem(last=False)
    return ids


def audio(cid: str, wait_s: float = 25) -> tuple[bytes, str]:
    """-> (audio bytes, content type)"""
    with _lock:
        f = _cache.get(cid)
    if not f:
        raise KeyError("unknown clip")
    return f.result(timeout=wait_s)


def duration_s(wav: bytes) -> float:
    try:
        rate = struct.unpack("<I", wav[24:28])[0]
        return round((len(wav) - 44) / (rate * 2), 2)
    except Exception:  # noqa: BLE001
        return 0.0


# ---------------------------------------------------------------------------
# One file per answer (current path)
# ---------------------------------------------------------------------------
_answers: "OrderedDict[str, Future]" = OrderedDict()


def norm_sentences(texts: list[str]) -> list[str]:
    return [t.strip()[:600] for t in (texts or []) if t and t.strip()][:40]


def answer_key(sents: list[str], voice: str, speed: float) -> str:
    return hashlib.sha1(f"{voice}|{float(speed):.2f}|".encode() + "\n".join(sents).encode()).hexdigest()[:24]


def _make_answer(sents: list[str], voice: str, speed: float) -> dict:
    if os.getenv("ANANTA_VOICE_LOCAL", "1") != "1":
        raise RuntimeError("the Mac's voice is switched off")
    req = urllib.request.Request(LOCAL + "/speak", data=json.dumps({"sentences": sents, "voice": voice, "speed": speed}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    return {"audio": base64.b64decode(d["audio_b64"]), "mime": d.get("mime", "audio/mpeg"), "offsets": d["offsets"],
            "duration": d["duration"], "engine": "kokoro", "voice": d.get("voice", voice), "ms": d.get("ms")}


def prepare_answer(texts: list[str], voice: str = DEFAULT_VOICE, speed: float = 0.9, make=None) -> str:
    """Start making the whole answer's audio (if not already made or being made); returns its id at once."""
    sents = norm_sentences(texts)
    speed = round(max(0.6, min(1.5, float(speed or 0.9))), 2)
    key = answer_key(sents, voice, speed)
    with _lock:
        f = _answers.get(key)
        if f is not None and f.done() and f.exception() is not None:
            f = None                                  # an earlier try failed (voice server was down): try again
        if f is None and sents:
            _answers[key] = _pool.submit(make or _make_answer, sents, voice, speed)
        if key in _answers:
            _answers.move_to_end(key)
        while len(_answers) > 120:
            _answers.popitem(last=False)
    return key


def _answer(key: str, wait_s: float) -> dict:
    with _lock:
        f = _answers.get(key)
    if f is None:
        raise KeyError("unknown answer audio")
    return f.result(timeout=wait_s)


def answer_meta(key: str, wait_s: float = 25) -> dict:
    a = _answer(key, wait_s)
    return {"id": key, "offsets": a["offsets"], "duration": a["duration"], "engine": a["engine"], "voice": a.get("voice"),
            "mime": a["mime"], "bytes": len(a["audio"]), "ms": a.get("ms")}


def answer_audio(key: str, wait_s: float = 25) -> tuple[bytes, str]:
    a = _answer(key, wait_s)
    return a["audio"], a["mime"]
