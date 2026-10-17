"""Kite Connect sign-in for the owner, done by the Jarvis service on the Mac (plan of 16 Oct 2026, section 5).

Madhav opens http://127.0.0.1:8100/kite/login, Zerodha shows its own login page (password and two-factor code typed by him,
never seen here), and sends the browser back to /kite/callback with a request_token. This module swaps that token for the
day's access_token (checksum = sha256(api_key + request_token + api_secret)) and writes ~/ananta_private/kite_token.json,
which the India data jobs read. The token dies at 6 am IST (Kite docs: regulatory requirement), so this repeats daily.
The API key and secret live in ~/ananta_private/kite.env (KITE_API_KEY, KITE_API_SECRET); nothing here prints either.
The first login pins the Zerodha user id: a later login by a different user is refused, so a stray visitor can never
connect their account to Ananta.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

PRIVATE = Path(os.path.expanduser("~/ananta_private"))
ENV_FILE = PRIVATE / "kite.env"
TOKEN_FILE = PRIVATE / "kite_token.json"
IST = ZoneInfo("Asia/Kolkata")


def creds() -> tuple[str, str]:
    if not ENV_FILE.exists():
        raise RuntimeError("~/ananta_private/kite.env is missing (KITE_API_KEY and KITE_API_SECRET)")
    kv: dict[str, str] = {}
    for line in ENV_FILE.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip().strip('"').strip("'")
    key, secret = kv.get("KITE_API_KEY", ""), kv.get("KITE_API_SECRET", "")
    if not key or not secret:
        raise RuntimeError("kite.env needs KITE_API_KEY and KITE_API_SECRET")
    return key, secret


def login_url() -> str:
    key, _ = creds()
    return f"https://kite.zerodha.com/connect/login?v=3&api_key={key}"


def expires_at(login_time: dt.datetime) -> dt.datetime:
    """The next 6:00 am IST after the login."""
    local = login_time.astimezone(IST)
    six = local.replace(hour=6, minute=0, second=0, microsecond=0)
    if local >= six:
        six += dt.timedelta(days=1)
    return six.astimezone(dt.timezone.utc)


def pinned_user() -> str:
    if TOKEN_FILE.exists():
        try:
            return json.loads(TOKEN_FILE.read_text()).get("user_id", "")
        except ValueError:
            return ""
    return ""


def exchange(request_token: str) -> dict:
    """Swap the request_token for today's access_token and store it. Returns what is safe to show (no token)."""
    key, secret = creds()
    checksum = hashlib.sha256((key + request_token + secret).encode()).hexdigest()
    r = requests.post("https://api.kite.trade/session/token", data={"api_key": key, "request_token": request_token, "checksum": checksum},
                      headers={"X-Kite-Version": "3"}, timeout=30)
    if r.status_code != 200:
        try:
            msg = r.json().get("message", r.text[:200])
        except ValueError:
            msg = r.text[:200]
        raise RuntimeError(f"Kite refused the token exchange ({r.status_code}): {msg}")
    data = r.json()["data"]
    user_id = data.get("user_id", "")
    pinned = pinned_user()
    if pinned and user_id != pinned:
        raise RuntimeError("this Zerodha login is not the owner's account; nothing was stored")
    now = dt.datetime.now(dt.timezone.utc)
    rec = {"api_key": key, "access_token": data["access_token"], "user_id": user_id, "user_name": data.get("user_name", ""),
           "login_time": now.isoformat(timespec="seconds"), "expires_at": expires_at(now).isoformat(timespec="seconds")}
    PRIVATE.mkdir(exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(rec))
    os.chmod(TOKEN_FILE, 0o600)
    return status()


def status() -> dict:
    """Connected or not, and until when (IST), for the app and for Ask Ananta. Never includes the token."""
    if not TOKEN_FILE.exists():
        return {"connected": False, "why": "not signed in yet"}
    t = json.loads(TOKEN_FILE.read_text())
    exp = dt.datetime.fromisoformat(t["expires_at"])
    now = dt.datetime.now(dt.timezone.utc)
    left = int((exp - now).total_seconds())
    return {"connected": left > 0, "user_id": t.get("user_id", ""), "user_name": t.get("user_name", ""),
            "login_time": t.get("login_time"), "expires_at_ist": exp.astimezone(IST).strftime("%Y-%m-%d %H:%M IST"),
            "seconds_left": max(left, 0), "why": "" if left > 0 else "the token expired at 6 am IST; sign in again"}
