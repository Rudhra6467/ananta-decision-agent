"""Kite Connect, read side only: candles, instruments, and the owner's holdings, positions and funds.

The token comes from ~/ananta_private/kite_token.json, written by the Jarvis service when Madhav signs in at
http://127.0.0.1:8100/kite/login (src/india/kite_auth.py in the agent repo). This module never logs in, never sees
the password or the API secret, and has no method that places, changes or cancels an order. It sends GET, with ONE exception approved by
Madhav on 19 Oct 2026 21:01 Toronto ("through kites margin calculator"): POST /margins/basket, Kite's margin calculator, which computes the
margin a basket would need and places nothing (used by the sizing v2 margin check). post_calc() refuses every other path (CALC_POSTS), and
india/leakcheck.py (kite_calls) fails if any other POST, PUT or DELETE appears in this file.
Limits (Kite forum, staff, 2018; the probe confirms): 3 requests a second; per request, minute 30 days, 5minute 90 days,
15minute 180 days, 60minute 365 days, day 2000 days. The token expires at 6 am IST; a 403 TokenException raises NeedLogin
and, when the ntfy topic is configured, sends the phone "Kite login needed" (at most once in 30 minutes).

12 Nov 2026 (the keen outside audit, G-54). The scheduled job owns the password sign-in. A read here that finds the token dead may ask for
one only when 30 minutes have passed since the last attempt of any kind and fewer than three such on-demand sign-ins ran in 24 hours
(on_demand_ok; the sign-in module checks the same again). And a refusal from Kite that is not a sign-in failure (a 4xx or 5xx on a read)
now leaves one line in ~/ananta_runs/kite_refusals.log, which the self-check reads: before, it left no trace anywhere.
The same day (the outside check of that repair, N10): a stamp that is there but cannot be read now says no to an on-demand sign-in (it said
yes, so the pause and the limit stopped working), and the note's stamp is read and written under a lock, so two readers at once send one note.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import time
from pathlib import Path

import requests

from india import paths

BASE = "https://api.kite.trade"
TOKEN_FILE = paths.private_dir() / "kite_token.json"
CALC_POSTS = ("/margins/basket",)   # calculation only: the one POST allowed (Madhav, 19 Oct 2026)
DAYS_PER_REQUEST = {"minute": 30, "3minute": 90, "5minute": 90, "10minute": 90, "15minute": 180, "30minute": 180, "60minute": 365, "day": 2000}


class NeedLogin(RuntimeError):
    pass


RUNS = Path.home() / "ananta_runs"
ATTEMPTS_FILE = RUNS / "kite_auto_attempts.json"   # written by the sign-in module (src/india/kite_auth.py in the agent repo): times and kinds only
ON_DEMAND_PAUSE_S = 1800                           # the same two numbers as the sign-in module's (tests/test_india_kite_ondemand.py reads both files)
ON_DEMAND_LIMIT = 3
REFUSALS_LOG = RUNS / "kite_refusals.log"          # one line per refused read: time, status, Kite's error type, the path; never a token or a parameter
NOTE_STAMP = RUNS / "kite_note_stamp.json"         # when the phone was last told "Kite login needed"
NOTE_EVERY_S = 1800

AUTO_ENV = paths.private_dir() / "kite_login.env"            # present only when Madhav has set up the automatic sign-in (22 Oct 2026)
AGENT_REPO = Path(os.path.expanduser("~/code/ananta-agent-research"))
AGENT_PY = Path(os.path.expanduser("~/ananta_venvs/jarvis/bin/python"))


def _read_token() -> dict | None:
    """The stored token, or None when it is missing or past 6 am IST."""
    if not TOKEN_FILE.exists():
        return None
    t = json.loads(TOKEN_FILE.read_text())
    if t.get("expires_at") and dt.datetime.fromisoformat(t["expires_at"]) <= dt.datetime.now(dt.timezone.utc):
        return None
    return t


def on_demand_ok(now: float | None = None) -> bool:
    """May a read ask for a sign-in now? Not within ON_DEMAND_PAUSE_S of the last attempt of any kind (the scheduled job's included), and
    not after ON_DEMAND_LIMIT on-demand attempts in 24 hours. Reads the attempts stamp only (times and kinds)."""
    now = now or time.time()
    try:
        raw = json.loads(ATTEMPTS_FILE.read_text())
    except FileNotFoundError:
        raw = []                                   # no attempt yet
    except (OSError, ValueError):
        return False                               # 12 Nov (N10): a stamp that cannot be read is not "no attempts"
    if not isinstance(raw, list):
        return False
    rows = [r for r in raw if isinstance(r, dict) and isinstance(r.get("t"), (int, float))]
    if rows and now - max(r["t"] for r in rows) < ON_DEMAND_PAUSE_S:
        return False
    return sum(1 for r in rows if r.get("kind") == "on_demand" and now - r["t"] < 24 * 3600) < ON_DEMAND_LIMIT


def try_auto_login(force: bool = False) -> bool:
    """Ask the agent service's sign-in module (src/india/kite_auth.py auto, in its own process and venv) for a fresh token.
    This module still never sees the password, the two-factor secret or the API secret: they stay in the other process.
    Returns True when a token is on disk afterwards; False when auto sign-in is off (no kite_login.env), it failed, or it is held back
    (12 Nov: on_demand_ok; no process is started then)."""
    import subprocess
    if not (AUTO_ENV.exists() and AGENT_PY.exists() and (AGENT_REPO / "src" / "india" / "kite_auth.py").exists()):
        return False
    if not on_demand_ok():
        return False
    try:
        args = [str(AGENT_PY), "-m", "src.india.kite_auth", "auto", "--on-demand"] + (["--force"] if force else [])
        subprocess.run(args, cwd=AGENT_REPO, capture_output=True, text=True, timeout=240)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return _read_token() is not None


def token() -> dict:
    t = _read_token()
    if t is None and try_auto_login():
        t = _read_token()
    if t is not None:
        return t
    if not TOKEN_FILE.exists():
        raise NeedLogin("no Kite token on disk: open http://127.0.0.1:8100/kite/login on the Mac")
    raise NeedLogin("the Kite token expired at 6 am IST: open http://127.0.0.1:8100/kite/login on the Mac")


def _trace(path: str, status: int, kind: str) -> None:
    """One line for a read Kite refused: when, the status, Kite's error type and the path. No token, no parameter, no message text."""
    try:
        REFUSALS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with REFUSALS_LOG.open("a") as f:
            f.write(f"{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')} {status} {kind or '-'} {path}\n")
    except OSError:
        pass


def _error_type(r) -> str:
    try:
        return str(r.json().get("error_type", ""))[:40].replace(" ", "_")
    except (ValueError, AttributeError):
        return ""


def _note_due(now: float | None = None) -> bool:
    """True at most once in NOTE_EVERY_S: every page and question behind a dead token used to send the phone the same note.
    12 Nov (N10): read and written under a lock, so two readers at the same moment send one note; and a stamp that cannot be written sends
    none, since without it there would be no limit (the scheduled sign-in's own failure note does not pass through here)."""
    import fcntl

    now = now or time.time()
    try:
        NOTE_STAMP.parent.mkdir(parents=True, exist_ok=True)
        with NOTE_STAMP.with_suffix(".lock").open("w") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)
            try:
                last = float(json.loads(NOTE_STAMP.read_text()).get("t", 0))
            except (OSError, ValueError, AttributeError, TypeError):
                last = 0.0                         # none yet, or broken: the note may go, and the stamp is written fresh
            if now - last < NOTE_EVERY_S:
                return False
            tmp = NOTE_STAMP.with_suffix(".tmp")
            tmp.write_text(json.dumps({"t": int(now)}))
            tmp.replace(NOTE_STAMP)
            return True
    except OSError:
        return False


