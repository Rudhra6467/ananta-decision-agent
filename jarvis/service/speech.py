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


# ---------------------------------------------------------------------------
# Written -> spoken (Madhav 2026-10-03: "it still feels like a robot"). The answer is written for the screen; before the voice
# reads it, codes become names, tickers become coin names, long decimals are rounded and symbols are said as words. One
# sentence in, one sentence out (so the highlight timing still lines up), never empty.
# ---------------------------------------------------------------------------
_CODES = {"T3": "trend portfolio", "SD6": "Hunter's book", "H07": "short dip trade", "E1": "pullback setup", "E2": "breakout setup",
          "E3": "bounce setup", "E4": "momentum setup", "E5": "squeeze setup", "E6": "deep dip setup", "E7": "downtrend dip setup",
          "E8": "dip setup", "V02": "Bitcoin 50-day rule", "V01": "trend rule", "M1a": "capitulation setup", "M2a-G": "retest setup",
          "M2a": "retest setup", "M3a": "quiet base setup", "M3b": "quiet base setup"}
_CODE_RE = re.compile(r"(\b(?:the|our|a|an|your|my|its|this|that|his)\s+)?\b(" + "|".join(sorted(map(re.escape, _CODES), key=len, reverse=True))
                      + r")\b(\s+(?:setup|setups|book|portfolio|trade|trades|rule))?", re.I)


def _code(m: re.Match) -> str:
    art, code, noun = m.group(1), m.group(2), m.group(3) or ""
    key = next((k for k in _CODES if k.lower() == code.lower()), code)
    name = _CODES.get(key, code)
    if noun and name.split()[-1].rstrip("s") == noun.strip().rstrip("s"):
        name = name.rsplit(" ", 1)[0] + " " + noun.strip()      # "E4 setups" -> "momentum setups"
        noun = ""
    if key.startswith("M") and not art:
        art = "your "
    if "'s " in name and (art or "").strip().lower() in ("", "the"):
        art = ""                                                # "the SD6" -> "Hunter's book", not "the Hunter's book"
    return (art if art is not None else "the ") + name + noun


_SAY = [
    (r"\bBTC\b", "Bitcoin"), (r"\bETH\b", "Ethereum"), (r"\bSOL\b", "Solana"), (r"\bADA\b", "Cardano"), (r"\bDOGE\b", "Dogecoin"),
    (r"\bAVAX\b", "Avalanche"), (r"\bBCH\b", "Bitcoin Cash"), (r"\bLINK\b", "Chainlink"), (r"\bLTC\b", "Litecoin"), (r"\bXRP\b", "X R P"),
    (r"\bRSI\b", "R S I"), (r"\bATR\b", "A T R"), (r"\bEMA\b", "E M A"), (r"\bSMA\b", "average"), (r"\bP&L\b|\bPnL\b|\bP/L\b", "profit and loss"),
    (r"\bUSD\b", "dollars"), (r"\bvs\.?(?=\s)", "versus"), (r"\be\.g\.", "for example"), (r"\bi\.e\.", "that is"), (r"\bapprox\.?", "about"),
    (r"\betc\.", "and so on"), (r"&", " and "), (r"\bw/", "with "), (r"~\s*", "about "), (r"≈\s*", "about "), (r"→|->", " to "),
    (r"\b(\d+(?:\.\d+)?)R\b", r"\1 times the risk"), (r"\b2 times the risk\b", "twice the risk"), (r"\b1 times the risk\b", "one times the risk"),
    (r"\bUTC\b", "U T C"), (r"\b24/7\b", "around the clock"),
]
_EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF️‍]+")


def _round_num(m: re.Match) -> str:
    s = m.group(0)
    raw = s.replace("$", "").replace(",", "")
    try:
        v = float(raw)
    except ValueError:
        return s
    dollar = s.startswith("$")
    if abs(v) >= 1000:
        out = f"{round(v):,}"
    elif abs(v) >= 100:
        out = f"{round(v)}"
    elif abs(v) >= 1:
        out = f"{v:.2f}".rstrip("0").rstrip(".")
    elif v == 0:
        out = "0"
    else:
        out = f"{v:.4g}"
    return ("$" if dollar else "") + out


def for_ear(text: str) -> str:
    t0 = text or ""
    t = re.sub(r"\*\*|__|`|^#+\s*|^[-*•]\s+", "", t0, flags=re.M)
    t = _EMOJI.sub("", t)
    t = t.replace("−", "-").replace("$-", "minus $")
    t = re.sub(r"(\w)\((\d+)\)", r"\1 \2", t)                         # "RSI(10)" -> "RSI 10"
    t = re.sub(r"\(([^()]{0,40})\)", r", \1,", t)                       # "(about a cent)" -> ", about a cent,"
    t = _CODE_RE.sub(_code, t)
    t = re.sub(r"[+](?=\d+(?:\.\d+)?R\b)", "", t)                       # "+2R" -> "2R" -> "twice the risk"
    t = re.sub(r"[~≈]\s*(?=[$\d])", "about ", t)
    t = re.sub(r"[~≈]", "", t)
    for pat, rep in _SAY:
        t = re.sub(pat, rep, t)
    t = re.sub(r"\b(up|down|rose|fell|gained|lost)\s+[+-](?=\$?\d)", r"\1 ", t)   # "up +2.5%" -> "up 2.5%"
    t = re.sub(r"(?<![\w.])\+(\d[\d,]*(?:\.\d+)?)\s*%", r"up \1 percent", t)
    t = re.sub(r"(?<![\w.])-(\d[\d,]*(?:\.\d+)?)\s*%", r"down \1 percent", t)
    t = re.sub(r"\$?\d[\d,]*\.\d{3,}|\$\d[\d,]*\.\d{1,2}(?=\D|$)", _round_num, t)   # long decimals, and cents on prices
    t = re.sub(r"(\d)\s*%", r"\1 percent", t)
    t = re.sub(r"\b(\d{1,2})/(\d{1,2})\b(?![/\d])", lambda m: f"{m.group(1)} of {m.group(2)}" if int(m.group(1)) <= int(m.group(2)) <= 20 else m.group(0), t)
    t = re.sub(r"(?<![\w.])\+(\$?\d)", r"plus \1", t)
    t = re.sub(r"\s+,", ",", t)
    t = re.sub(r",\s*,", ",", t)
    t = re.sub(r",\s*([.!?;:])", r"\1", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" ,")
    return t or t0.strip()


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
    """The sentences as they will be SPOKEN (for_ear), one per written sentence, so sentence i's highlight still matches."""
    return [for_ear(t.strip()[:600]) for t in (texts or []) if t and t.strip()][:40]


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


def prepare_answer(texts: list[str], voice: str = DEFAULT_VOICE, speed: float = 1.0, make=None) -> str:
    """Start making the whole answer's audio (if not already made or being made); returns its id at once."""
    sents = norm_sentences(texts)
    speed = round(max(0.6, min(1.5, float(speed or 1.0))), 2)
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
