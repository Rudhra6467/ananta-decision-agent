"""Jarvis service over HTTP (owner only). Run from the Agent folder:

    .venv-jarvis/bin/python -m uvicorn jarvis.service.app:app --host 127.0.0.1 --port 8100

Every route except /health needs "Authorization: Bearer <token>" from POST /auth/login.
"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from jarvis.service import core

app = FastAPI(title="Jarvis", version=core.VERSION, docs_url=None, redoc_url=None, openapi_url=None)
_J: core.Jarvis | None = None


def J() -> core.Jarvis:
    global _J
    if _J is None:
        _J = core.from_env()
    return _J


def owner(authorization: str = Header(default="")) -> str:
    try:
        return J().check(authorization.removeprefix("Bearer ").strip())
    except core.AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


class Login(BaseModel):
    email: str
    password: str


class Ids(BaseModel):
    ids: list[str] | str = "all"


class Mode(BaseModel):
    mode: str
    confirm: bool = False


class Kill(BaseModel):
    on: bool
    confirm: bool = False


class Push(BaseModel):
    token: str
    device: str = "iPhone"


def _run(fn, *a) -> Any:
    try:
        return fn(*a)
    except core.ConfirmRequired as exc:
        raise HTTPException(status_code=428, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.on_event("startup")
def _snapshots() -> None:
    """Value history for the charts: one snapshot now and every 15 minutes."""
    import threading
    import time as _t

    def loop():
        while True:
            try:
                J().record_snapshot()
            except Exception:  # noqa: BLE001  history is best-effort
                pass
            try:
                background_jobs()
            except Exception:  # noqa: BLE001
                pass
            _t.sleep(900)

    threading.Thread(target=loop, daemon=True).start()


@app.get("/history")
def history(days: float = 30, who: str = Depends(owner)) -> dict:
    return J().history(days)


@app.get("/coin/{sym}")
def coin(sym: str, who: str = Depends(owner)) -> dict:
    return _run(J().coin, sym)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "version": core.VERSION}


@app.post("/auth/login")
def login(b: Login) -> dict:
    try:
        return {"token": J().login(b.email, b.password), "expires_in_s": core.TOKEN_TTL_S}
    except core.AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@app.get("/today")
def today(who: str = Depends(owner)) -> dict:
    return J().today()


@app.get("/portfolio")
def portfolio(who: str = Depends(owner)) -> dict:
    return J().portfolio()


@app.post("/portfolio/approve")
def approve(b: Ids, who: str = Depends(owner)) -> dict:
    return {"fills": _run(J().approve, who, b.ids)}


@app.post("/portfolio/reject")
def reject(b: Ids, who: str = Depends(owner)) -> dict:
    return {"rejected": _run(J().reject, who, b.ids)}


@app.post("/portfolio/mode")
def mode(b: Mode, who: str = Depends(owner)) -> dict:
    return {"mode": _run(J().set_mode, who, b.mode, b.confirm)}


@app.get("/evidence")
def evidence(who: str = Depends(owner)) -> dict:
    return J().evidence()


@app.get("/safety")
def safety(who: str = Depends(owner)) -> dict:
    return J().safety()


@app.post("/safety/kill")
def kill(b: Kill, who: str = Depends(owner)) -> dict:
    return _run(J().set_kill, who, b.on, b.confirm)


@app.post("/push/register")
def push_register(b: Push, who: str = Depends(owner)) -> dict:
    _run(J().register_push, who, b.token, b.device)
    return {"ok": True}


# ---- v0.3: plain-language views, evidence, cockpit, Ask Ananta ----
from jarvis.service import ask as _ask  # noqa: E402
from jarvis.service import views  # noqa: E402

_A: _ask.Ask | None = None


def A() -> _ask.Ask:
    global _A
    if _A is None:
        _A = _ask.Ask(J())
    return _A


class Question(BaseModel):
    text: str
    thread: str | None = None
    provider: str | None = None
    mode: str | None = None
    context: dict | None = None


class Second(BaseModel):
    id: str


class Setting(BaseModel):
    key: str
    value: str


class Rating(BaseModel):
    id: str
    rating: int


@app.get("/v3/home")
def home(who: str = Depends(owner)) -> dict:
    return {"summary": views.day_summary(J()), "feed": views.feed(J(), hours=72, limit=40)}


@app.get("/v3/holdings")
def holdings(who: str = Depends(owner)) -> dict:
    return views.holdings(J())


@app.get("/v3/trade/{trade_id}")
def trade(trade_id: str, who: str = Depends(owner)) -> dict:
    return _run(views.trade_detail, J(), trade_id)


@app.get("/v3/evidence/collected")
def ev_collected(who: str = Depends(owner)) -> dict:
    return views.evidence_collected(J())


@app.get("/v3/evidence/forwarded")
def ev_forwarded(who: str = Depends(owner)) -> dict:
    return views.evidence_forwarded(J())


@app.get("/v3/cockpit")
def cockpit(who: str = Depends(owner)) -> dict:
    return views.cockpit(J())


@app.post("/v3/ask")
def ask_q(b: Question, who: str = Depends(owner)) -> dict:
    return _run(lambda: A().ask(who, b.text, b.thread, b.provider, b.mode, None, b.context))


@app.post("/v3/ask/second")
def ask_second(b: Second, who: str = Depends(owner)) -> dict:
    return _run(A().second, who, b.id)


@app.get("/v3/spend")
def spend(who: str = Depends(owner)) -> dict:
    return A().spend()


@app.post("/v3/settings")
def set_setting(b: Setting, who: str = Depends(owner)) -> dict:
    return _run(A().set_setting, who, b.key, b.value)


@app.post("/v3/ask/rate")
def ask_rate(b: Rating, who: str = Depends(owner)) -> dict:
    A().rate(b.id, b.rating)
    return {"ok": True}


@app.get("/v3/ask/threads")
def ask_threads(who: str = Depends(owner)) -> dict:
    return {"threads": A().threads()}


@app.get("/v3/ask/thread/{thread}")
def ask_thread(thread: str, who: str = Depends(owner)) -> dict:
    return {"messages": A().thread(thread)}


@app.get("/v3/ask/stats")
def ask_stats(who: str = Depends(owner)) -> dict:
    return A().stats()


@app.get("/v3/coin/{sym}/watch")
def coin_watch(sym: str, who: str = Depends(owner)) -> dict:
    return _run(views.coin_watch, J(), sym)


@app.get("/v3/trades")
def trades_list(who: str = Depends(owner)) -> dict:
    return views.trades_list(J())


@app.get("/v3/markets")
def markets(who: str = Depends(owner)) -> dict:
    return views.markets(J())


@app.get("/v3/chart/{sym}")
def chart(sym: str, tf: str = "1h", who: str = Depends(owner)) -> dict:
    return _run(views.chart, J(), sym, tf)


# ---- mandate and pending actions ----
from jarvis.service.mandate import Mandate  # noqa: E402


def M() -> Mandate:
    return Mandate(J().db, J().now)


class MandateBody(BaseModel):
    sections: dict
    why: str = ""


class Decide(BaseModel):
    confirm: bool


def AL():
    from jarvis.service.alerts import Alerts

    return Alerts(J().db, J().now)


def MN():
    from jarvis.service.manual import Manual

    return Manual(J().db, J().now)


def executors() -> dict:
    return {"mandate": M().apply_mandate_change, "alert": AL().create,
            "paper_order": lambda who, p: MN().execute(who, p, J().prices())}


@app.get("/v3/mandate")
def mandate_get(who: str = Depends(owner)) -> dict:
    return {**M().get(), "history": M().history()}


@app.post("/v3/mandate")
def mandate_set(b: MandateBody, who: str = Depends(owner)) -> dict:
    out = _run(M().set, who, b.sections, b.why or "edited in the app")
    J().audit(who, "mandate.edit", b.why or "app", f"v{out['version']}")
    return out


@app.get("/v3/actions")
def actions(who: str = Depends(owner)) -> dict:
    return {"pending": M().pending()}


@app.post("/v3/actions/{aid}")
def action_decide(aid: str, b: Decide, who: str = Depends(owner)) -> dict:
    out = _run(M().decide, who, aid, b.confirm, executors())
    J().audit(who, f"action.{'confirm' if b.confirm else 'cancel'}", f"{aid} {out.get('kind')}", out.get("status"))
    return out



class VoiceTurn(BaseModel):
    audio_b64: str
    mime: str = "audio/wav"
    thread: str | None = None
    mode: str | None = None
    context: dict | None = None


@app.post("/v3/voice/turn")
def voice_turn(b: VoiceTurn, who: str = Depends(owner)) -> dict:
    return _run(lambda: A().voice_turn(who, b.audio_b64, b.mime, b.thread, b.mode, b.context))



def _push(title: str, body: str):
    from src.intelligence.paper_watch import push_phone

    return push_phone(title, body, level="EVENT")


def background_jobs() -> dict:
    """Every 15 minutes: check alerts (no AI cost); write the morning / evening brief once each (free model)."""
    ex = J()._explorer()
    out = {"fired": AL().check(ex, push=_push), "manual_stops": MN().check_stops(ex.prices() if ex else {}, push=_push)}
    a = A()
    if a.setting("ask_enabled") == "1" and a.setting("voice_enabled") == "1":
        kind = AL().due_brief()
        if kind:
            out["brief"] = AL().write_brief(kind, lambda q: a.ask("ananta (scheduled)", q, mode="everyday"), push=_push)
    return out


@app.get("/v3/alerts")
def alerts_list(who: str = Depends(owner)) -> dict:
    return {"alerts": AL().list()}


@app.post("/v3/alerts/{aid}/off")
def alert_off(aid: str, who: str = Depends(owner)) -> dict:
    AL().turn_off(who, aid)
    J().audit(who, "alert.off", aid, "OK")
    return {"ok": True}


@app.get("/v3/brief")
def brief(who: str = Depends(owner)) -> dict:
    return {"brief": AL().latest_brief()}


@app.post("/v3/brief/now")
def brief_now(who: str = Depends(owner)) -> dict:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    kind = "evening" if datetime.now(ZoneInfo("America/Toronto")).hour >= 17 else "morning"
    r = AL().write_brief(kind, lambda q: A().ask(who, q, mode="everyday"))
    if not r:
        raise HTTPException(status_code=503, detail="Could not write the brief right now; try again in a minute.")
    return {"brief": AL().latest_brief()}


@app.get("/v3/inbox")
def inbox(who: str = Depends(owner)) -> dict:
    ps = J()._layer().pending()
    return {"actions": M().pending(), "portfolio": ps, "alerts_active": len(AL().list(include_done=False)),
            "count": len(M().pending()) + (1 if ps else 0)}



class Note(BaseModel):
    kind: str = "note"
    ref: str = ""
    text: str


@app.get("/v3/manual")
def manual(who: str = Depends(owner)) -> dict:
    m = MN()
    return {**m.state(J().prices()), "fills": m.fills(), "journal": m.journal(), "jobs": m.jobs()}


@app.post("/v3/journal")
def journal_note(b: Note, who: str = Depends(owner)) -> dict:
    if not b.text.strip():
        raise HTTPException(status_code=400, detail="empty note")
    return MN().note(who, b.kind, b.ref, b.text)
