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
are the only inputs. It reads no sealed data and touches no Kite path (it cannot: no key, no token). Read-only by construction: no route writes.
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


app.include_router(r)                      # on this Mac: http://127.0.0.1:8110/...
app.include_router(r, prefix="/india")     # through the tunnel: https://api.livetrading247.com/india/... (same token as the crypto app)
