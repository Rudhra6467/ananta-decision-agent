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


def expected_names(n: int = 12) -> str:
    """The names Whisper is told to expect in India. 25 Oct: Madhav, then his holdings by size. 27 Oct: Madhav only. The holdings went in as
    ticker codes ("TATAPOWER, UNITDSPR, TMPV"), and on a noisy or half-heard clip Whisper repeated them back ("Nameshav, TMPV, IDEA, MARICO,
    UNITDSPR, TATAPOWER, TATAPOWER, ...", twice on the morning of 27 Oct). The India prompt already carries the spoken names (Tata Power,
    Jio Financial ...), and the India voice check heard 12 of 12 both with and without the tickers (27 Oct), so they are dropped."""
    return "Madhav"


# Indian names Whisper still bends after the India prompt (25 Oct voice check: "GIO Financial"; with the old crypto prompt also "Ziradha",
# "Tadah power" and "one lock"): put right after hearing, only these exact shapes.
HEARD_FIX = [(re.compile(r"\b(?:gio|geo|jeo)\s+(fin(?:ancial|ance)?)\b", re.I), r"Jio \1"), (re.compile(r"\bzi?radha\b|\bzerod[ah]+\b|\bzeroda\b", re.I), "Zerodha"),
             (re.compile(r"\btad(?:ah|a)?\s+power\b", re.I), "Tata Power"),
             (re.compile(r"\b(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|a)\s+locks?\b", re.I), r"\1 lakh")]


def fix_heard(text: str) -> str:
    for rx, rep in HEARD_FIX:
        text = rx.sub(rep, text)
    return text


def transcribe_full(audio_b64: str, mime: str, post=None) -> tuple[str, dict]:
    """The words and who spoke them (27 Oct: the voice server scores each clip against Madhav's enrolled voice; "unknown" when it can't say)."""
    post = post or (lambda url, body: requests.post(url, json=body, timeout=120).json())
    # context "india": the voice server uses India's words (Nifty, Zerodha, lakh ...), not the crypto prompt it used before 25 Oct
    j = post(f"{VOICE_URL}/stt", {"audio_b64": audio_b64, "mime": mime or "audio/webm", "language": "en", "context": "india", "names": expected_names()})
    spk = j.get("speaker") if isinstance(j.get("speaker"), dict) else {"speaker": "unknown", "score": None}
    return fix_heard(str(j.get("text") or "").strip()), spk


def transcribe(audio_b64: str, mime: str, post=None) -> str:
    return transcribe_full(audio_b64, mime, post)[0]


# ---- 'Teach Ananta my voice' (27 Oct): the app's enrolment screen talks to the voice server's /speaker/* routes through these
def speaker_call(path: str, body: dict | None = None, post=None) -> dict:
    if post is not None:
        return post(f"{VOICE_URL}/speaker/{path}", body or {})
    url = f"{VOICE_URL}/speaker/{path}"
    r = requests.get(url, timeout=15) if body is None else requests.post(url, json=body, timeout=60)
    r.raise_for_status()
    return r.json()


# ---- the India voice check (25 Oct refinement; crypto's is jarvis/service/exam.py voice): India phrases spoken by the Mac's own voice, heard by
# the India speech path (India prompt, his holdings as names). Free, local; run weekly with the India exam. Pass: 9 of 12 heard right.
VOICE_CHECK = [
    ("nifty", "How did the Nifty close today?", [r"nifty"]),
    ("banknifty", "What is Bank Nifty doing?", [r"bank\s*nifty"]),
    ("zerodha", "Did the Zerodha sign-in work this morning?", [r"zerodha", r"sign"]),
    ("tatapower", "Should I trim Tata Power?", [r"tata\s*power", r"trim"]),
    ("jiofin", "Why is Jio Financial rated D?", [r"jio", r"rated|rate"]),
    ("lakh", "My stocks are worth one lakh eight thousand rupees.", [r"lakh|lac", r"rupee"]),
    ("expiry", "When is the next weekly expiry?", [r"expir", r"week"]),
    ("straddle", "How did the straddle do?", [r"straddle"]),
    ("fixone", "Use fix one.", [r"fix", r"one|1"]),
    ("flag", "Flag it, the chart is wrong.", [r"flag", r"wrong"]),
    ("morning", "Open the morning view.", [r"morning", r"view"]),
    ("pullback", "How are the pullback trades doing?", [r"pull\s*-?\s*back", r"trade"]),
]
VOICE_CHECK_PASS = 9


def _say_wav(text: str, d, k: int) -> bytes:
    import subprocess
    from pathlib import Path
    aiff, wav = Path(d) / f"v{k}.aiff", Path(d) / f"v{k}.wav"
    subprocess.run(["say", "-o", str(aiff), text], check=True, timeout=60)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(aiff), str(wav)], check=True, timeout=60)
    return wav.read_bytes()


def check(post=None, speak=None) -> dict:
    """Each phrase spoken (say), heard through transcribe(), judged by its word groups; the result kept in manifests/voice_check_*.json."""
    import json
    import tempfile
    import time
    from pathlib import Path
    speak = speak or _say_wav
    rows = []
    with tempfile.TemporaryDirectory() as td:
        for k, (cid, said, groups) in enumerate(VOICE_CHECK):
            try:
                heard = transcribe(base64.b64encode(speak(said, td, k)).decode(), "audio/wav", post)
            except Exception as exc:  # noqa: BLE001
                heard = f"(error: {str(exc)[:100]})"
            rows.append({"id": cid, "said": said, "heard": heard, "ok": all(re.search(g, heard, re.I) for g in groups)})
    n = sum(r["ok"] for r in rows)
    out = {"t": int(time.time()), "day": time.strftime("%Y-%m-%d"), "understood": n, "of": len(rows), "pass": n >= VOICE_CHECK_PASS, "rows": rows,
           "note": "spoken by the Mac's voice (say), heard by India's speech path (India prompt and his holdings as names)"}
    d = Path(os.getenv("ANANTA_INDIA_DATA", os.path.expanduser("~/ananta_data/india"))) / "manifests"
    if d.exists():
        (d / "voice_check_latest.json").write_text(json.dumps(out, indent=1))
        with (d / "voice_check_history.jsonl").open("a") as f:
            f.write(json.dumps({k: v for k, v in out.items() if k != "rows"}) + "\n")
    return out


FILLER = re.compile(r"^(um+|uh+|hmm+|okay|ok|yeah|thanks?|thank you)[.!]?$", re.I)


def turn(who: str, audio_b64: str, mime: str, thread: str | None, mode: str | None, context: dict | None, ask_fn, post=None) -> dict:
    heard, spk = transcribe_full(audio_b64, mime, post)
    if not heard:
        return {"heard": "", "thread": thread, "error": "I didn't catch any words. Try again a little closer to the phone.", "speaker": spk}
    if FILLER.match(heard.strip()):
        return {"heard": heard, "thread": thread, "ignored": "filler", "speaker": spk}
    ctx = {**(context or {}), "voice_id": spk}          # 27 Oct: who the voice belongs to, for the Ask's handover logic (jarvis/india/voiceid.py)
    out = ask_fn(who, heard, thread=thread, mode=mode, context=ctx, voice=True)
    # 27 Oct: the speaker verdict is "speaker", never "voice_id": the app reads voice_id as the id of the answer's audio, and an object there sent
    # it to /v3/voice/answer/[object Object] (404) and so to the phone's female voice for every answer
    return {"heard": heard, "speaker": spk, **out}
