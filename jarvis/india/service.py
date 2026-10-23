"""India Ananta V1: its own service, its own look, reading only the India read model (blueprint 22 Oct, W5 -> V1).
  ~/ananta_venvs/jarvis/bin/python -m uvicorn jarvis.india.service:app --host 127.0.0.1 --port 8110   (launchd com.ananta.india.web)
What it serves
  GET  /                      the India screens (Today, Books, League, Research, Jobs, Telugu): one self-contained page
  GET  /api/readmodel         readmodel/latest.json as the records repo built it (plus served_at); nothing is computed here
  GET  /api/brief?lang=en|te  the brief sentences (Telugu through india.telugu, the father-mode layer)
  GET  /api/page/<name>       a registrations page as text: exit_policy_book, others_league, india_morning, research_tracker, telugu_glossary, india_readmodel
  POST /api/speak             {"sentences": [...], "lang": "en"|"te"} -> the voice server's mp3 (English: Kokoro, India's own voice; Telugu: the MMS server)
  GET  /health
Boundary: this process imports nothing from the crypto service and opens no crypto table; the read-model file and the registrations folder
are the only inputs. It reads no sealed data and touches no Kite path (it cannot: no key, no token). It writes only its own chat threads and the allocation setting; no trade, rule or ledger.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

import requests
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel

RECORDS = Path(os.getenv("ANANTA_RECORDS", os.path.expanduser("~/code/ananta-records")))
DATA = Path(os.getenv("ANANTA_INDIA_DATA", os.path.expanduser("~/ananta_data/india")))
READMODEL = DATA / "readmodel" / "latest.json"
REG = RECORDS / "india" / "registrations"
PAGES = {"exit_policy_book", "others_league", "india_morning", "research_tracker", "telugu_glossary", "india_readmodel", "missed_movers", "sp1_results"}
VOICE_URL = os.getenv("ANANTA_VOICE_URL", "http://127.0.0.1:8200")
TELUGU_URL = os.getenv("ANANTA_PARLER_URL", "http://127.0.0.1:8210")
INDIA_VOICE = os.getenv("ANANTA_INDIA_VOICE", "bm_lewis")      # India's own Kokoro voice; crypto speaks with another
MAX_SENTENCES = 12

if str(RECORDS) not in sys.path:                                 # india.telugu (the father-mode layer) lives in the records repo;
    sys.path.append(str(RECORDS))                                # appended, so the records repo's own top-level packages never shadow this repo's

JARVIS_URL = os.getenv("ANANTA_JARVIS_URL", "http://127.0.0.1:8100")   # the sign-in service: the same token the crypto app carries
_TOKENS: dict[str, tuple[float, str]] = {}                               # token sha -> (checked_at, who); 5-minute memory
TOKEN_TTL = 300

app = FastAPI(title="Ananta India", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in os.getenv("ANANTA_INDIA_ORIGINS", "https://livetrading247.com,https://www.livetrading247.com,"
                   "https://app.livetrading247.com,http://localhost:8081,http://127.0.0.1:8300,http://127.0.0.1:8301").split(",") if o.strip()],
                   allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type", "X-Ananta-Quiet"])
r = APIRouter()


def signed_in(request: Request, authorization: str = Header(default="")) -> str:
    """Who is asking. A call from this Mac itself (no Cloudflare header, loopback client) passes as the owner, so the local page works;
    anything that came through the tunnel must carry the app's sign-in token, which the Jarvis service checks (/v3/me, marked quiet so it
    does not count as use). India keeps no accounts of its own: one login, one place."""
    import hashlib
    import time

    through_tunnel = bool(request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for"))
    if not through_tunnel and request.client and request.client.host in ("127.0.0.1", "::1"):
        return "owner"
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="not signed in")
    key = hashlib.sha256(token.encode()).hexdigest()
    hit = _TOKENS.get(key)
    if hit and time.time() - hit[0] < TOKEN_TTL:
        return hit[1]
    try:
        resp = requests.get(f"{JARVIS_URL}/v3/me", headers={"Authorization": f"Bearer {token}", "X-Ananta-Quiet": "1"}, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"the sign-in service did not answer: {str(e)[:80]}") from e
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="not signed in")
    who = str(resp.json().get("who") or "someone")
    _TOKENS[key] = (time.time(), who)
    return who


def readmodel() -> dict:
    try:
        rm = json.loads(READMODEL.read_text())
    except (OSError, ValueError) as e:
        raise HTTPException(status_code=503, detail=f"no India read model yet ({e.__class__.__name__}); the 22:30 paper job builds it") from e
    rm["served_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    try:
        rm["age_hours"] = round((dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(rm["built_at"])).total_seconds() / 3600, 1)
    except (KeyError, ValueError):
        rm["age_hours"] = None
    return rm


@r.get("/health")
def health() -> dict:
    ok = READMODEL.exists()
    return {"ok": ok, "readmodel": str(READMODEL), "data_through": json.loads(READMODEL.read_text()).get("data_through") if ok else None, "voice": INDIA_VOICE}


@r.get("/api/readmodel")
def api_readmodel(who: str = Depends(signed_in)) -> dict:
    return readmodel()


@r.get("/api/brief")
def api_brief(lang: str = "en", who: str = Depends(signed_in)) -> dict:
    rm = readmodel()
    if lang == "te":
        from india import telugu

        return {"lang": "te", "sentences": telugu.brief_te(rm), "data_through": rm["data_through"]}
    return {"lang": "en", "sentences": rm.get("brief", []), "data_through": rm["data_through"]}


@r.get("/api/page/{name}", response_class=PlainTextResponse)
def api_page(name: str, who: str = Depends(signed_in)) -> str:
    if name not in PAGES:
        raise HTTPException(status_code=404, detail=f"no such page; pages: {sorted(PAGES)}")
    p = REG / f"{name}.md"
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"{name}.md not written yet")
    return p.read_text()


class Speak(BaseModel):
    sentences: list[str]
    lang: str = "en"
    speed: float = 1.0


@r.post("/api/speak")
def api_speak(b: Speak, who: str = Depends(signed_in)) -> dict:
    sents = [str(s)[:400] for s in b.sentences if str(s).strip()][:MAX_SENTENCES]
    if not sents:
        raise HTTPException(status_code=400, detail="nothing to say")
    url = f"{TELUGU_URL}/speak" if b.lang == "te" else f"{VOICE_URL}/speak"
    body = {"sentences": sents, "speed": max(0.8, min(1.3, b.speed))}
    if b.lang != "te":
        body["voice"] = INDIA_VOICE
    try:
        r = requests.post(url, json=body, timeout=300)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"the {'Telugu' if b.lang == 'te' else 'voice'} server did not answer: {str(e)[:120]}") from e


@r.get("/", response_class=HTMLResponse)
def index() -> str:
    return (Path(__file__).parent / "page.html").read_text()


# ---- the app's own /v3 contract, filled with Indian data (jarvis/india/views.py): the crypto screens render these unchanged ----
from jarvis.india import views as india_views  # noqa: E402


# ---- Ask Ananta, Indian market (jarvis/india/ask.py): the same routes the chat screen calls on the crypto service ----
from jarvis.india import ask as india_ask  # noqa: E402


class Question(BaseModel):
    text: str
    thread: str | None = None
    mode: str | None = None
    provider: str | None = None
    context: dict | None = None
    source: str | None = None


class Rate(BaseModel):
    id: str
    rating: int


class Second(BaseModel):
    id: str


def _ask_run(fn, *a, **k):
    try:
        return fn(*a, **k)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@r.post("/v3/ask")
def ask_q(b: Question, who: str = Depends(signed_in), authorization: str = Header(default="")) -> dict:
    tok = authorization.removeprefix("Bearer ").strip() or None            # his own token: the fix flow files on the shared board as him
    return _ask_run(india_ask.ask, who, b.text, b.thread, b.mode, b.context, token=tok)


@r.post("/v3/ask/second")
def ask_second(b: Second, who: str = Depends(signed_in)) -> dict:
    for p in india_ask.ASK_DIR.glob("*.jsonl"):
        for m in india_ask.thread_messages(p.stem):
            if m.get("id") == b.id and m.get("role") == "assistant":
                return {**{k: v for k, v in m.items() if k != "usage"}, "second_of": b.id}
    raise HTTPException(status_code=404, detail="no such answer")


@r.post("/v3/ask/rate")
def ask_rate(b: Rate, who: str = Depends(signed_in)) -> dict:
    return india_ask.rate(b.id, b.rating)


@r.post("/v3/ask/speaker")
def ask_speaker(who: str = Depends(signed_in)) -> dict:
    return {"ok": True}


@r.get("/v3/ask/threads")
def ask_threads(who: str = Depends(signed_in)) -> dict:
    return {"threads": india_ask.threads()}


@r.get("/v3/ask/last")
def ask_last(who: str = Depends(signed_in)) -> dict:
    return india_ask.last()


@r.get("/v3/ask/stats")
def ask_stats(who: str = Depends(signed_in)) -> dict:
    return india_ask.stats()


@r.get("/v3/ask/thread/{thread}/export")
def ask_export(thread: str, who: str = Depends(signed_in)) -> dict:
    return {"text": india_ask.export(thread)}


@r.post("/v3/ask/thread/{thread}/delete")
def ask_delete(thread: str, who: str = Depends(signed_in)) -> dict:
    return india_ask.delete_thread(thread)


@r.get("/v3/ask/thread/{thread}")
def ask_thread(thread: str, who: str = Depends(signed_in)) -> dict:
    return {"messages": india_ask.thread_view(thread)}


# ---- India voice (jarvis/india/voice.py): the app's voice loop, on the local voice server, India's own voice ----
from fastapi.responses import Response  # noqa: E402

from jarvis.india import voice as india_voice  # noqa: E402


class Audio(BaseModel):
    audio_b64: str
    mime: str = "audio/webm"


class VoiceTurn(BaseModel):
    audio_b64: str
    mime: str = "audio/webm"
    thread: str | None = None
    mode: str | None = None
    context: dict | None = None
    source: str | None = None
    prefix: str | None = None
    client_timing: dict | None = None


class AnswerVoice(BaseModel):
    sentences: list[str]
    voice: str = "Calm"
    speed: float = 1.0
    wait: bool = True


class SpeakReq(BaseModel):
    sentences: list[str]
    voice: str = "Calm"


class UiResult(BaseModel):
    answer_id: str
    results: list[dict] = []
    spots: list[str] = []


def _voice_run(fn, *a, **k):
    try:
        return fn(*a, **k)
    except KeyError as e:
        raise HTTPException(status_code=404, detail="unknown answer audio") from e
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"the voice server did not answer ({str(e)[:80]})") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@r.post("/v3/voice/transcribe")
def voice_transcribe(b: Audio, who: str = Depends(signed_in)) -> dict:
    return {"text": _voice_run(india_voice.transcribe, b.audio_b64, b.mime)}


@r.post("/v3/voice/turn")
def voice_turn(b: VoiceTurn, who: str = Depends(signed_in), authorization: str = Header(default="")) -> dict:
    tok = authorization.removeprefix("Bearer ").strip() or None
    return _voice_run(india_voice.turn, who, b.audio_b64, b.mime, b.thread, b.mode, b.context, lambda *a, **k: india_ask.ask(*a, token=tok, **k))


@r.post("/v3/voice/answer")
def voice_answer(b: AnswerVoice, who: str = Depends(signed_in)) -> dict:
    return _voice_run(india_voice.prepare_answer, b.sentences, b.speed)


@r.get("/v3/voice/answer/{key}")
def voice_answer_meta(key: str, who: str = Depends(signed_in)) -> dict:
    return _voice_run(india_voice.answer_meta, key)


@r.get("/v3/voice/answer/{key}/audio")
def voice_answer_audio(key: str, who: str = Depends(signed_in)):
    body, ctype = _voice_run(india_voice.answer_audio, key)
    return Response(content=body, media_type=ctype, headers={"Cache-Control": "private, max-age=600", "Content-Length": str(len(body))})


@r.post("/v3/voice/prepare")
def voice_prepare(b: SpeakReq, who: str = Depends(signed_in)) -> dict:
    return {"ids": _voice_run(india_voice.prepare, b.sentences), "voices": [INDIA_VOICE]}


@r.get("/v3/voice/clip/{cid}")
def voice_clip(cid: str, who: str = Depends(signed_in)):
    body, ctype = _voice_run(india_voice.clip, cid)
    return Response(content=body, media_type=ctype, headers={"Cache-Control": "private, max-age=600"})


@r.post("/v3/voice/ui_result")
def voice_ui_result(b: UiResult, who: str = Depends(signed_in)) -> dict:
    return {"ok": True}


class Allocation(BaseModel):
    mode: str = "advisory"          # "advisory": options fixed, stocks as in the account, Ananta rates and suggests; "autonomous": Ananta moves capital on paper
    options_inr: float | None = None
    note: str = ""


@r.post("/v3/allocation")
def allocation_set(b: Allocation, who: str = Depends(signed_in)) -> dict:
    """The allocation mode (Madhav, 23 Oct, 14:04): advisory (options Rs 50,000 fixed, stocks as in the account, Ananta rates, ranks and suggests) or
    autonomous (Ananta moves capital between stocks, options and cash on paper). Both are paper: no order is placed. The allocator job (records repo)
    reads this file and rebuilds the plan within minutes."""
    import datetime as _dt

    if who == "owner" or not who.startswith("guest:"):
        mode = {"autonomous": "autonomous", "ananta": "autonomous"}.get(b.mode, "advisory")
        if b.options_inr is not None and not (0 <= b.options_inr <= 1_000_000):
            raise HTTPException(status_code=400, detail="options amount out of range")
        rec = {"mode": mode, "options_inr": b.options_inr or 50000.0,
               "note": b.note or ("Ananta moves capital between stocks, options and cash on paper, inside the regime table" if mode == "autonomous" else "options fixed; Ananta rates, ranks and suggests"),
               "set_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "set_by": who, "paper": True}
        p = india_views.DATA / "paper" / "allocation.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(rec, indent=1))
        return rec
    raise HTTPException(status_code=403, detail="owner only")


@r.get("/v3/allocation/plan")
def allocation_plan(who: str = Depends(signed_in)) -> dict:
    """The full plan (every holding, rating, suggestion and paper move) is the owner's; anyone else gets the totals."""
    return india_views.allocation_plan(full=(who == "owner" or not who.startswith("guest:")))


@r.get("/v3/{name:path}")
def v3(name: str, who: str = Depends(signed_in), days: int = 30) -> dict:
    fn = india_views.ROUTES.get(name)
    if fn is None:
        raise HTTPException(status_code=404, detail=f"India has no view for /v3/{name} yet")
    try:
        return fn()
    except Exception as e:   # noqa: BLE001 - a view that cannot build says so; the screen shows the error box, never a half page
        raise HTTPException(status_code=503, detail=f"India view {name} could not build: {e.__class__.__name__}: {str(e)[:120]}") from e


@r.get("/history")
def history(days: int = 30, who: str = Depends(signed_in)) -> dict:
    return india_views.history(days)


app.include_router(r)                      # on this Mac: http://127.0.0.1:8110/...
app.include_router(r, prefix="/india")     # through the tunnel: https://api.livetrading247.com/india/... (same token as the crypto app)
