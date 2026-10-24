"""Jarvis service over HTTP (owner only). Run from the Agent folder:

    .venv-jarvis/bin/python -m uvicorn jarvis.service.app:app --host 127.0.0.1 --port 8100

Every route except /health needs "Authorization: Bearer <token>" from POST /auth/login.
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel

from jarvis.service import core

app = FastAPI(title="Jarvis", version=core.VERSION, docs_url=None, redoc_url=None, openapi_url=None)

# The web app (livetrading247.com, Madhav 2026-10-06: "where i can access it through web") calls this API from the browser;
# only our own sites may. Phones are not browsers and are unaffected. Every route still needs the login token.
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402


@app.exception_handler(RequestValidationError)
async def _plain_422(request: Request, exc: RequestValidationError):
    """A refused request says in one sentence what was missing (Oct 13: the phone showed the raw error list as "[object Object]")."""
    bits = []
    for e in exc.errors()[:3]:
        loc = ".".join(str(x) for x in e.get("loc", []) if x not in ("body", "query"))
        bits.append(f"{loc or 'the request'}: {e.get('msg', 'invalid')}")
    return JSONResponse(status_code=422, content={"detail": "The app sent a request Ananta could not read (" + "; ".join(bits) +
                                                            "). Please update the app or tell Madhav."})

app.add_middleware(CORSMiddleware, allow_origins=["https://livetrading247.com", "https://www.livetrading247.com",
                                                  "http://localhost:8081", "http://127.0.0.1:8300", "http://localhost:8300"],   # local test copies
                   allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"], allow_headers=["Authorization", "Content-Type", "X-Ananta-Quiet"])
_J: core.Jarvis | None = None

# Guest practice sandbox: a guest sees the real system (markets, Explorer, portfolio, evidence) and can do everything Madhav can
# in the app, but every change (paper orders, alerts, mandate edits, questions, settings) goes to the guest's own database.
import contextvars  # noqa: E402
import re as _re  # noqa: E402
import threading as _threading  # noqa: E402

_SANDBOX: contextvars.ContextVar[str | None] = contextvars.ContextVar("jarvis_sandbox", default=None)
_JG: dict[str, core.Jarvis] = {}
_JG_LOCK = _threading.Lock()
SHARED_TABLES = ("snapshots", "briefings", "read_fires", "zone_visits", "news_log", "credit_records", "shadow_h07", "evidence_trades", "eye_events",
                 "brain_decisions", "missed_moves", "trade_reviews", "daily_reviews")   # read-only system history the guest should see too (copied, never written back)


def _main() -> core.Jarvis:
    global _J
    if _J is None:
        _J = core.from_env()
    return _J


def _sync_shared(g: core.Jarvis) -> None:
    from jarvis.service.alerts import Alerts
    from jarvis.service.mandate import Mandate

    m = _main()
    from jarvis.service import reads_watch

    Alerts(g.db, g.now)
    reads_watch._table(g)
    from jarvis.service import zones_watch

    zones_watch._table(g)
    from jarvis.service import news_watch

    news_watch._table(g)
    from jarvis.service import credit

    credit._table(g)
    from jarvis.service import shadow_h07

    shadow_h07._table(g)
    from jarvis.service import eye as _eye
    from jarvis.service import watch_engine

    watch_engine._table(g)
    _eye._table(g)
    from jarvis.service import brain as _brain
    from jarvis.service import missed as _missed
    from jarvis.service import reviews as _reviews

    _brain._table(g)
    _missed._table(g)
    _reviews._table(g)
    md = Mandate(g.db, g.now)
    for tbl in SHARED_TABLES:
        try:
            rows = m.db.execute(f"SELECT * FROM {tbl}").fetchall()
        except Exception:  # noqa: BLE001  the owner has none yet
            continue
        if rows:
            names = [c[1] for c in m.db.execute(f"PRAGMA table_info({tbl})").fetchall()]
            have = {c[1] for c in g.db.execute(f"PRAGMA table_info({tbl})").fetchall()}
            if not have:                                    # the guest never had this table: make it from the owner's own definition
                sql = m.db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tbl,)).fetchone()
                g.db.execute(sql[0])
            else:                                           # the owner's table grew a column after the guest's copy was made (Oct 14)
                for c in names:
                    if c not in have:
                        g.db.execute(f"ALTER TABLE {tbl} ADD COLUMN {c}")
            ph = ",".join("?" * len(names))
            g.db.executemany(f"INSERT OR REPLACE INTO {tbl} ({','.join(names)}) VALUES ({ph})",
                             [tuple(r) for r in rows])      # by column name; updates too (a trade that closed)
    try:
        if not g.db.execute("SELECT 1 FROM mandate LIMIT 1").fetchone():      # start from Madhav's mandate; edits stay in the sandbox
            for t, by, why, js in m.db.execute("SELECT t, by, why, json FROM mandate ORDER BY version DESC LIMIT 1").fetchall():
                g.db.execute("INSERT INTO mandate (t, by, why, json) VALUES (?,?,?,?)", (t, by, "copied for the guest sandbox", js))
    except Exception:  # noqa: BLE001
        pass
    g.db.commit()
    del md


def _sandbox(who: str) -> core.Jarvis:
    name = _re.sub(r"[^a-z0-9]+", "_", who.split(":", 1)[1].lower()).strip("_")[:40] or "guest"
    with _JG_LOCK:
        if name not in _JG:
            m = _main()
            g = core.Jarvis(m.dir, owner_email=m.owner, password_hash=m.pw_hash, secret=m.secret, hands=m._hands, now=m.now,
                            db_file=f"jarvis_guest_{name}.sqlite")
            g.users_db = m.db                                   # accounts live in the owner's database
            _sync_shared(g)
            _JG[name] = g
        return _JG[name]


def _sandbox_name(email: str) -> str:
    return _re.sub(r"[^a-z0-9]+", "_", email.lower()).strip("_")[:40] or "guest"


def _archive_sandbox(email: str) -> str | None:
    """A removed visitor's (or a reset) practice book is moved to guest_archive/, never deleted; the next sign-in starts empty."""
    import shutil
    from pathlib import Path

    name = _sandbox_name(email)
    with _JG_LOCK:
        g = _JG.pop(name, None)
        if g is not None:
            try:
                g.db.con.close()
            except Exception:  # noqa: BLE001
                pass
        src = Path(_main().dir) / f"jarvis_guest_{name}.sqlite"
        if not src.exists():
            return None
        dst = Path(_main().dir) / "guest_archive" / f"jarvis_guest_{name}.{int(_main().now())}.sqlite"
        dst.parent.mkdir(exist_ok=True)
        shutil.move(str(src), str(dst))
        return dst.name


def J() -> core.Jarvis:
    w = _SANDBOX.get()
    return _sandbox(w) if w else _main()


def owner(authorization: str = Header(default=""), x_ananta_quiet: str = Header(default="")) -> str:
    """The signed-in account. A request the person made keeps the sign-in alive; the app marks its quiet background refreshes
    (X-Ananta-Quiet: 1) so an open but unused screen still signs out after 3 hours (Madhav, Oct 12)."""
    try:
        return J().check(authorization.removeprefix("Bearer ").strip(), touch=x_ananta_quiet != "1")
    except core.AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


# Controls that change shared state (Madhav's real paper portfolio, the kill switch) stay locked for guests.
GUEST_LOCKED = ("/portfolio/approve", "/portfolio/reject", "/portfolio/mode", "/safety/kill")


@app.middleware("http")
async def plain_words(request, call_next):
    """Plan 2.3: no internal code (E4, H07, T3, P02...) reaches a screen. Every /v3 answer's sentences and labels are rewritten
    with display names; pure identifiers stay for the app, which names them with /v3/names."""
    import json as _json
    from fastapi.responses import Response
    from jarvis.service import plain

    resp = await call_next(request)
    if not request.url.path.startswith("/v3/") or "application/json" not in resp.headers.get("content-type", ""):
        return resp
    body = b"".join([c async for c in resp.body_iterator])
    try:
        out = _json.dumps(plain.scrub(_json.loads(body)), ensure_ascii=False).encode()
    except ValueError:
        out = body
    headers = {k: v for k, v in resp.headers.items() if k.lower() != "content-length"}
    return Response(out, status_code=resp.status_code, headers=headers, media_type="application/json")


@app.get("/v3/coins")
def coins_all(who: str = Depends(owner)) -> dict:
    """Home's "Load more" (plan 3.1): every live coin with its price and move. The market is shared by every account."""
    from jarvis.service import views
    return {"coins": views.markets(J()).get("coins") or []}


@app.get("/v3/names")
def display_names(who: str = Depends(owner)) -> dict:
    """The one dictionary of display names (glossary.json names + the watch catalogue)."""
    from jarvis.service import plain
    return {"names": plain.names()}


