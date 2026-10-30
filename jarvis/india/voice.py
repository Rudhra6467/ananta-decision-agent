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
import json
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


# 30 Oct (Madhav: "it's about you pronouncing them ... while saying you have to say Jio Financial"): the screen keeps the ticker, the voice says
# the company name. Applied to every India sentence just before it is made into audio, so the shown text, the sentence count and the
# highlights are unchanged. Letters said one by one are spaced ("I E X"), never dotted, so a sentence does not split. ~/ananta_data/india/
# say_names.json (ticker -> spoken name) adds to or overrides this list without a code change.
SAY_NAMES = {"JIOFIN": "Jio Financial", "TATAPOWER": "Tata Power", "TATACHEM": "Tata Chemicals", "TATAMOTORS": "Tata Motors",
             "TMPV": "Tata Motors Passenger Vehicles", "TMCV": "Tata Motors Commercial Vehicles", "MARICO": "Marico", "NATIONALUM": "National Aluminium",
             "IDEA": "Vodafone Idea", "LICI": "L I C", "UNITDSPR": "United Spirits", "KARURVYSYA": "Karur Vysya Bank", "IRFC": "I R F C", "IEX": "I E X",
             "NETWORK18": "Network Eighteen", "ADANIPORTS": "Adani Ports", "GESHIP": "G E Shipping", "KOTAKBANK": "Kotak Bank", "IFCI": "I F C I",
             "HDFCBANK": "H D F C Bank", "ICICIBANK": "I C I C I Bank", "SBIN": "State Bank of India", "RELIANCE": "Reliance", "INFY": "Infosys",
             "TCS": "T C S", "ITC": "I T C", "LT": "L and T", "HINDUNILVR": "Hindustan Unilever", "BHARTIARTL": "Bharti Airtel", "AXISBANK": "Axis Bank",
             "BAJFINANCE": "Bajaj Finance", "MARUTI": "Maruti", "SUNPHARMA": "Sun Pharma", "ONGC": "O N G C", "NTPC": "N T P C", "COALINDIA": "Coal India",
             "POWERGRID": "Power Grid", "ULTRACEMCO": "Ultratech Cement", "ASIANPAINT": "Asian Paints", "WIPRO": "Wipro", "HCLTECH": "H C L Tech",
             "TECHM": "Tech Mahindra", "TITAN": "Titan", "NESTLEIND": "Nestle India", "BANKNIFTY": "Bank Nifty", "FINNIFTY": "Fin Nifty"}
_say_rx: tuple[re.Pattern, dict] | None = None


def say_names(text: str) -> str:
    """The spoken form of a sentence: tickers replaced by company names (SAY_NAMES plus say_names.json). Whole words only, case kept out
    of it (JIOFIN, Jiofin), and a possessive stays ("JIOFIN's" -> "Jio Financial's")."""
    global _say_rx
    if _say_rx is None:
        m = dict(SAY_NAMES)
        try:
            extra = json.loads((Path(os.getenv("ANANTA_INDIA_DATA", os.path.expanduser("~/ananta_data/india"))) / "say_names.json").read_text())
            m.update({str(k).upper(): str(v) for k, v in extra.items() if v})
        except Exception:  # noqa: BLE001 - no file, or a bad one: the built-in list
            pass
        _say_rx = (re.compile(r"\b(" + "|".join(sorted(map(re.escape, m), key=len, reverse=True)) + r")\b"), m)
    rx, m = _say_rx
    return rx.sub(lambda mo: m.get(mo.group(1).upper(), mo.group(1)), text or "")


