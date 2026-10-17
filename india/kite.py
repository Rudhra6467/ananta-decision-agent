"""Kite Connect, read side only: candles, instruments, and the owner's holdings, positions and funds.

The token comes from ~/ananta_private/kite_token.json, written by the Jarvis service when Madhav signs in at
http://127.0.0.1:8100/kite/login (src/india/kite_auth.py in the agent repo). This module never logs in, never sees
the password or the API secret, and has no method that places, changes or cancels an order: it sends GET only.
Limits (Kite forum, staff, 2018; the probe confirms): 3 requests a second; per request, minute 30 days, 5minute 90 days,
15minute 180 days, 60minute 365 days, day 2000 days. The token expires at 6 am IST; a 403 TokenException raises NeedLogin
and, when the ntfy topic is configured, sends the phone "Kite login needed".
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
DAYS_PER_REQUEST = {"minute": 30, "3minute": 90, "5minute": 90, "10minute": 90, "15minute": 180, "30minute": 180, "60minute": 365, "day": 2000}


class NeedLogin(RuntimeError):
    pass


def token() -> dict:
    if not TOKEN_FILE.exists():
        raise NeedLogin("no Kite token on disk: open http://127.0.0.1:8100/kite/login on the Mac")
    t = json.loads(TOKEN_FILE.read_text())
    if t.get("expires_at") and dt.datetime.fromisoformat(t["expires_at"]) <= dt.datetime.now(dt.timezone.utc):
        raise NeedLogin("the Kite token expired at 6 am IST: open http://127.0.0.1:8100/kite/login on the Mac")
    return t


def _ntfy(text: str) -> None:
    """Phone nudge through the same ntfy topic the Jarvis alerts use (read from the agent .env, names only)."""
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
        for k in range(4):
            r = self.s.get(BASE + path, params=params, timeout=40)
            self._last = time.time()
            self.calls += 1
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(2 * (k + 1))
                continue
            break
        if r.status_code == 403:
            try:
                err = r.json().get("error_type", "")
            except ValueError:
                err = ""
            if err == "TokenException":
                _ntfy("Kite login needed: open http://127.0.0.1:8100/kite/login on the Mac")
                raise NeedLogin("Kite token rejected (TokenException): sign in again")
        r.raise_for_status()
        return r.text if raw else r.json()["data"]

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