@app.middleware("http")
async def guest_sandbox(request, call_next):
    from fastapi.responses import JSONResponse

    auth = request.headers.get("authorization", "")
    who = ""
    if auth:
        try:
            who = _main().check(auth.removeprefix("Bearer ").strip())
        except core.AuthError:
            who = ""
    if who.startswith("guest:"):
        if request.method != "GET" and request.url.path in GUEST_LOCKED:
            return JSONResponse({"detail": "Practice mode: the kill switch, autopilot and portfolio approvals belong to Madhav's real "
                                           "paper books, so they are locked here. Everything else you do goes to your own practice book."},
                                status_code=403)
        tok = _SANDBOX.set(who)
        try:
            return await call_next(request)
        finally:
            _SANDBOX.reset(tok)
    return await call_next(request)


def is_guest(who: str) -> bool:
    return who.startswith("guest:")


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


STATE_W: dict = {}


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
            try:                                          # Oct 21: every step's *_error is kept with its UTC time, never thrown away
                jobs_out = background_jobs()
            except Exception as exc:  # noqa: BLE001
                jobs_out = {"background_jobs_error": f"{type(exc).__name__}: {str(exc)[:200]}"}
            try:
                from jarvis.service import reliability

                reliability.record_job_errors(jobs_out)
            except Exception:  # noqa: BLE001  recording never stops the loop
                pass
            try:                                          # build plan 1.4b: every account's watches and positions, one shared snapshot
                from jarvis.service import watches as _W

                from jarvis.service import notify as _N

                ems = [em for (em,) in _main().db.execute("SELECT email FROM users").fetchall()]
                accts = [_main()] + [_sandbox("guest:" + em) for em in ems]
                mail = {id(_sandbox("guest:" + em)): em for em in ems}

                def _reach(a):                            # plan 1.7: Madhav's phone + his web devices; a visitor's web devices and email
                    if a is _main():
                        return lambda t, b: (_push(t, b), _N.notify(a, t, b))
                    return lambda t, b: _N.notify(a, t, b, email=mail.get(id(a), ""))

                STATE_W["last"] = _W.check_all(_main(), accts, push_for=_reach)
            except Exception as exc:  # noqa: BLE001
                STATE_W["error"] = str(exc)[:200]
            for name, g in list(_JG.items()):             # guest sandboxes: their own alerts and stops, no phone pushes
                tok = _SANDBOX.set("guest:" + name)
                try:
                    _sync_shared(g)
                    ex = _main()._explorer()
                    AL().check(ex, push=None)
                    MN().check_stops(ex.prices() if ex else {}, push=None)
                except Exception:  # noqa: BLE001
                    pass
                finally:
                    _SANDBOX.reset(tok)
            _t.sleep(900)

    threading.Thread(target=loop, daemon=True).start()


@app.on_event("startup")
def _start_eye() -> None:
    """The eye: live prices every 10 seconds against your stops, alerts, zones and a sudden Bitcoin drop (owner books only)."""
    import os

    if os.getenv("ANANTA_EYE", "1") != "1" or "PYTEST_CURRENT_TEST" in os.environ:
        return
    from jarvis.service import eye

    eye.start(_main, push=lambda t, b: _push(t, b))


@app.on_event("startup")
def _start_watchdog_and_brain() -> None:
    """The health watchdog (every part every 2 minutes, phone note when one goes quiet) and Jarvis's brain (decisions on the
    moments the eye and the watches flag, its own paper book)."""
    import os

    if "PYTEST_CURRENT_TEST" in os.environ:
        return
    from jarvis.service import brain, health

    if os.getenv("ANANTA_HEALTH", "1") == "1":
        health.start(_main, push=_push_warn)
    if os.getenv("BRAIN_ENABLED", "1") == "1":
        brain.start(_main, push=lambda t, b: _push(t, b))


@app.on_event("startup")
def _start_universe() -> None:
    """Engine plan U2-U4: one feed for every coin (Binance public data), every rule on every coin, zone touches on live prices.
    The 10-coin books are untouched (D7)."""
    import os
    import threading

    if os.getenv("ANANTA_UNIVERSE", "1") != "1" or "PYTEST_CURRENT_TEST" in os.environ:
        return
    from jarvis.service import feed, universe_explorer, universe_watch

    def first_arm():
        try:
            if not (universe_watch.Path(_main().dir) / "universe_zones.json").exists():
                universe_watch.arm(_main())
        except Exception:  # noqa: BLE001
            pass

    feed.start(_main, on_prices=universe_watch.tick, on_daily=universe_watch.run_daily, on_5m=universe_explorer.step_async)
    threading.Timer(90, first_arm).start()


@app.get("/v3/universe")
def universe_live(who: str = Depends(owner)) -> dict:
    from jarvis.service import universe_watch

    return universe_watch.status(_main())


@app.get("/v3/universe/scoreboard")
def universe_scoreboard(who: str = Depends(owner)) -> dict:
    from jarvis.service import universe_watch

    return universe_watch.scoreboard(_main())


@app.get("/v3/exposure")
def exposure_live(who: str = Depends(owner)) -> dict:
    """Engine fixes 1-4: the dial, the benchmark books, the measured-edge table, the would-be account in R against the hurdle."""
    from jarvis.service import ev, exposure, universe_watch

    j = _main()
    return {"dial": exposure.state(j), "books": exposure.books(j), "measured_edges": ev.table(), "account": universe_watch.would_be(j),
            "fidelity": ev.fidelity(j)}


@app.get("/v3/universe/ladder")
def universe_ladder(who: str = Depends(owner)) -> dict:
    from jarvis.service import universe_watch

    return universe_watch.ladder(_main())


@app.post("/v3/universe/ladder")
def universe_ladder_set(body: dict, who: str = Depends(owner)) -> dict:
    """Madhav's sign-off on the promotion ladder (one step up when the evidence allows it, or down)."""
    if is_guest(who):
        raise HTTPException(status_code=403, detail="Only Madhav signs off a promotion.")
    from jarvis.service import universe_watch

    try:
        return universe_watch.set_step(_main(), str(body.get("watch") or ""), str(body.get("step") or ""), who)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v3/needs")
def needs_list(who: str = Depends(owner)) -> dict:
    """Home's "Needs you" (Oct 14): the decisions waiting for Madhav, today a rule that passed its forward test and may step up."""
    if is_guest(who):
        return {"items": []}
    from jarvis.service import needs

    return {"items": needs.list_(_main())}


class NeedsIn(BaseModel):
    id: str
    decision: str = "later"


@app.post("/v3/needs/decide")
def needs_decide(b: NeedsIn, who: str = Depends(owner)) -> dict:
    """Madhav's tap on the card: approve = one step up the ladder (paper); later = hide it for a week."""
    if is_guest(who):
        raise HTTPException(status_code=403, detail="Only Madhav decides.")
    from jarvis.service import needs

    try:
        return needs.decide(_main(), b.id, b.decision, who)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v3/universe/coins")
def universe_coins(tier: str | None = None, q: str | None = None, sort: str = "trading", n: int = 60, who: str = Depends(owner)) -> dict:
    from jarvis.service import universe_watch

    return universe_watch.coins(_main(), tier=tier, q=q, sort=sort, n=n)


@app.get("/history")
def history(days: float = 30, who: str = Depends(owner)) -> dict:
    return J().history(days)


@app.get("/coin/{sym}")
def coin(sym: str, who: str = Depends(owner)) -> dict:
    return _run(J().coin, sym)


# Kite Connect sign-in (India plan, 16 Oct 2026, section 5): the owner opens /kite/login on the Mac, Zerodha's own page takes
# the password and two-factor code, and /kite/callback stores the day's token in ~/ananta_private. Both routes answer only a
# browser on this Mac (loopback, not through the Cloudflare tunnel), and the first login pins the Zerodha user id.
def _local_only(request: Request) -> None:
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost") or request.headers.get("cf-connecting-ip") or request.headers.get("x-forwarded-for"):
        raise HTTPException(status_code=403, detail="The Kite sign-in works only in a browser on the Mac itself.")


def _kite_page(title: str, body: str) -> "HTMLResponse":
    from fastapi.responses import HTMLResponse

    return HTMLResponse(f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title>"
                        "<style>body{font-family:-apple-system,Helvetica,Arial;max-width:34em;margin:4em auto;color:#1a1a1a}"
                        "h1{font-size:1.3em}p{line-height:1.5}</style></head>"
                        f"<body><h1>{title}</h1><p>{body}</p></body></html>")


@app.get("/kite/login")
def kite_login(request: Request):
    from fastapi.responses import RedirectResponse

    from src.india import kite_auth

    _local_only(request)
    try:
        return RedirectResponse(kite_auth.login_url())
    except RuntimeError as exc:
        return _kite_page("Kite sign-in not set up", str(exc))