def _speak(sents: list[str], speed: float = 1.0, post=None, tail: float = 0.0) -> dict:
    post = post or (lambda url, body: requests.post(url, json=body, timeout=300).json())
    body = {"sentences": [say_names(x) for x in sents], "voice": INDIA_VOICE, "speed": max(0.6, min(1.5, float(speed or 1.0)))}
    if tail:
        body["tail"] = tail
    j = post(f"{VOICE_URL}/speak", body)
    return {"audio": base64.b64decode(j["audio_b64"]), "mime": j.get("mime", "audio/mpeg"), "offsets": j.get("offsets", []), "duration": j.get("duration", 0.0),
            "engine": "kokoro", "voice": INDIA_VOICE, "ms": j.get("ms")}


# ---- 27 Oct (Madhav: "the time gap for replying in voice has become a new issue"): the answer spoken in pieces --------------------------
# Kokoro made the WHOLE answer before the phone could play a word (23-25 s for a 470-character answer while the Mac's GPU was busy, about 5 s
# when idle). Now the first sentence is made first (about 0.5 s idle, 2-3 s busy) and plays while the rest is made, piece by piece, in order,
# in the same voice (bm_lewis). A stream's id is "s<key>"; piece i is "s<key>.<i>" on the same /v3/voice/answer routes. Only a client that
# says it can play pieces (tts.stream) gets a stream; an older client still gets one file.
STREAM_FIRST_CHARS = 120          # the first piece: the first sentence, plus the next when the first is very short
STREAM_PIECE_CHARS = 200          # then about this much per piece (at most 3 sentences): short enough to keep ahead of playback on a busy GPU
STREAM_RAMP = (110, 160)          # 30 Oct: the second and third pieces are smaller still, so each is made while the one before it plays
STREAM_HOLD_S = 4.0               # 30 Oct: when piece 0 was made slower than it plays (busy GPU), hold it up to this long for piece 1, so the
                                  # voice starts a little later instead of going silent after its first sentence
STREAM_WAIT_S = 45.0              # how long a request for a piece waits for it to be made (27 Oct: 30 s ran out once while the GPU was saturated)
STREAM_TAIL_S = 0.32              # the pause after a piece, so pieces join like sentences
_streams: OrderedDict[str, dict] = OrderedDict()


CLAUSE = re.compile(r"[,;:]\s+|\s[—–-]\s+")
JOIN = re.compile(r"\s(?=(?:if|because|but|so|when|which|while|unless|though|although)\b)", re.I)
HEAD_SPLIT_OVER = 10_000          # 30 Oct (Madhav: "voice cuts after the first 4-5 words"): the opening-clause cut is off. A 4-word clause is
                                  # 2 s of audio, and the next piece took 3.5-8 s to make with the GPU busy, so the voice went silent mid-sentence
                                  # after every opening. The first piece is now a whole sentence; STREAM_RAMP keeps the pieces after it small.
HEAD_TAIL_S = 0.12                # the short breath after that opening clause (mid-sentence, not a full stop)


def _head_cut(s: str) -> int | None:
    """Where to cut a long first sentence, in order of preference: after a comma/semicolon/colon/dash 30-90 characters in; before a joining
    word (if, because, but, so, when, which, while, unless, though) 40-100 in; after a comma etc. up to 120 in. At least 15 characters stay."""
    def first(rx, lo, hi, at):
        return next((m for m in rx.finditer(s) if lo <= at(m) <= hi and len(s) - m.end() >= 15), None)
    m = first(CLAUSE, 30, 90, lambda m: m.end()) or first(JOIN, 40, 100, lambda m: m.start()) or first(CLAUSE, 30, 120, lambda m: m.end())
    return m.end() if m else None


