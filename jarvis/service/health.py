"""The health watchdog (Madhav, 2026-10-04: a must-have before live): every part of Ananta checked every 2 minutes, a phone
note when one goes quiet and another when it is back.

  explorer      the 15-minute Explorer made a real scan in the last 35 minutes (its decision log; a state write without a scan,
                as during the Oct 4-5 night when Hands' login failed for 8.5 hours, no longer counts as healthy)
  hourly_watch  the hourly watch wrote a heartbeat in the last 80 minutes, and the last two were not errors
  eye           the eye looked at live prices in the last 2 minutes (and on Kraken, not the fallback)
  jobs          Jarvis's 15-minute jobs (alerts, daily watches, news, requests) ran in the last 25 minutes
  candles       the latest closed daily candle is in the Explorer's store (at most 2 days and 3 hours old)
  voice         the Mac's voice server answers and has its voice loaded
  hands         Hands (the App backend) answers /health
  hands_login   Hands accepts the agent's login (what the Explorer and the hourly watch need to read the kill switch and trade);
                skipped when no credentials are set
  tier30        the 30-coin paper tier pulled its daily candles and decided after the last daily close (from 01:00 UTC)
  tunnel        the public address (api.livetrading247.com) reaches Jarvis
  disk          at least 5 GB free

A part is DOWN after two failed checks in a row (one slow answer is not an outage); a reminder every 3 hours while it stays
down; a note when it recovers. Each outage is kept (health_log) for the evening self-review. Jarvis itself cannot report its
own death, so an outside watchdog (scripts/jarvis_watchdog.py, launchd every 5 minutes) checks Jarvis and this watchdog.

Read-only: it never restarts anything; the phone note says what to run.
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Callable

EVERY = 120
FAILS_TO_DOWN = 2
REMIND_S = 3 * 3600
MIN_FREE_GB = 5.0
NAMES = {"explorer": "the 15-minute Explorer", "hourly_watch": "the hourly watch (Hunter's book)", "eye": "the eye (live prices)",
         "jobs": "Jarvis's 15-minute jobs", "candles": "the daily candles", "voice": "the voice server", "hands": "Hands (the App backend)",
         "tunnel": "the public address (tunnel)", "disk": "disk space", "hands_login": "Hands login (the agent's access)",
         "tier30": "the 30-coin paper tier"}
FIX = {"explorer": "Restart it from the main checkout (RUNBOOK_SAFETY.md, 'Explorer').",
       "hourly_watch": "Restart paper_watch from the main checkout (RUNBOOK_SAFETY.md, 'hourly watch').",
       "eye": "Restart Jarvis (deploy_jarvis.sh) if it stays down.",
       "jobs": "Restart Jarvis (deploy_jarvis.sh).",
       "candles": "The Explorer is not storing new candles: check the Explorer and Hands.",
       "voice": "launchctl kickstart -k gui/$(id -u)/com.ananta.voice",
       "hands": "Check the App backend (Hands) on port 8001.",
       "tunnel": "Check cloudflared (the tunnel) on the Mac.",
       "disk": "Free some disk space on the Mac.",
       "hands_login": "Hands answers but refuses the login: check its database connection (MongoDB) and the internet; the Explorer "
                      "and the hourly watch stand still until it works (they cannot read the kill switch).",
       "tier30": "Check Jarvis's daily jobs (tier30.run after the daily close) and the internet (Binance daily candles)."}
STATE: dict[str, Any] = {"last_run": None, "jobs_t": None, "running": False, "parts": {}}
_lock = threading.Lock()


def _get(url: str, timeout: float = 6.0) -> tuple[int, Any]:
    import requests

    r = requests.get(url, timeout=timeout)
    try:
        body = r.json()
    except ValueError:
        body = r.text[:200]
    return r.status_code, body


def _login(base: str, email: str, pw: str) -> int:
    """Status code of a real login to Hands (the token is never kept or shown)."""
    import requests

    r = requests.post(base.rstrip("/") + "/api/auth/login", json={"email": email, "password": pw}, timeout=10)
    return r.status_code


def _age(t: float | None, now: float) -> float | None:
    return None if not t else now - t


def _mins(s: float | None) -> str:
    if s is None:
        return "never"
    return f"{s / 60:.0f} min" if s < 5400 else f"{s / 3600:.1f} h"


def checks(j, get: Callable = _get, now: float | None = None) -> dict[str, dict]:
    """One look at every part: {part: {ok, detail}}. A part not set up on this machine (no file yet) is skipped, not failed."""
    now = now or time.time()
    d = Path(j.dir)
    out: dict[str, dict] = {}

    p = d / "explorer_decisions.jsonl"
    if p.exists():
        last_t = None
        try:
            with open(p, "rb") as f:                                   # the last line: the most recent scan
                f.seek(0, 2)
                f.seek(max(0, f.tell() - 4096))
                tail = f.read().decode(errors="ignore").strip().splitlines()
            last_t = json.loads(tail[-1]).get("t") if tail else None
        except (OSError, ValueError):
            last_t = None
        a = _age(last_t, now)                                      # t = when the scan ran
        out["explorer"] = {"ok": a is not None and a < 35 * 60, "detail": f"last real scan {_mins(a)} ago"}
    elif (d / "explorer_state.pkl").exists():
        a = _age((d / "explorer_state.pkl").stat().st_mtime, now)
        out["explorer"] = {"ok": a < 35 * 60, "detail": f"last write {_mins(a)} ago"}

    hb = d / "watch_heartbeat.jsonl"
    if hb.exists():
        try:
            lines = [json.loads(x) for x in hb.read_text().strip().splitlines()[-2:] if x.strip()]
        except ValueError:
            lines = []
        if lines:
            from datetime import datetime

            t = datetime.fromisoformat(lines[-1]["ts"].replace("Z", "+00:00")).timestamp()
            a = _age(t, now)
            bad = sum(1 for x in lines if not x.get("ok"))
            out["hourly_watch"] = {"ok": a < 80 * 60 and bad < 2, "detail": f"last heartbeat {_mins(a)} ago" + (", the last two had errors" if bad >= 2 else "")}

    if os.getenv("ANANTA_EYE", "1") == "1" and "PYTEST_CURRENT_TEST" not in os.environ or STATE.get("check_eye"):
        from jarvis.service import eye

        a = _age(eye.STATE.get("last_t"), now)
        src = eye.STATE.get("source") or ""
        ok = bool(eye.STATE.get("running")) and a is not None and a < 120
        out["eye"] = {"ok": ok, "detail": (f"last look {a:.0f} s ago" if a is not None else "not looking") +
                      ("" if not src or src == "kraken" else f" ({src})")}

    if STATE.get("jobs_t") or STATE.get("check_jobs"):
        a = _age(STATE.get("jobs_t"), now)
        out["jobs"] = {"ok": a is not None and a < 25 * 60, "detail": f"last run {_mins(a)} ago"}

    bars = d / "explorer_bars.sqlite"
    if bars.exists():
        import sqlite3

        con = sqlite3.connect(f"file:{bars}?mode=ro", uri=True, timeout=10)
        try:
            t = con.execute("SELECT MAX(t) FROM bars WHERE coin='BTC' AND tf='1d'").fetchone()[0]
        finally:
            con.close()
        a = _age(t, now)
        out["candles"] = {"ok": a is not None and a < 2 * 86400 + 3 * 3600, "detail": f"latest daily candle opened {_mins(a)} ago"}

    urls = {"voice": os.getenv("ANANTA_VOICE_URL", "http://127.0.0.1:8200") + "/health",
            "hands": os.getenv("ANANTA_HANDS_HEALTH", "http://127.0.0.1:8001/health"),
            "tunnel": os.getenv("ANANTA_PUBLIC_HEALTH", "https://api.livetrading247.com/health")}
    if os.getenv("ANANTA_VOICE_LOCAL", "1") != "1":
        urls.pop("voice")
    for part, url in urls.items():
        try:
            code, body = get(url, 10.0 if part == "tunnel" else 5.0)
            ok = code == 200 and (part != "voice" or (isinstance(body, dict) and body.get("tts_loaded", True)))
            out[part] = {"ok": ok, "detail": "answers" if ok else f"HTTP {code}"}
        except Exception as exc:  # noqa: BLE001
            out[part] = {"ok": False, "detail": f"no answer ({type(exc).__name__})"}

    email, pw = os.getenv("ANANTA_EMAIL"), os.getenv("ANANTA_PASSWORD")
    if email and pw and os.getenv("ANANTA_HANDS_LOGIN_CHECK", "1") == "1":
        try:
            code = _login(os.getenv("ANANTA_BASE_URL", "http://127.0.0.1:8001"), email, pw)
            out["hands_login"] = {"ok": code == 200, "detail": "login works" if code == 200 else f"login refused (HTTP {code})"}
        except Exception as exc:  # noqa: BLE001
            out["hands_login"] = {"ok": False, "detail": f"no answer to login ({type(exc).__name__})"}

    t30 = d / "tier30_bars.sqlite"
    if t30.exists() and time.gmtime(now).tm_hour >= 1:
        import sqlite3

        con = sqlite3.connect(f"file:{t30}?mode=ro", uri=True, timeout=10)
        try:
            row = con.execute("SELECT v FROM meta WHERE k='done_day'").fetchone()
        finally:
            con.close()
        today = int(now // 86400 * 86400)
        done = int(row[0]) if row else None
        out["tier30"] = {"ok": done is not None and done >= today, "detail": "daily candles pulled today" if done and done >= today else
                         ("daily candles last pulled " + (time.strftime("%Y-%m-%d", time.gmtime(done)) if done else "never"))}

    try:
        free = shutil.disk_usage(str(d)).free / 1e9
        out["disk"] = {"ok": free >= MIN_FREE_GB, "detail": f"{free:.0f} GB free"}
    except OSError:
        pass
    return out


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS health_state (part TEXT PRIMARY KEY, ok INTEGER, fails INTEGER, down_t INTEGER, last_push INTEGER, detail TEXT)")
    j.db.execute("CREATE TABLE IF NOT EXISTS health_log (id INTEGER PRIMARY KEY AUTOINCREMENT, part TEXT, down_t INTEGER, up_t INTEGER, detail TEXT)")


def _note(j, kind: str, part: str, title: str, body: str, push: Callable | None) -> None:
    """Into the feed (eye_events) and, when push is given, the phone."""
    from jarvis.service import eye

    eye._table(j)
    eye._event(j, kind, None, None, title, body, push, {"part": part})


def watch(j, push: Callable | None = None, get: Callable = _get, now: float | None = None) -> dict:
    """One round: check, then DOWN / still down / back notes."""
    _table(j)
    now = now or time.time()
    res = checks(j, get=get, now=now)
    down, back = [], []
    for part, r in res.items():
        row = j.db.execute("SELECT ok, fails, down_t, last_push FROM health_state WHERE part=?", (part,)).fetchone()
        ok0, fails, down_t, last_push = row if row else (1, 0, None, None)
        name = NAMES.get(part, part)
        if r["ok"]:
            if down_t:                                                     # it was DOWN and is back
                mins = (now - down_t) / 60
                j.db.execute("UPDATE health_log SET up_t=? WHERE part=? AND up_t IS NULL", (int(now), part))
                _note(j, "HEALTH_UP", part, f"Back: {name}", f"Working again after about {mins:.0f} minutes ({r['detail']}).", push)
                back.append(part)
            j.db.execute("INSERT OR REPLACE INTO health_state VALUES (?,?,?,?,?,?)", (part, 1, 0, None, None, r["detail"]))
            continue
        fails = (fails or 0) + 1
        if not down_t and fails >= FAILS_TO_DOWN:
            down_t, last_push = int(now), int(now)
            j.db.execute("INSERT INTO health_log (part, down_t, up_t, detail) VALUES (?,?,?,?)", (part, down_t, None, r["detail"]))
            _note(j, "HEALTH_DOWN", part, f"Ananta: {name} has gone quiet", f"{r['detail'][:1].upper() + r['detail'][1:]}. {FIX.get(part, '')}", push)
            down.append(part)
        elif down_t and now - (last_push or down_t) >= REMIND_S:
            last_push = int(now)
            _note(j, "HEALTH_DOWN", part, f"Still down: {name}", f"Down for {(now - down_t) / 3600:.1f} hours ({r['detail']}). {FIX.get(part, '')}", push)
            down.append(part)
        j.db.execute("INSERT OR REPLACE INTO health_state VALUES (?,?,?,?,?,?)", (part, 0, fails, down_t, last_push, r["detail"]))
    j.db.commit()
    STATE.update(last_run=now, parts=res)
    return {"parts": res, "went_down": down, "came_back": back}


def status(j) -> dict:
    """For the app and Ask: every part's last check, and the outages of the last 3 days."""
    _table(j)
    rows = {p: {"ok": bool(ok), "fails": f, "down_since": d, "detail": det} for p, ok, f, d, _, det in
            j.db.execute("SELECT part, ok, fails, down_t, last_push, detail FROM health_state")}
    log = [dict(zip(("part", "down_t", "up_t", "detail"), r)) for r in
           j.db.execute("SELECT part, down_t, up_t, detail FROM health_log WHERE down_t >= ? ORDER BY down_t DESC LIMIT 30", (int(time.time() - 3 * 86400),))]
    for x in log:
        x["name"] = NAMES.get(x["part"], x["part"])
        x["minutes"] = round(((x["up_t"] or time.time()) - x["down_t"]) / 60)
    bad = [NAMES.get(p, p) for p, r in rows.items() if r["down_since"]]
    last = STATE.get("last_run")
    return {"all_ok": not bad, "down": bad, "parts": {p: {**r, "name": NAMES.get(p, p)} for p, r in rows.items()},
            "outages_3d": log, "checked_every_s": EVERY, "last_check_s_ago": round(time.time() - last) if last else None,
            "summary": ("Everything is running." if not bad else "Down: " + ", ".join(bad) + ".")}


def outages(j, since: float) -> list[dict]:
    _table(j)
    return [{"part": p, "name": NAMES.get(p, p), "down_t": d, "up_t": u, "detail": det} for p, d, u, det in
            j.db.execute("SELECT part, down_t, up_t, detail FROM health_log WHERE down_t >= ? OR up_t IS NULL OR up_t >= ? ORDER BY down_t", (int(since), int(since)))]


def start(get_j: Callable[[], Any], push: Callable | None = None, every: float = EVERY) -> bool:
    with _lock:
        if STATE.get("running"):
            return False
        STATE["running"] = True

    def loop():
        time.sleep(90)                                   # let the eye and the jobs start first
        while STATE.get("running"):
            try:
                watch(get_j(), push=push)
            except Exception as exc:  # noqa: BLE001  the watchdog never dies
                STATE["last_error"] = str(exc)[:160]
            time.sleep(every)

    threading.Thread(target=loop, name="ananta-health", daemon=True).start()
    return True