@app.get("/kite/callback")
def kite_callback(request: Request, request_token: str = "", status: str = "", action: str = ""):
    from src.india import kite_auth

    _local_only(request)
    if status != "success" or not request_token:
        return _kite_page("Kite sign-in did not complete", "Zerodha did not return a login token. Close this tab and try /kite/login again.")
    try:
        st = kite_auth.exchange(request_token)
    except Exception as exc:  # noqa: BLE001
        return _kite_page("Kite sign-in failed", str(exc))
    return _kite_page("Ananta is connected to Kite",
                      f"Signed in as {st.get('user_name') or st.get('user_id')} ({st.get('user_id')}). The connection lasts until "
                      f"{st.get('expires_at_ist')}; after that the phone will ask for a fresh sign-in. You can close this tab.")


@app.get("/v3/kite/status")
def kite_status(who: str = Depends(owner)) -> dict:
    from src.india import kite_auth

    return kite_auth.status()


@app.get("/health")
def health() -> dict:
    import time as _t

    from jarvis.service import health as _h

    last = _h.STATE.get("last_run")
    return {"ok": True, "version": core.VERSION, "health_checks_s_ago": round(_t.time() - last) if last else None}


class Join(BaseModel):
    code: str
    name: str = ""
    email: str = ""
    password: str


class Invite(BaseModel):
    name: str = ""
    email: str = ""


class Person(BaseModel):
    email: str


@app.get("/auth/invite/{code}")
def invite_info(code: str) -> dict:
    """What the join page shows before the visitor signs up (no sign-in needed: the code is the key)."""
    try:
        return _main().invite_info(code)
    except core.AuthError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/auth/join")
def join(b: Join) -> dict:
    """A visitor accepts Madhav's invite link: their own name and password, and a fresh $1,000 practice book."""
    m = _main()
    try:
        info = m.invite_info(b.code)
        _archive_sandbox(info.get("email") or b.email)           # never inherit an old practice book under the same email
        return {"token": m.join(b.code, b.name, b.email, b.password), "expires_in_s": 7 * 86400}
    except core.AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/auth/login")
def login(b: Login) -> dict:
    try:
        return {"token": J().login(b.email, b.password), "expires_in_s": core.TOKEN_TTL_S, "idle_s": core.IDLE_S}
    except core.AccountExpired as exc:
        # Oct 12: a visitor's practice days are over. No app token: the feedback form (once), then a thank-you.
        return {"expired": True, "name": exc.name, "answered": exc.answered, "form_token": exc.form_token,
                "questions": [] if exc.answered else core.FEEDBACK_QUESTIONS,
                "message": (f"Thank you, {exc.name}. Your practice days with Ananta are over and Madhav has your answers." if exc.answered else
                            f"Hi {exc.name}, your {core.GUEST_DAYS:g} practice days with Ananta are over. Before you go, please answer a few "
                            "short questions: Madhav reads every answer.")}
    except core.AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


class Feedback(BaseModel):
    form_token: str
    answers: dict[str, str]


@app.post("/auth/feedback")
def feedback_submit(b: Feedback) -> dict:
    """A visitor whose practice days are over answers the feedback form (the form token from /auth/login is the key)."""
    try:
        return _main().submit_feedback(b.form_token, b.answers)
    except core.AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/auth/logout")
def logout_route(authorization: str = Header(default="")) -> dict:
    """Ends this sign-in on the server too (the app forgets its token either way)."""
    return {"ok": _main().logout(authorization.removeprefix("Bearer ").strip())}


class Password(BaseModel):
    current: str
    new: str


@app.post("/v3/account/password")
def change_password(b: Password, who: str = Depends(owner), authorization: str = Header(default="")) -> dict:
    """Madhav changes his own password (Cockpit › Additional features). Every other signed-in device is signed out."""
    _owner_only(who)
    try:
        return _main().change_password(b.current, b.new, keep_token=authorization.removeprefix("Bearer ").strip())
    except core.AuthError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v3/feedback")
def feedback_list(who: str = Depends(owner)) -> dict:
    """Madhav reads what visitors answered when their practice days ended."""
    _owner_only(who)
    return _main().feedback()


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

_A: dict[int, _ask.Ask] = {}
GUEST_CLAUDE_BUDGET = 0.5      # dollars a day of Madhav's Claude credit a guest can use; then Gemini answers


def A() -> _ask.Ask:
    j = J()
    if id(j) not in _A:
        _A[id(j)] = _ask.Ask(j)
    a = _A[id(j)]
    if j.sandbox and float(a.setting("daily_budget_usd") or 0) > GUEST_CLAUDE_BUDGET:
        a.set_setting("system", "daily_budget_usd", str(GUEST_CLAUDE_BUDGET))    # guests: a small Claude budget, then free Gemini
    return a


class Question(BaseModel):
    text: str
    thread: str | None = None
    provider: str | None = None
    mode: str | None = None
    context: dict | None = None
    source: str = ""


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
    if is_guest(who):                                   # a visitor's own Home: their coins, their book, their next step
        from jarvis.service import account as visitor

        return visitor.home(J())
    return {"summary": views.day_summary(J()), "feed": views.feed(J(), hours=72, limit=40), "mission": views.mission(J())}


class WatchIn(BaseModel):
    coins: list[str] | None = None
    group: str | None = None
    kind: str | None = None
    mode: str = "ask"


class WatchChange(BaseModel):
    mode: str | None = None
    state: str | None = None


@app.get("/v3/watches/mine")
def my_watches(who: str = Depends(owner)) -> dict:
    """This account's own watches (build plan 1.4a), the kinds it may pick (evidence-allowed only) and the modes."""
    from jarvis.service import watches

    return {"watches": watches.list_(J()), "kinds": watches.kinds(), "modes": watches.MODES, "groups": watches.GROUPS}


@app.post("/v3/watches/mine")
def my_watch_create(b: WatchIn, who: str = Depends(owner)) -> dict:
    from jarvis.service import watches

    try:
        return watches.create(J(), b.coins, b.group, b.kind, b.mode, by=who)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v3/watches/mine/{wid}")