def plan(sents: list[str]) -> list[list[tuple[int, str]]]:
    """Each audio piece as (sentence index, text) items, in order. The first piece is small: the first sentence (with the next when the first is
    very short), or only the opening clause of a long first sentence (its rest opens the next piece, still sentence 0), so the first audio is
    ready fast even when the Mac's GPU is busy. Then about STREAM_PIECE_CHARS per piece, at most 3 items."""
    if not sents:
        return []
    items = [(i, s) for i, s in enumerate(sents)]
    first: list[tuple[int, str]] = [items.pop(0)]
    s0 = sents[0]
    cut = _head_cut(s0) if len(s0) > HEAD_SPLIT_OVER else None
    if cut:
        first = [(0, s0[:cut].rstrip())]
        items.insert(0, (0, s0[cut:].lstrip()))
    elif items and len(s0) < 40 and len(s0) + len(items[0][1]) <= STREAM_FIRST_CHARS:
        first.append(items.pop(0))
    out, cur, n = [first], [], 0
    for it in items:
        cur.append(it)
        n += len(it[1])
        limit = STREAM_RAMP[len(out) - 1] if len(out) - 1 < len(STREAM_RAMP) else STREAM_PIECE_CHARS
        if n >= limit or len(cur) >= 3:
            out.append(cur)
            cur, n = [], 0
    if cur:
        out.append(cur)
    return out


def pieces(sents: list[str]) -> list[list[int]]:
    """Sentence indices per audio piece (a sentence split across two pieces appears in both)."""
    return [[i for i, _ in p] for p in plan(sents)]


def _stream_worker(key: str, post=None) -> None:
    with _lock:
        s = _streams.get(key)
    if not s:
        return
    last = len(s["plan"]) - 1
    for i, items in enumerate(s["plan"]):
        part = [t for _, t in items]
        split_head = i == 0 and len(s["plan"]) > 1 and s["plan"][1][0][0] == 0      # the opening clause of sentence 0: a short breath only
        for attempt in (1, 2):                      # one retry: a busy voice server sometimes drops a request
            try:
                s["segs"][i] = _speak(part, s["speed"], post, tail=0.0 if i == last else (HEAD_TAIL_S if split_head else STREAM_TAIL_S))
                s["errors"][i] = None
                break
            except Exception as exc:  # noqa: BLE001 - the phone falls back to its own voice for the rest; never a crash
                s["errors"][i] = f"{type(exc).__name__}: {str(exc)[:120]}"
        s["events"][i].set()


def start_stream(texts: list[str], speed: float = 1.0, post=None, background: bool = True) -> str:
    """Start making an answer's audio piece by piece (the first piece first) and return its id at once."""
    sents = sentences(texts)
    if not sents:
        raise ValueError("no text to speak")
    speed = max(0.6, min(1.5, float(speed or 1.0)))
    key = "s" + _key(sents, INDIA_VOICE, speed)
    with _lock:
        old = _streams.get(key)
        if old and not any(e for e in old["errors"] if e):
            _streams.move_to_end(key)
            return key
        p = plan(sents)
        groups = [[i for i, _ in items] for items in p]
        _streams[key] = {"sents": sents, "plan": p, "pieces": groups, "speed": speed, "segs": [None] * len(groups), "errors": [None] * len(groups),
                         "events": [threading.Event() for _ in groups]}
        while len(_streams) > 60:
            _streams.popitem(last=False)
    if background:
        threading.Thread(target=_stream_worker, args=(key, post), daemon=True).start()
    else:
        _stream_worker(key, post)
    return key


def _piece(key: str, i: int, wait: float = STREAM_WAIT_S) -> dict:
    with _lock:
        s = _streams[key]                           # KeyError -> 404
    if not 0 <= i < len(s["pieces"]):
        raise KeyError(f"{key}.{i}")
    if not s["events"][i].wait(wait):
        raise requests.Timeout(f"piece {i} not made within {int(wait)} s")
    a = s["segs"][i]
    if a is None:
        raise requests.ConnectionError(s["errors"][i] or "the voice server did not make this piece")
    return a


def _split_id(key: str) -> tuple[str, int] | None:
    if key.startswith("s") and "." in key:
        base, _, n = key.rpartition(".")
        if n.isdigit():
            return base, int(n)
    return None