def _ntfy(text: str) -> None:
    """Phone nudge through the same ntfy topic the Jarvis alerts use (read from the agent .env, names only)."""
    if os.environ.get("ANANTA_NTFY_TOPIC") == "":      # 12 Nov (audit G-57): set and empty means off (the tests' switch); it used to fall
        return                                         # through to the .env file and reach the real phone
    if not _note_due():
        return
    topic = os.getenv("ANANTA_NTFY_TOPIC")
    if not topic:
        env = Path(os.path.expanduser("~/code/ananta-decision-agent/.env"))
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("ANANTA_NTFY_TOPIC="):
                    topic = line.split("=", 1)[1].strip().strip('"')
    if topic:
        try:
            requests.post(f"https://ntfy.sh/{topic}", data=text.encode(), headers={"Title": "Ananta: Kite"}, timeout=10)
        except requests.RequestException:
            pass


class Kite:
    def __init__(self, rate_per_s: float = 3.0):
        t = token()
        self.user_id = t.get("user_id", "")
        self.s = requests.Session()
        self.s.headers.update({"X-Kite-Version": "3", "Authorization": f"token {t['api_key']}:{t['access_token']}"})
        self.gap = 1.0 / rate_per_s
        self._last = 0.0
        self.calls = 0

    def get(self, path: str, params: dict | None = None, raw: bool = False):
        wait = self.gap - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        r = None
        for k in range(5):
            try:
                r = self.s.get(BASE + path, params=params, timeout=40)
            except requests.RequestException:          # a timeout or a dropped connection: wait and ask again
                self._last = time.time()
                self.calls += 1
                time.sleep(3 * (k + 1))
                continue
            self._last = time.time()
            self.calls += 1
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 * (k + 1))
                continue
            break
        if r is None:
            _trace(path, 0, "NoAnswer")
            raise RuntimeError(f"Kite did not answer {path} after 5 tries")
        if r.status_code >= 400 and _error_type(r) != "TokenException":      # a dead token has its own path below (the phone note, NeedLogin)
            _trace(path, r.status_code, _error_type(r))
        if r.status_code == 403:
            try:
                err = r.json().get("error_type", "")
            except ValueError:
                err = ""
            if err == "TokenException":
                # The stored token looks alive but Kite rejects it (a sign-in elsewhere, a logout): one forced auto sign-in, then one retry.
                if not getattr(self, "_relogged", False) and try_auto_login(force=True):
                    self._relogged = True
                    t = token()
                    self.s.headers.update({"Authorization": f"token {t['api_key']}:{t['access_token']}"})
                    return self.get(path, params, raw)
                _ntfy("Kite login needed: open http://127.0.0.1:8100/kite/login on the Mac")
                raise NeedLogin("Kite token rejected (TokenException): sign in again")
        r.raise_for_status()
        return r.text if raw else r.json()["data"]

    def post_calc(self, path: str, body: list, params: dict | None = None):
        """Kite's margin calculator (CALC_POSTS only): a calculation, never an order."""
        if path not in CALC_POSTS:
            raise PermissionError(f"POST refused: {path} is not a calculation endpoint on the allowed list {CALC_POSTS}")
        wait = self.gap - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        r = self.s.post(BASE + path, params=params, json=body, timeout=40)
        self._last = time.time()
        self.calls += 1
        if r.status_code >= 400 and _error_type(r) != "TokenException":
            _trace(path, r.status_code, _error_type(r))
        if r.status_code == 403:
            raise NeedLogin("Kite token rejected: sign in again")
        r.raise_for_status()
        return r.json()["data"]

    def basket_margin(self, orders: list[dict]) -> dict:
        """Margin Kite would block for a basket (spread benefit included in 'final'); nothing is placed."""
        return self.post_calc("/margins/basket", orders, params={"consider_positions": "false", "mode": "compact"})

    # ---- data ----
    def instruments(self, exchange: str | None = None) -> str:
        """The instruments master as CSV text (one copy a day goes to bronze/kite_instruments)."""
        return self.get("/instruments" + (f"/{exchange}" if exchange else ""), raw=True)

    def historical(self, instrument_token: int, interval: str, start: dt.date, end: dt.date) -> list[list]:
        """Candles [time, open, high, low, close, volume] for one window; the caller keeps windows within DAYS_PER_REQUEST."""
        return self.get(f"/instruments/historical/{instrument_token}/{interval}",
                        {"from": f"{start} 09:00:00", "to": f"{end} 15:45:00"})["candles"]

    def historical_all(self, instrument_token: int, interval: str, start: dt.date, end: dt.date) -> list[list]:
        """Every candle between start and end, in windows the API allows."""
        step = dt.timedelta(days=DAYS_PER_REQUEST[interval] - 1)
        out: list[list] = []
        a = start
        while a <= end:
            b = min(a + step, end)
            out.extend(self.historical(instrument_token, interval, a, b))
            a = b + dt.timedelta(days=1)
        return out

    # ---- the ledger (read-only) ----
    def holdings(self) -> list[dict]:
        return self.get("/portfolio/holdings")

    def positions(self) -> dict:
        return self.get("/portfolio/positions")

    def margins(self) -> dict:
        return self.get("/user/margins")

    def orders(self) -> list[dict]:
        return self.get("/orders")

    def trades(self) -> list[dict]:
        return self.get("/trades")
