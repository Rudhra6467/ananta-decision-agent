"""Natural voice for Ananta: Gemini text-to-speech, one clip per sentence.

The app asks for all sentences of an answer at once (prepare), then plays them in order (audio).
Each sentence is made in parallel, so the first one is ready quickly and the highlights can follow
the voice exactly: the app points at a spot when that sentence's clip starts playing.
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


def _speak(text: str, voice: str, post=None) -> bytes:
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
                _cache[cid] = _pool.submit(_speak, t, voice, post)
            _cache.move_to_end(cid)
            ids.append(cid)
        while len(_cache) > 300:
            _cache.popitem(last=False)
    return ids


def audio(cid: str, wait_s: float = 25) -> bytes:
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