def my_watch_change(wid: str, b: WatchChange, who: str = Depends(owner)) -> dict:
    from jarvis.service import watches

    try:
        return watches.change(J(), wid, b.mode, b.state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v3/agent/state")
def agent_state(who: str = Depends(owner)) -> dict:
    """'What are you doing right now' for this account (build plan 1.8)."""
    from jarvis.service import watches

    return watches.state(J()) | {"last_check": STATE_W.get("last")}


@app.get("/v3/agent/activity")
def agent_activity(since_t: int = 0, who: str = Depends(owner)) -> dict:
    """'What changed since ...' for this account (build plan 1.8)."""
    from jarvis.service import watches

    return watches.since(J(), since_t)


@app.get("/v3/books")
def books_view(who: str = Depends(owner)) -> dict:
    """Books as one list (build plan 1.3): every trade this account holds, each stamped with who took it. The same shape for
    Madhav and for a visitor; a visitor's holds only their own trades."""
    from jarvis.service import books

    return books.view(J(), J().name_of(who), owner=not is_guest(who))


@app.get("/v3/books/trade/{tid}")
def books_trade(tid: str, who: str = Depends(owner)) -> dict:
    """One trade's story (plan 3.3b): reasons, start, stop, peak, low, exits and its decision card."""
    from jarvis.service import books

    try:
        return books.story(J(), tid, J().name_of(who), owner=not is_guest(who))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v3/watchlists")
def watchlists(who: str = Depends(owner)) -> dict:
    """Watchlists (was Markets), per account: a visitor's coins, or Madhav's 10."""
    if is_guest(who):
        from jarvis.service import account

        return account.markets(J())
    return views.markets(J())


@app.get("/v3/holdings")
def holdings(who: str = Depends(owner)) -> dict:
    if is_guest(who):                                   # a visitor's Books: their own practice book only
        from jarvis.service import account as visitor

        return visitor.books(J())
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


@app.get("/v3/evidence/pipeline")
def ev_pipeline(who: str = Depends(owner)) -> dict:
    return views.evidence_pipeline(J())


@app.get("/v3/evidence/week")
def ev_week(days: int = 7, who: str = Depends(owner)) -> dict:
    """Request #34: wins and losses of the last 7 days across every book."""
    from jarvis.service import week

    return week.week(J(), max(1, min(int(days or 7), 90)))


@app.get("/v3/evidence/live")
def ev_live(who: str = Depends(owner)) -> dict:
    """The Evidence page: inside the logic repair, live (Madhav, 2026-10-05)."""
    from jarvis.service import evidence_live

    return evidence_live.build(J())


def _owner_only(who: str) -> None:
    if is_guest(who):
        raise HTTPException(status_code=403, detail="Only Madhav manages accounts.")


@app.get("/v3/people")
def people(who: str = Depends(owner)) -> dict:
    """Madhav's account and the visitors he invited (owner only)."""
    _owner_only(who)
    return _main().people()


@app.post("/v3/people/invite")
def people_invite(b: Invite, who: str = Depends(owner)) -> dict:
    _owner_only(who)
    try:
        inv = _main().invite(b.name, b.email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    inv["link"] = f"https://livetrading247.com/join?code={inv['code']}"
    return inv


@app.post("/v3/people/remove")
def people_remove(b: Person, who: str = Depends(owner)) -> dict:
    """Removes a visitor (sign-in stops at once; their practice book is archived) or cancels an unused invite (by code)."""
    _owner_only(who)
    ok = _main().remove_person(b.email)
    arch = _archive_sandbox(b.email) if "@" in b.email else None
    return {"ok": ok, "archived": arch}


class Extend(BaseModel):
    email: str
    days: float = 3


@app.post("/v3/people/extend")
def people_extend(b: Extend, who: str = Depends(owner)) -> dict:
    """Madhav gives a visitor more practice days, counted from now."""
    _owner_only(who)
    try:
        return _main().extend(b.email, max(0.5, min(float(b.days), 90)))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v3/practice/reset")
def practice_reset(who: str = Depends(owner)) -> dict:
    """A visitor starts over: their practice book goes back to $1,000 and an empty history (the old one is archived)."""
    if not who.startswith("guest:"):
        raise HTTPException(status_code=400, detail="Reset is for practice accounts; Madhav's books are the real paper books.")
    return {"ok": True, "archived": _archive_sandbox(who.split(":", 1)[1])}


class Setup(BaseModel):
    name: str | None = None
    coins: list[str] | None = None
    tz: str | None = None
    experience: str | None = None
    crypto: str | None = None
    risk: str | None = None
    voice: str | None = None
    theme: str | None = None
    tour_done: bool = False
    capital: int | None = None
    start_trading: bool = False
    method: str | None = None
    paused: bool | None = None
    auto: bool | None = None


@app.post("/v3/me/setup")
def me_setup(b: Setup, who: str = Depends(owner)) -> dict:
    """Profile answers for any account (build plan 1.1): a visitor's setup steps, and everyone's time zone, voice, theme and
    experience. The owner's account keeps no setup steps (name, coins, capital, start are visitor steps)."""
    from jarvis.service import account

    body = b.model_dump()
    if not is_guest(who):
        body = {k: body.get(k) for k in ("tz", "voice", "theme", "experience", "crypto", "risk")}
    try:
        r = account.update(J(), body, who.split(":", 1)[-1] if is_guest(who) else "")
        return r if is_guest(who) else {"profile": account.owner_profile(J())}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


class Order(BaseModel):
    side: str = "buy"
    coin: str
    usd: float | None = None
    stop: float | None = None
    target: float | None = None
    reason: str = ""
    confirm: bool = False


@app.post("/v3/manual/order")
def manual_order(b: Order, who: str = Depends(owner)) -> dict:
    """'Trade myself': a paper order in the caller's own book. Without confirm it only previews (nothing changes)."""
    p = {"side": b.side, "coin": b.coin, "usd": b.usd, "stop": b.stop, "target": b.target, "reason": b.reason}
    try:
        px = J().prices()
        return MN().execute(who, p, px, trigger="direct") if b.confirm else MN().preview(p, px)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v3/me")
def me(who: str = Depends(owner)) -> dict:
    g = who.startswith("guest:")
    if g:
        from jarvis.service import account as visitor

        v = visitor.me(J())
        return {"who": who.split(":", 1)[-1], "guest": True, "name": v["profile"].get("name") or _main().name_of(who), **v,
                "needs_you": len(M().pending()),
                "practice_note": "Your own practice account: paper money only, your coins, your trades. Nothing here is real money."}
    from jarvis.service import account

    return {"who": who.split(":", 1)[-1], "guest": g, "name": _main().name_of(who), "profile": account.owner_profile(J()), "stage": "owner",
            "needs_you": len(M().pending()) + (1 if J()._layer().pending() else 0),
            "practice_note": "Practice mode: everything works like Madhav's app, but your orders, alerts and changes go to your own "
                             "practice book. Kill switch, autopilot and portfolio approvals are locked." if g else ""}


class OnboardIn(BaseModel):
    step: str
    value: Any = None
    tz: str | None = None


@app.get("/v3/onboard")
def onboard_get(who: str = Depends(owner)) -> dict:
    """Plan Phase 5: the first conversation, where this visitor is in it (Madhav's account has none)."""
    if not is_guest(who):
        return {"step": "done", "done": True, "log": []}
    from jarvis.service import onboard

    return onboard.prompt(J())


@app.post("/v3/onboard")
def onboard_post(b: OnboardIn, who: str = Depends(owner)) -> dict:
    if not is_guest(who):
        return {"step": "done", "done": True, "log": []}
    from jarvis.service import onboard

    try:
        return onboard.answer(J(), b.step, b.value, who.split(":", 1)[-1], b.tz)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v3/onboard/restart")
def onboard_restart(who: str = Depends(owner)) -> dict:
    if not is_guest(who):
        return {"step": "done", "done": True, "log": []}
    from jarvis.service import onboard

    onboard.start_over(J())
    return onboard.prompt(J())


class OnboardCapital(BaseModel):
    amount: int


class OnboardMode(BaseModel):
    mode: str


@app.post("/v3/onboard/capital")
def onboard_capital(b: OnboardCapital, who: str = Depends(owner)) -> dict:
    if not is_guest(who):
        raise HTTPException(status_code=400, detail="only practice accounts")
    from jarvis.service import onboard

    try:
        return onboard.set_capital(J(), b.amount, who.split(":", 1)[-1])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v3/onboard/mode")
def onboard_mode(b: OnboardMode, who: str = Depends(owner)) -> dict:
    if not is_guest(who):
        raise HTTPException(status_code=400, detail="only practice accounts")
    from jarvis.service import onboard

    try:
        return onboard.set_mode(J(), b.mode, who.split(":", 1)[-1])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v3/onboard/demo")
def onboard_demo(who: str = Depends(owner)) -> dict:
    """The DEMO trade from the first conversation (never in a book); gone at the first sign-out or after 24 hours."""
    if not is_guest(who):
        return {"demo": None}
    from jarvis.service import onboard

    return {"demo": onboard.demo(J())}


@app.post("/v3/onboard/demo/clear")
def onboard_demo_clear(who: str = Depends(owner)) -> dict:
    if is_guest(who):
        from jarvis.service import onboard

        onboard.clear_demo(J())
    return {"ok": True}


class WebSub(BaseModel):
    sub: dict
    device: str = ""


@app.get("/v3/push/web")
def web_push_info(who: str = Depends(owner)) -> dict:
    """Plan 1.7: the key a browser needs to subscribe, how many of this account's devices are on, and whether email is set up."""
    from jarvis.service import account, notify

    return {"key": notify.public_key(), "devices": notify.devices(J()), "email_ready": notify.email_ready(),
            "email_alerts": bool(account.profile(J().db).get("email_alerts"))}


@app.post("/v3/push/web/subscribe")
def web_push_subscribe(b: WebSub, who: str = Depends(owner)) -> dict:
    from jarvis.service import notify

    try:
        r = notify.subscribe(J(), b.sub, b.device)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    notify.web_push(J(), "Notifications are on", "Ananta will tell you here when a watch fires or something needs you.")
    return r


@app.post("/v3/push/web/email")
def web_push_email(b: dict, who: str = Depends(owner)) -> dict:
    from jarvis.service import account, notify

    if not notify.email_ready():
        raise HTTPException(status_code=400, detail="Email is not set up on the service yet.")
    J().db.execute("INSERT OR REPLACE INTO visitor_profile VALUES ('email_alerts', ?)", (json.dumps(bool(b.get("on"))),))
    J().db.commit()
    return {"email_alerts": bool(account.profile(J().db).get("email_alerts"))}


_PUB = {"t": 0.0, "v": None}


@app.get("/v3/public/status")
def public_status() -> dict:
    """The public front page (no sign-in): a few honest, live numbers about Ananta. Nothing personal, no trades, no accounts.
    Cached for 10 minutes."""
    import time as _t

    if _PUB["v"] and _t.time() - _PUB["t"] < 600:
        return _PUB["v"]
    out: dict = {"paper_only": True}
    try:
        from jarvis.service import evidence_live, views

        s = evidence_live.summary(_main())
        res = {x["key"]: x for x in (s.get("results") or {}).get("items") or []}
        out |= {"days": s.get("headline", "").split(" of paper")[0].replace("Day ", "") or None,
                "events": (s.get("results") or {}).get("events"), "goal_events": (s.get("results") or {}).get("goal_events"),
                "real_per_100": (res.get("real") or {}).get("avg_usd"), "random_per_100": (res.get("random") or {}).get("avg_usd"),
                "trades_scored": sum((res.get(k) or {}).get("closed") or 0 for k in ("real", "would_be", "no_type", "random")),
                "rebuilds": (s.get("reconstruction") or {}).get("total"), "mismatches": (s.get("reconstruction") or {}).get("mismatches"),
                "reviews": len(views.evidence_collected(_main()).get("forwarded") or []), "coins_live": 10}
        try:
            from jarvis.service import registry as _reg

            out["coins_watched"] = (_reg.load(_main()).get("counts") or {}).get("listed")
        except Exception:  # noqa: BLE001
            pass
    except Exception as exc:  # noqa: BLE001
        out["error"] = str(exc)[:80]
    _PUB.update(t=_t.time(), v=out)
    return out


@app.get("/v3/costs")
def costs_summary(days: int = 30, who: str = Depends(owner)) -> dict:
    """Where the AI money goes, by job and model, for every account together (Madhav only)."""
    if is_guest(who):
        raise HTTPException(status_code=403, detail="Only Madhav sees the costs.")
    from jarvis.service import costs

    m = _main()
    dbs = [m.db] + [_sandbox("guest:" + em).db for (em,) in m.db.execute("SELECT email FROM users").fetchall()]
    return costs.summary(dbs, days)


_ACC = {"running": False}


@app.get("/v3/acceptance")
def acceptance_latest(who: str = Depends(owner)) -> dict:
    """Phase 6.1: the latest run of the ten automatic checks and the no-leak test."""
    from jarvis.service import acceptance

    return {"running": _ACC["running"], "latest": acceptance.latest() if not is_guest(who) else None}


@app.post("/v3/acceptance/run")
def acceptance_run(who: str = Depends(owner)) -> dict:
    """Run the checks now, in the background (a few minutes; counted on the Test lab budget)."""
    if is_guest(who):
        raise HTTPException(status_code=403, detail="Only Madhav can run the acceptance checks.")
    if _ACC["running"]:
        return {"running": True}
    from jarvis.service import acceptance

    main = _main()
    vis = _sandbox("guest:" + acceptance.TEST_VISITOR)

    def go():
        _ACC["running"] = True
        try:
            acceptance.run(main, vis)
        finally:
            _ACC["running"] = False

    _threading.Thread(target=go, daemon=True).start()
    return {"running": True}


@app.get("/v3/concepts/next")
def concept_next(who: str = Depends(owner)) -> dict:
    """Plan 4.5: the next idea to introduce to this account (once each, when it first matters), or none."""
    from jarvis.service import concepts

    return {"concept": concepts.due(J())}


@app.post("/v3/concepts/{cid}/seen")
def concept_seen(cid: str, who: str = Depends(owner)) -> dict:
    from jarvis.service import concepts

    try:
        return concepts.seen(J(), cid)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v3/ask/chips")
def ask_chips(days: int = 7, who: str = Depends(owner)) -> dict:
    """Plan 4.1: the weekly table of chips shown and tapped, to refine them."""
    from jarvis.service import ask as _a

    return {"days": days, "chips": _a.chip_stats(J(), days)}


@app.get("/v3/chain")
def chain_board(who: str = Depends(owner)) -> dict:
    """Madhav's decision chain for all 10 coins: where each one stops (fail-closed) and why."""
    from jarvis.service import chain

    if is_guest(who):                                   # a visitor's chain counts only their own trades (plan 1.2a, 3.5)
        from jarvis.service import account
        return chain.board(J(), book=account.chain_book(J()))
    return chain.board(J())


@app.get("/v3/layers")
def layers_board(who: str = Depends(owner)) -> dict:
    """The layer map: every part of Ananta, its layer, status, whether it may act, and the known gaps."""
    from jarvis.service import layers

    return layers.board(J().dir)


@app.get("/v3/zones")
def zones_board(who: str = Depends(owner)) -> dict:
    """Zones around every coin's price, which coins are inside one, and recent zone entries with how they ended."""
    from jarvis.service import zones_watch

    return zones_watch.board(J())


@app.get("/v3/zones/{coin}")
def zones_coin(coin: str, who: str = Depends(owner)) -> dict:
    from jarvis.service import zones_watch

    r = zones_watch.coin(J(), coin)
    if r is None:
        raise HTTPException(status_code=404, detail=f"No zones for {coin}")
    return r


class ReqStatus(BaseModel):
    status: str
    note: str = ""


@app.get("/v3/requests")
def requests_list(who: str = Depends(owner)) -> dict:
    """Requests logged for the repair shop from Ask Ananta / voice, newest first, with their status."""
    from jarvis.service import requests_log

    return {"requests": requests_log.list_(J())}


@app.post("/v3/requests/{rid}")
def requests_status(rid: str, b: ReqStatus, who: str = Depends(owner)) -> dict:
    from jarvis.service import requests_log

    if str(who).startswith("guest:"):
        raise HTTPException(status_code=403, detail="Practice mode: only the owner updates the repair shop.")
    r = _run(requests_log.set_status, J(), rid, b.status, b.note)
    requests_log.notify(J(), push=_push)                               # tell the phone now, not in 15 minutes
    J().audit(who, "request.status", f"{rid} {b.status}", "OK")
    return {"ok": True, "request": r}


class FlagIn(BaseModel):
    text: str
    market: str = "crypto"
    screen: str = ""
    route: str = ""


class FlagChoice(BaseModel):
    option: int
    words: str = ""


def _owner_only(who: str) -> None:
    if str(who).startswith("guest:"):
        raise HTTPException(status_code=403, detail="Practice mode: only the owner flags fixes.")


@app.post("/v3/flags")
def flags_new(b: FlagIn, who: str = Depends(owner)) -> dict:
    """Madhav's Flag button (Oct 23): file the request now and offer up to three fixes, each SAFE (built and deployed by the repair
    worker) or DECISION (near trading: a plan for his yes). Both markets come here; the flag names its market."""
    from jarvis.service import fixflow

    _owner_only(who)
    r = _run(fixflow.flag, J(), b.text, b.market, b.screen, b.route)
    J().audit(who, "flag.new", f"#{r['num']} {b.market} {b.screen}", "OK")
    return r


@app.post("/v3/flags/{num}/choose")
def flags_choose(num: int, b: FlagChoice, who: str = Depends(owner)) -> dict:
    from jarvis.service import fixflow, requests_log

    _owner_only(who)
    r = _run(fixflow.choose, J(), num, b.option, b.words)
    requests_log.notify(J(), push=_push)
    J().audit(who, "flag.choose", f"#{num} option {b.option} -> {r['state']}", "OK")
    return r


@app.get("/v3/flags")
def flags_board(who: str = Depends(owner)) -> dict:
    """Every request with its flag flow (state, lane, steps, commit), newest first: the app's 'My flags' screen."""
    from jarvis.service import fixflow

    _owner_only(who)
    return {"flags": fixflow.board(J()), "states": fixflow.STATE_WORDS}


@app.get("/v3/scoreboard")
def scoreboard_board(who: str = Depends(owner)) -> dict:
    """Every watch's evidence book with the same columns, against its random baseline (docs/knowledge/watches.json)."""
    from jarvis.service import scoreboard

    return scoreboard.board(J())


@app.get("/v3/watches")
def watches_registry(who: str = Depends(owner)) -> dict:
    """The watch registry: every watch by section, where it runs, its entry, exit and evidence status; plus the eye's state."""
    from jarvis.service import eye, scoreboard

    return {**scoreboard.registry(J()), "eye": eye.status(_main())}


@app.get("/v3/eye")
def eye_status(who: str = Depends(owner)) -> dict:
    from jarvis.service import eye

    return eye.status(_main())


@app.get("/v3/health/parts")
def health_parts(who: str = Depends(owner)) -> dict:
    from jarvis.service import health as _h

    return _h.status(_main())


@app.get("/v3/brain")
def brain_report(days: int = 30, who: str = Depends(owner)) -> dict:
    from jarvis.service import brain

    return brain.report(J(), days)


@app.get("/v3/decisions/recent")
def decisions_recent(n: int = 10, who: str = Depends(owner)) -> dict:
    """Home (Madhav, 23 Oct): Ananta's recent decisions in plain words - a headline a person reads in two seconds, the whole message behind it.
    Display only, from the brain's own decision rows (TAKE and PASS with their thesis and plan); nothing is changed."""
    import datetime as _dt
    import json as _json


    j = J()
    names = {"BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana", "XRP": "XRP", "ADA": "Cardano", "DOGE": "Dogecoin", "AVAX": "Avalanche", "LINK": "Chainlink", "LTC": "Litecoin", "BCH": "Bitcoin Cash"}
    out = []
    for rid, t, coin, action, conf, size, price, plan, thesis, trade_id, note in j.db.execute(
            "SELECT id, t, coin, action, confidence, size_pct, price, plan, thesis, trade_id, note FROM brain_decisions ORDER BY t DESC LIMIT ?", (max(1, min(n, 50)),)):
        try:
            p = _json.loads(plan or "{}")
        except ValueError:
            p = {}
        name = names.get(coin, coin)
        px = f"${price:,.2f}" if price and price >= 10 else (f"${price:.4f}" if price else "")
        first = (thesis or "").split(". ")[0].strip()
        if first and first[:1].isupper() and first[1:2].islower() and first.split(" ")[0] not in names.values():   # "The dial…" -> "the dial…"; never "ADA" -> "aDA"
            first = first[:1].lower() + first[1:]
        if action == "TAKE":
            head = f"Bought {name} at {px} because {first if first else 'its setup fired'}"
        else:
            head = f"Passed on {name} at {px} because {first if first else 'the setup did not clear its bar'}"
        wrong = f"Wrong if: it closes under ${p['stop']:,} (the stop)." if p.get("stop") else ""
        msg = (f"What: {'a paper trade' if action == 'TAKE' else 'no trade'} in {name} at {px}" + (f", {size:.0f}% of the book" if action == "TAKE" and size else "") + ".\n"
               f"Why: {thesis or ''}\n" + (("For: " + "; ".join(p.get("for", [])[:4]) + "\n") if p.get("for") else "") + (("Against: " + "; ".join(p.get("against", [])[:3]) + "\n") if p.get("against") else "")
               + (wrong + "\n" if wrong else "") + f"Confidence {conf:.0f}%." + (f" Note: {note}" if note else ""))
        out.append({"id": rid, "t": int(t), "time": _dt.datetime.fromtimestamp(int(t)).strftime("%b %-d, %-I:%M %p"), "coin": coin, "action": action, "price": price,
                    "headline": head[:220], "message": msg[:2000], "confidence": conf, "link": f"/trade/{trade_id}" if trade_id else "/jarvis"})
    return {"decisions": out, "page": "/jarvis"}


@app.get("/v3/stance")
def stance_now(who: str = Depends(owner)) -> dict:
    """Fixes A2/A3: the brain's newest written stance, its expectations, and the morning scan's record."""
    from jarvis.service import stance

    return {"stance": stance.latest(J()), "record": stance.record(J())}


@app.get("/v3/brain/trade/{trade_id}")
def brain_trade(trade_id: str, who: str = Depends(owner)) -> dict:
    from jarvis.service import brain

    return _run(brain.trade_detail, J(), trade_id)


@app.get("/v3/officer")
def officer_notes(n: int = 7, who: str = Depends(owner)) -> dict:
    from jarvis.service import officer

    return {"notes": officer.latest(J(), n)}


@app.get("/v3/verdicts")
def verdicts(who: str = Depends(owner)) -> dict:
    """Every losing paper trade by its strategy's verdict, and the strategy list (Madhav, Oct 13)."""
    from jarvis.service import strategy_status

    r = strategy_status.losing_trades(J())
    return {**r, "strategies": strategy_status.strategies_live(r["by_strategy"])}


@app.get("/v3/situations")
def situations(days: int = 7, who: str = Depends(owner)) -> dict:
    from jarvis.service import learning

    return _run(learning.weekly_review, J(), days, False)


@app.get("/v3/book500")
def book500(who: str = Depends(owner)) -> dict:
    from jarvis.service import ndax_book

    return ndax_book.status(J())


@app.post("/v3/book500/resume")
def book500_resume(who: str = Depends(owner)) -> dict:
    from jarvis.service import ndax_book

    return ndax_book.resume(J())


@app.get("/v3/missed")
def missed_moves(days: int = 7, who: str = Depends(owner)) -> dict:
    from jarvis.service import missed

    return missed.recent(J(), days)


@app.get("/v3/reviews")
def trade_reviews(days: int = 7, who: str = Depends(owner)) -> dict:
    from jarvis.service import reviews

    return {**reviews.recent_reviews(J(), days), "evenings": reviews.latest(J(), 3)}


@app.get("/v3/tier30")
def tier30_report(who: str = Depends(owner)) -> dict:
    """The 30-coin paper tier (review #15): the T3 book and the H07-T30 watch, kept apart from the 10-coin books."""
    from jarvis.service import tier30

    return tier30.status(J())


@app.get("/v3/shadow/h07")
def shadow_h07_report(who: str = Depends(owner)) -> dict:
    """The short dip trade (H07) paper shadow: every signal since it started, its paper entry, exit and result."""
    from jarvis.service import shadow_h07

    return shadow_h07.report(J())


@app.get("/v3/credit")
def credit_report(who: str = Depends(owner)) -> dict:
    """Credit tracking: what each layer said at every daily close, and how the next 20 days went with and without it."""
    from jarvis.service import credit

    return credit.report(J())


@app.get("/v3/reads")
def reads_board(who: str = Depends(owner)) -> dict:
    """Madhav's three buy setups (capitulation, higher-low retest, quiet base) on every coin at the last daily close."""
    from jarvis.service import reads_watch

    return reads_watch.board(J())


@app.get("/v3/reads/{coin}")
def reads_coin(coin: str, who: str = Depends(owner)) -> dict:
    from jarvis.service import reads_watch

    r = reads_watch.coin(J(), coin)
    if r is None:
        raise HTTPException(status_code=404, detail=f"No reads for {coin}")
    return r


@app.post("/v3/reads/{coin}/news")
def reads_news(coin: str, who: str = Depends(owner)) -> dict:
    """The blunder guard on demand: an AI look at the last few days of news about this coin (Claude Haiku, about a cent)."""
    from jarvis.service import reads_watch

    if str(who).startswith("guest:"):
        raise HTTPException(status_code=403, detail="Practice mode: the news check uses Madhav's AI budget, so it is locked here.")
    c = coin.upper()
    if c not in reads_watch.NAMES:
        raise HTTPException(status_code=404, detail=f"{coin} is not one of our coins")
    res = reads_watch.news_check(J(), c)
    J().audit(who, "reads.news", f"{c} {res.get('verdict')}", "OK")
    if res.get("verdict") != "NOT_CHECKED":
        import json as _json

        from jarvis.service import news_watch

        news_watch._table(J())
        J().db.execute("INSERT OR REPLACE INTO news_log VALUES (?,?,?,?,?,?)",
                       (news_watch.today(J()), c, int(J().now()), res.get("verdict"), res.get("why"), _json.dumps(res)))
        J().db.commit()
    return {"coin": c, **res}


@app.get("/v3/knowledge/hypotheses")
def knowledge_hypotheses(who: str = Depends(owner)) -> dict:
    import json as _json

    p = core.docs_dir(J().dir) / "knowledge" / "hypotheses.json"
    return _json.loads(p.read_text()) if p.exists() else {"hypotheses": []}


@app.get("/v3/cockpit")
def cockpit(who: str = Depends(owner)) -> dict:
    return views.cockpit(J())


def _with_country(ctx, request: Request):
    """The country Cloudflare saw the request come from (CF-IPCountry): who might be speaking on Madhav's account (Oct 11)."""
    c = request.headers.get("cf-ipcountry")
    return {**(ctx if isinstance(ctx, dict) else {}), "country": c} if c else ctx


@app.post("/v3/ask")
def ask_q(b: Question, request: Request, who: str = Depends(owner)) -> dict:
    ctx = _with_country(b.context, request)
    return _run(lambda: A().ask(who, b.text, b.thread, b.provider, b.mode, None, ctx, source="eval" if b.source == "eval" else ""))


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


@app.get("/v3/ask/last")
def ask_last(who: str = Depends(owner)) -> dict:
    """The newest real conversation: the app continues it when it is under 6 minutes old, else offers it in a box (Oct 11)."""
    return {"last": A().last_conversation(), "continue_minutes": 6}


@app.post("/v3/ask/speaker")
def ask_speaker(body: dict, who: str = Depends(owner)) -> dict:
    """Who Ananta talks with in a conversation: a person's id or name hands it over, null brings Madhav back (the chip's "I'm back")."""
    if is_guest(who):
        raise HTTPException(status_code=403, detail="Introductions work in Madhav's account only.")
    from jarvis.service import ask as askmod, people

    th = str(body.get("thread") or "")
    if not th:
        raise HTTPException(status_code=400, detail="thread missing")
    j = A().j
    if body.get("person"):
        p = people.find(str(body["person"])) or people.resolve(str(body["person"]))
        if not p:
            raise HTTPException(status_code=404, detail="not one of Madhav's people")
        people.set_speaker(j, th, p)
        return {"talking_to": askmod._speaker(j, th), "opener": people.opener(p)}
    people.back(j, th)
    return {"talking_to": None}


@app.get("/v3/people")
def people_list(who: str = Depends(owner)) -> dict:
    """Madhav's people (names and relations only) for the app's "talking with" menu; never shown to guests."""
    if is_guest(who):
        return {"people": []}
    from jarvis.service import people

    return {"people": [{"id": p["id"], "name": p["names"][0], "relation": p.get("relation")} for p in people.load().get("people") or []]}


@app.get("/v3/ask/thread/{thread}/export")
def ask_export(thread: str, who: str = Depends(owner)) -> dict:
    return {"text": _run(A().export, thread)}


@app.post("/v3/ask/thread/{thread}/delete")
def ask_delete(thread: str, who: str = Depends(owner)) -> dict:
    return A().delete_thread(thread)


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
    if is_guest(who):                                   # a visitor's Markets: only the coins they picked
        from jarvis.service import account as visitor

        return visitor.markets(J())
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


def _locked_for_guests(who: str, what: str) -> None:
    if is_guest(who):
        raise ValueError(f"Practice mode: {what} belong to Madhav's real paper books, so they are locked here.")


def _switch(who: str, p: dict) -> dict:
    _locked_for_guests(who, "the kill switch and autopilot")
    if p.get("switch") == "kill_switch":
        return J().set_kill(who, bool(p.get("on")), True)
    if p.get("switch") == "autopilot":
        return {"mode": J().set_mode(who, "AUTO" if p.get("on") else "SUGGEST", True)}
    raise ValueError("unknown switch")


def _portfolio_decision(who: str, p: dict) -> dict:
    _locked_for_guests(who, "portfolio approvals")
    ids = p.get("ids") or "all"
    if p.get("decision") == "approve":
        return {"fills": J().approve(who, ids)}
    return {"rejected": J().reject(who, ids)}


def _alert_off(who: str, p: dict) -> dict:
    AL().turn_off(who, p["id"])
    return {"off": p["id"]}


def _setting(who: str, p: dict) -> dict:
    _locked_for_guests(who, "settings")
    return A().set_setting(who, p["key"], p["value"])


def executors() -> dict:
    """What each kind of card does once the owner confirms it (Face ID / passcode in the app)."""
    return {"mandate": M().apply_mandate_change, "alert": AL().create,
            "paper_order": lambda who, p: MN().execute(who, p, J().prices()),
            "levels": lambda who, p: MN().set_levels(who, p["coin"], p.get("stop"), p.get("target"), J().prices()),
            "switch": _switch, "portfolio_decision": _portfolio_decision, "alert_off": _alert_off, "setting": _setting}


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
    source: str = ""
    prefix: str = ""          # what he said just before, when he stopped mid-sentence (joined to this turn)
    client_timing: dict | None = None   # Oct 20 (repair #74): the app's mic timing for this turn (stored with his message)


@app.post("/v3/voice/turn")
def voice_turn(b: VoiceTurn, request: Request, who: str = Depends(owner)) -> dict:
    return _run(lambda: A().voice_turn(who, b.audio_b64, b.mime, b.thread, b.mode, _with_country(b.context, request), source="eval" if b.source == "eval" else "",
                                       prefix=b.prefix, client_timing=b.client_timing))



def _push(title: str, body: str):
    from src.intelligence.paper_watch import push_phone

    return push_phone(title, body, level="EVENT")


def _push_warn(title: str, body: str):
    from src.intelligence.paper_watch import push_phone

    return push_phone(title, body, level="WARN")


def background_jobs() -> dict:
    """Every 15 minutes: check alerts (no AI cost); write the morning / evening brief once each (free model)."""
    import time as _t

    from jarvis.service import health as _health

    _health.STATE["jobs_t"] = _t.time()
    ex = J()._explorer()
    out = {"fired": AL().check(ex, push=_push), "manual_stops": MN().check_stops(ex.prices() if ex else {}, push=_push)}
    try:                                                                # Oct 15 (research audit): a verdict Madhav changes is on record within 15 minutes
        from jarvis.service import strategy_status

        out["verdicts_recorded"] = strategy_status.record_verdicts(J())
    except Exception as exc:  # noqa: BLE001
        out["verdicts_error"] = str(exc)[:200]
    try:
        from jarvis.service import reads_watch

        out["your_setups"] = reads_watch.watch(J(), push=_push)
    except Exception as exc:  # noqa: BLE001  never let the reads stop the other jobs
        out["your_setups_error"] = str(exc)[:200]
    try:
        from jarvis.service import zones_watch

        out["zones"] = zones_watch.watch(J())
    except Exception as exc:  # noqa: BLE001
        out["zones_error"] = str(exc)[:200]
    try:
        from jarvis.service import news_watch

        out["news"] = news_watch.watch(J())
    except Exception as exc:  # noqa: BLE001
        out["news_error"] = str(exc)[:200]
    try:
        from jarvis.service import watch_engine

        out["daily_watches"] = watch_engine.run(J())                  # your setups, the short dip trade, random baselines, zone-touch exits
    except Exception as exc:  # noqa: BLE001
        out["daily_watches_error"] = str(exc)[:200]
    try:
        from jarvis.service import tier30

        out["tier30"] = tier30.run(J())                                 # the 30-coin paper tier: T3 book + H07-T30 (review #15)
    except Exception as exc:  # noqa: BLE001
        out["tier30_error"] = str(exc)[:200]
    try:
        from jarvis.service import market_shift

        out["market_shift"] = market_shift.close(J(), push=_push)    # did the daily close flip the market regime?
    except Exception as exc:  # noqa: BLE001
        out["market_shift_error"] = str(exc)[:200]
    try:
        from jarvis.service import brain

        out["brain_woke"] = brain.scan(J(), (out.get("daily_watches") or {}).get("opened"))   # moments for Jarvis's brain
        out["brain_passes_scored"] = brain.settle_passes(J())
    except Exception as exc:  # noqa: BLE001
        out["brain_error"] = str(exc)[:200]
    try:
        from jarvis.service import stance

        out["stance"] = stance.plan(J())                               # fixes A2/A3: once a day after the daily close
        out["expectations"] = stance.watch(J())                         # the brain's own written plans against the market
    except Exception as exc:  # noqa: BLE001
        out["stance_error"] = str(exc)[:200]
    try:
        from jarvis.service import bold

        out["bold"] = bold.run(J())                                     # fix A8: off until Madhav approves (two locks)
    except Exception as exc:  # noqa: BLE001
        out["bold_error"] = str(exc)[:200]
    try:
        from jarvis.service import missed

        if _t.time() % 86400 >= 1800:                                  # half an hour after the daily close: yesterday's biggest moves
            out["missed"] = missed.run(J())
    except Exception as exc:  # noqa: BLE001
        out["missed_error"] = str(exc)[:200]
    try:
        from jarvis.service import evidence_live

        out["rebuild_log"] = evidence_live.record_rebuild(J())          # keep every nightly rebuild (the file is overwritten)
    except Exception as exc:  # noqa: BLE001
        out["rebuild_log_error"] = str(exc)[:200]
    try:
        from jarvis.service import reviews

        out["trade_reviews"] = reviews.review_closed(J())
        out["evening_review"] = reviews.evening(J(), push=_push)
    except Exception as exc:  # noqa: BLE001
        out["reviews_error"] = str(exc)[:200]
    try:
        from jarvis.service import credit

        out["credit"] = credit.watch(J())
    except Exception as exc:  # noqa: BLE001
        out["credit_error"] = str(exc)[:200]
    try:
        from jarvis.service import requests_log

        out["requests"] = requests_log.notify(J(), push=_push)       # "Fixed: request 4" on the phone
    except Exception as exc:  # noqa: BLE001
        out["requests_error"] = str(exc)[:200]
    try:  # OD-SHADOW-LANE (Oct 20): the attention board and the intraday breakout cross, logged blind; no result, no book
        from jarvis.service import shadow

        shadow.hook_15m(J(), out)
    except Exception as exc:  # noqa: BLE001  never breaks the jobs (hook_15m already swallows; this catches a failed import)
        out["shadow"] = {"error": f"{_t.strftime('%Y-%m-%d %H:%M:%S', _t.gmtime())} UTC {str(exc)[:200]}"}
    a = A()
    if a.setting("ask_enabled") == "1" and a.setting("voice_enabled") == "1":
        kind = AL().due_brief()
        if kind:
            out["brief"] = AL().write_brief(kind, lambda q: a.ask("ananta (scheduled)", q, mode="deep"), push=_push)
    return out


@app.get("/v3/alerts")
def alerts_list(who: str = Depends(owner)) -> dict:
    return {"alerts": AL().list()}


# --- the trader's discipline (Madhav, 24 Oct 2026, "Yes to all"): one plan line, the checks, the reconstruction card and its queue ---
@app.get("/v3/plan")
def plan_tonight(who: str = Depends(owner)) -> dict:
    from jarvis.service import discipline

    pl = discipline.latest_plan(J()) or discipline.plan_line(J())
    return {"plan": pl, "rules": discipline.rules().get("version"), "items": discipline.rules().get("items")}


@app.get("/v3/reconstruction/crypto")
def reconstruction_crypto(who: str = Depends(owner)) -> dict:
    from jarvis.service import reconstruct

    return {"card": reconstruct.latest(J()), "queue": reconstruct.queue(J()), "rules": reconstruct.RULES, "bars": reconstruct.BARS,
            "kind_words": reconstruct.KIND_WORDS}


class RxDecision(BaseModel):
    id: str
    words: str


@app.post("/v3/reconstruction/crypto/decide")
def reconstruction_decide(d: RxDecision, who: str = Depends(owner)) -> dict:
    from jarvis.service import reconstruct

    if is_guest(who):
        raise HTTPException(status_code=403, detail="the owner decides")
    try:
        r = reconstruct.decide(J(), d.id, d.words, by=who)
    except KeyError:
        raise HTTPException(status_code=404, detail="no such row")
    J().audit(who, "reconstruction.decide", d.id, d.words[:80])
    return r


@app.post("/v3/reconstruction/crypto/run")
def reconstruction_run(who: str = Depends(owner)) -> dict:
    from jarvis.service import reconstruct

    if is_guest(who):
        raise HTTPException(status_code=403, detail="the owner runs it")
    return {"result": reconstruct.evening(J(), force=True), "card": reconstruct.latest(J())}


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
    r = AL().write_brief(kind, lambda q: A().ask(who, q, mode="deep"))
    if not r:
        raise HTTPException(status_code=503, detail="Could not write the brief right now; try again in a minute.")
    return {"brief": AL().latest_brief()}


@app.get("/v3/inbox")
def inbox(who: str = Depends(owner)) -> dict:
    ps = [] if is_guest(who) else J()._layer().pending()     # the trend portfolio's suggestions are Madhav's, never a visitor's
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


# ---- test lab (suggested questions come from the same test catalog) ----
def _cases() -> dict:
    from pathlib import Path as _P
    import json as _json

    return _json.loads((_P(__file__).resolve().parents[1] / "evals" / "cases.json").read_text())


class Mark(BaseModel):
    run: str
    id: str
    provider: str
    verdict: str
    note: str = ""


@app.get("/v3/ask/suggestions")
def suggestions(who: str = Depends(owner)) -> dict:
    cs = _cases()["cases"]
    return {"questions": [c["q"] for c in cs if c.get("suggest")],
            "portfolio": [c["q"] for c in cs if c.get("suggest") == "portfolio"],
            "market": [c["q"] for c in cs if c.get("suggest") == "market"]}


def _evdir():
    from pathlib import Path as _P

    return _P(J().dir) / "eval_runs"


@app.get("/v3/evals")
def evals_list(who: str = Depends(owner)) -> dict:
    import json as _json

    out = []
    for f in sorted(_evdir().glob("*.json"), reverse=True)[:20]:
        d = _json.loads(f.read_text())
        out.append({"run": d["run"], "minutes": d.get("minutes"), "spend_usd": d.get("spend_usd"), "summary": d.get("summary")})
    return {"runs": out, "catalog": {"cases": len(_cases()["cases"]), "voice": len(_cases()["voice"])}}


@app.get("/v3/evals/{run}")
def evals_get(run: str, who: str = Depends(owner)) -> dict:
    import json as _json

    if not run.replace("T", "").replace("Z", "").isdigit():
        raise HTTPException(status_code=400, detail="bad run id")
    f = _evdir() / f"{run}.json"
    if not f.exists():
        raise HTTPException(status_code=404, detail="no such run")
    d = _json.loads(f.read_text())
    J().db.execute("CREATE TABLE IF NOT EXISTS eval_marks (run TEXT, id TEXT, provider TEXT, verdict TEXT, note TEXT, t INTEGER, PRIMARY KEY (run, id, provider))")
    marks = {(i, p): (v, n) for i, p, v, n in J().db.execute("SELECT id, provider, verdict, note FROM eval_marks WHERE run=?", (run,))}
    for r in d["results"]:
        m = marks.get((r["id"], r.get("provider", "system")))
        if m:
            r["verdict"], r["note"] = m
    return d


@app.post("/v3/evals/mark")
def evals_mark(b: Mark, who: str = Depends(owner)) -> dict:
    if b.verdict not in ("good", "ok", "bad"):
        raise HTTPException(status_code=400, detail="verdict is good, ok or bad")
    J().db.execute("CREATE TABLE IF NOT EXISTS eval_marks (run TEXT, id TEXT, provider TEXT, verdict TEXT, note TEXT, t INTEGER, PRIMARY KEY (run, id, provider))")
    J().db.execute("INSERT OR REPLACE INTO eval_marks VALUES (?,?,?,?,?,?)", (b.run, b.id, b.provider, b.verdict, b.note[:300], int(J().now())))
    J().db.commit()
    return {"ok": True}



class Audio(BaseModel):
    audio_b64: str
    mime: str = "audio/wav"


@app.post("/v3/voice/transcribe")
def voice_transcribe(b: Audio, who: str = Depends(owner)) -> dict:
    return {"text": _run(A().transcribe, b.audio_b64, b.mime)}


class AnswerVoice(BaseModel):
    sentences: list[str]
    voice: str = "Calm"
    speed: float = 1.0
    wait: bool = True


@app.post("/v3/voice/answer")
def voice_answer(b: AnswerVoice, who: str = Depends(owner)) -> dict:
    """The whole answer as one audio file in one voice, with the start time of each sentence (for highlights).
    wait=false only starts making it (used to get the tour ready ahead)."""
    from jarvis.service import speech

    if A().setting("voice_enabled") != "1":
        raise HTTPException(status_code=400, detail="Voice is switched off under More › Controls")
    key = speech.prepare_answer(b.sentences, b.voice, b.speed)
    if not b.wait:
        return {"id": key}
    try:
        return speech.answer_meta(key, 30)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"natural voice unavailable ({str(exc)[:80]})") from exc


@app.get("/v3/voice/answer/{key}")
def voice_answer_meta(key: str, who: str = Depends(owner)) -> dict:
    """Sentence start times etc. for audio that is already being made (e.g. right after an answer); waits until it is ready."""
    from jarvis.service import speech

    try:
        return speech.answer_meta(key, 30)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown answer audio") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"natural voice unavailable ({str(exc)[:80]})") from exc


@app.get("/v3/voice/answer/{key}/audio")
def voice_answer_audio(key: str, who: str = Depends(owner)):
    from fastapi.responses import Response

    from jarvis.service import speech

    try:
        body, ctype = speech.answer_audio(key, 30)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown answer audio") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"natural voice unavailable ({str(exc)[:80]})") from exc
    return Response(content=body, media_type=ctype, headers={"Cache-Control": "private, max-age=600", "Content-Length": str(len(body))})


class SpeakReq(BaseModel):
    sentences: list[str]
    voice: str = "Calm"


@app.post("/v3/voice/prepare")
def voice_prepare(b: SpeakReq, who: str = Depends(owner)) -> dict:
    """Start making natural-voice clips for an answer's sentences; the app then plays /v3/voice/clip/{id} in order."""
    from jarvis.service import speech

    if A().setting("voice_enabled") != "1":
        raise HTTPException(status_code=400, detail="Voice is switched off under More › Controls")
    return {"ids": speech.prepare(b.sentences, b.voice), "voices": list(speech.VOICES)}


@app.get("/v3/voice/clip/{cid}")
def voice_clip(cid: str, who: str = Depends(owner)):
    from fastapi.responses import Response

    from jarvis.service import speech

    try:
        body, ctype = speech.audio(cid)
        return Response(content=body, media_type=ctype, headers={"Cache-Control": "private, max-age=600"})
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="unknown clip") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"natural voice unavailable ({str(exc)[:80]})") from exc


class UiResult(BaseModel):
    answer_id: str
    results: list[dict] = []        # each move the app ran: {target, ok, landed}
    spots: list[str] = []           # the spots the answer was to light


@app.post("/v3/voice/ui_result")
def voice_ui_result(b: UiResult, who: str = Depends(owner)) -> dict:
    """Request #73 (Oct 20): after an answer moves the screen, the app says what really happened. Stored in voice_ui next to
    what Ananta planned and the say-show gate's note. The app sends it without waiting, so it never slows the voice."""
    from jarvis.service import sayshow

    j = J()
    return {"ok": _run(sayshow.record, j.db, b.answer_id, b.results, b.spots, int(j.now()))}
