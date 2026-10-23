"""India voice (V3, first version, 23 Oct): the same voice loop the crypto app runs, on the same local voice server (Whisper hears,
Kokoro speaks), with India's own voice. hear -> India Ask -> speak. No cloud voice; every clip is made on the Mac.
  /v3/voice/transcribe  audio -> text (Whisper on 127.0.0.1:8200 /stt)
  /v3/voice/turn        audio -> text -> India Ask -> the reply, with what was heard
  /v3/voice/answer      sentences -> one mp3 with sentence start times (Kokoro /speak), kept in memory by key; /answer/{key} and /answer/{key}/audio
  /v3/voice/prepare     sentences -> clip ids; /clip/{id} plays each
Telugu is not wired here yet (Madhav, 23 Oct: the last step); the Telugu server and states exist and wait for it.
"""
from __future__ import annotations

import base64
import hashlib
import os
import re
import threading
from collections import OrderedDict

import requests

VOICE_URL = os.getenv("ANANTA_VOICE_URL", "http://127.0.0.1:8200")
INDIA_VOICE = os.getenv("ANANTA_INDIA_VOICE", "bm_lewis")
_lock = threading.Lock()
_answers: OrderedDict[str, dict] = OrderedDict()
_clips: OrderedDict[str, dict] = OrderedDict()
MAX_KEEP = 120


def sentences(texts: list[str]) -> list[str]:
    out = []
    for t in texts:
        for s in re.split(r"(?<=[.!?])\s+", str(t or "").strip()):
            s = s.strip()
            if s:
                out.append(s[:400])
    return out[:40]


def _key(sents: list[str], voice: str, speed: float) -> str:
    return hashlib.sha1(("|".join(sents) + f"|{voice}|{speed}").encode()).hexdigest()[:16]


def _speak(sents: list[str], speed: float = 1.0, post=None) -> dict:
    post = post or (lambda url, body: requests.post(url, json=body, timeout=300).json())
    j = post(f"{VOICE_URL}/speak", {"sentences": sents, "voice": INDIA_VOICE, "speed": max(0.6, min(1.5, float(speed or 1.0)))})
    return {"audio": base64.b64decode(j["audio_b64"]), "mime": j.get("mime", "audio/mpeg"), "offsets": j.get("offsets", []), "duration": j.get("duration", 0.0),
            "engine": "kokoro", "voice": INDIA_VOICE, "ms": j.get("ms")}


def prepare_answer(texts: list[str], speed: float = 1.0, post=None) -> dict:
    """The whole answer as one file; made now (local, a few seconds) and kept by key."""
    sents = sentences(texts)
    key = _key(sents, INDIA_VOICE, speed)
    with _lock:
        a = _answers.get(key)
    if a is None:
        a = _speak(sents, speed, post) if sents else {"audio": b"", "mime": "audio/mpeg", "offsets": [], "duration": 0.0, "engine": "kokoro", "voice": INDIA_VOICE, "ms": 0}
        with _lock:
            _answers[key] = a
            while len(_answers) > MAX_KEEP:
                _answers.popitem(last=False)
    return {"id": key, "offsets": a["offsets"], "duration": a["duration"], "engine": a["engine"], "voice": a["voice"], "mime": a["mime"], "bytes": len(a["audio"]), "ms": a.get("ms")}


def answer_meta(key: str) -> dict:
    with _lock:
        a = _answers[key]
    return {"id": key, "offsets": a["offsets"], "duration": a["duration"], "engine": a["engine"], "voice": a["voice"], "mime": a["mime"], "bytes": len(a["audio"]), "ms": a.get("ms")}


def answer_audio(key: str) -> tuple[bytes, str]:
    with _lock:
        a = _answers[key]
    return a["audio"], a["mime"]


def prepare(texts: list[str], post=None) -> list[str]:
    ids = []
    for s in sentences(texts):
        cid = _key([s], INDIA_VOICE, 1.0)
        with _lock:
            have = cid in _clips
        if not have:
            a = _speak([s], 1.0, post)
            with _lock:
                _clips[cid] = a
                while len(_clips) > MAX_KEEP:
                    _clips.popitem(last=False)
        ids.append(cid)
    return ids


def clip(cid: str) -> tuple[bytes, str]:
    with _lock:
        a = _clips[cid]
    return a["audio"], a["mime"]


def transcribe(audio_b64: str, mime: str, post=None) -> str:
    post = post or (lambda url, body: requests.post(url, json=body, timeout=120).json())
    j = post(f"{VOICE_URL}/stt", {"audio_b64": audio_b64, "mime": mime or "audio/webm", "language": "en"})
    return str(j.get("text") or "").strip()


FILLER = re.compile(r"^(um+|uh+|hmm+|okay|ok|yeah|thanks?|thank you)[.!]?$", re.I)


def turn(who: str, audio_b64: str, mime: str, thread: str | None, mode: str | None, context: dict | None, ask_fn, post=None) -> dict:
    heard = transcribe(audio_b64, mime, post)
    if not heard:
        return {"heard": "", "thread": thread, "error": "I didn't catch any words. Try again a little closer to the phone."}
    if FILLER.match(heard.strip()):
        return {"heard": heard, "thread": thread, "ignored": "filler"}
    out = ask_fn(who, heard, thread=thread, mode=mode, context=context, voice=True)
    return {"heard": heard, **out}