def stream_meta(key: str) -> dict:
    """The stream's first piece (waited for) and the plan of all pieces: the phone plays piece 0 and fetches the next while it plays."""
    a = _piece(key, 0)
    with _lock:
        s = _streams[key]
    # 30 Oct: a busy GPU makes audio slower than it plays; then the phone would finish piece 0 before piece 1 exists. Hold piece 0 (bounded)
    # until piece 1 is made, so the answer starts a moment later but does not stop after its first sentence.
    try:
        ms0, dur0 = float(a.get("ms") or 0), float(a.get("duration") or 0)
        if len(s["pieces"]) > 1 and ms0 > 0 and dur0 > 0 and ms0 > 0.6 * dur0 * 1000:
            s["events"][1].wait(min(STREAM_HOLD_S, max(0.0, ms0 / 1000.0 * 1.6 - dur0 + 1.5)))
    except Exception:  # noqa: BLE001
        pass
    return {"id": key, "stream": True, "offsets": a["offsets"], "duration": a["duration"], "engine": a["engine"], "voice": a["voice"], "mime": a["mime"],
            "bytes": len(a["audio"]), "ms": a.get("ms"), "sentences": len(s["sents"]),
            "segments": [{"id": f"{key}.{i}", "first": idx[0], "count": len(idx)} for i, idx in enumerate(s["pieces"])]}


def attach_stream(out: dict, context: dict | None, post=None) -> dict:
    """For a spoken answer: start its audio now (the first piece is usually ready before the phone asks) and tell the phone its id.
    Only when the phone said it plays pieces in the natural voice (context.tts.stream); a clarify question, a tour or an error is left alone."""
    try:
        tts = (context or {}).get("tts") if isinstance(context, dict) else None
        ans = str(out.get("answer") or "").strip()
        if isinstance(tts, dict) and tts.get("stream") and ans and not out.get("error") and out.get("kind") != "clarify" and not out.get("tour"):
            out["voice_id"] = start_stream([ans], float(tts.get("speed") or 1.0), post)
            out["speak"] = ans
    except Exception:  # noqa: BLE001 - the phone makes the audio itself as before
        pass
    return out


def prepare_answer(texts: list[str], speed: float = 1.0, post=None, stream: bool = False) -> dict:
    """The whole answer as one file; made now (local, a few seconds) and kept by key. stream=True (a phone that plays pieces): the first piece
    now and the rest in order while it plays (see start_stream)."""
    if stream:
        return stream_meta(start_stream(texts, speed, post))
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
    sp = _split_id(key)
    if sp:                                              # one piece of a stream (waits until it is made)
        base, i = sp
        a = _piece(base, i)
        with _lock:
            idx = _streams[base]["pieces"][i]
        return {"id": key, "offsets": a["offsets"], "duration": a["duration"], "engine": a["engine"], "voice": a["voice"], "mime": a["mime"],
                "bytes": len(a["audio"]), "ms": a.get("ms"), "first": idx[0], "count": len(idx)}
    with _lock:
        is_stream = key in _streams
    if is_stream:
        return stream_meta(key)
    with _lock:
        a = _answers[key]
    return {"id": key, "offsets": a["offsets"], "duration": a["duration"], "engine": a["engine"], "voice": a["voice"], "mime": a["mime"], "bytes": len(a["audio"]), "ms": a.get("ms")}


def answer_audio(key: str) -> tuple[bytes, str]:
    sp = _split_id(key)
    if sp:
        a = _piece(*sp)
        return a["audio"], a["mime"]
    with _lock:
        is_stream = key in _streams
    if is_stream:                                       # a stream's own id plays its first piece
        a = _piece(key, 0)
        return a["audio"], a["mime"]
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
    out = attach_stream(out, context, post)          # 27 Oct: the first piece of the spoken answer starts now, before the phone asks for it
    # 27 Oct: the speaker verdict is "speaker", never "voice_id": the app reads voice_id as the id of the answer's audio, and an object there sent
    # it to /v3/voice/answer/[object Object] (404) and so to the phone's female voice for every answer
    return {"heard": heard, "speaker": spk, **out}
