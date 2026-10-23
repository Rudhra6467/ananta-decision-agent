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


# ---------------------------------------------------------------------------------------------------------------------
# Automatic sign-in (Madhav, 22 Oct 2026: "is there any way to automate the login process, as it will be more reliable").
#
# Zerodha offers no official headless login. This uses the two calls the Kite web page itself makes (kite.zerodha.com
# /api/login and /api/twofa, the second with a TOTP code generated from the account's external-2FA secret), then follows the
# Kite Connect redirect to pick up the request_token and swaps it exactly as the manual path does (exchange()). It is the
# community method (kite.trade forum "Autoconnect now working", 2023; still used by kite-mcp 0.1 in March 2026). Zerodha may
# change the page at any time, so the manual route stays, and every failure sends the phone the same "open /kite/login" note.
#
# It reads ~/ananta_private/kite_login.env, written once by Madhav (chmod 600):
#     KITE_USER_ID=...       the Zerodha client id of the account Ananta watches (must equal the pinned owner)
#     KITE_PASSWORD=...
#     KITE_TOTP_SECRET=...   the base32 key shown under "Can't scan? Copy key" when External 2FA TOTP is enabled on Console
# Nothing here prints, logs or stores any of those values or the tokens. The log (~/ananta_runs/kite_autologin.log) holds
# only times, the user id and the reason a step was refused.
# ---------------------------------------------------------------------------------------------------------------------
LOGIN_ENV = PRIVATE / "kite_login.env"
LOCK_FILE = PRIVATE / "kite_autologin.lock"
LOG_FILE = Path(os.path.expanduser("~/ananta_runs/kite_autologin.log"))
KITE_WEB = "https://kite.zerodha.com"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def login_creds() -> dict:
    if not LOGIN_ENV.exists():
        raise RuntimeError("no ~/ananta_private/kite_login.env (KITE_USER_ID, KITE_PASSWORD, KITE_TOTP_SECRET): auto sign-in is off")
    kv: dict[str, str] = {}
    for line in LOGIN_ENV.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip().strip('"').strip("'")
    missing = [k for k in ("KITE_USER_ID", "KITE_PASSWORD", "KITE_TOTP_SECRET") if not kv.get(k)]
    if missing:
        raise RuntimeError(f"kite_login.env is missing {', '.join(missing)}")
    kv["KITE_TOTP_SECRET"] = totp_secret(kv["KITE_TOTP_SECRET"])
    return kv


def totp_secret(raw: str) -> str:
    """Normalise the pasted TOTP key: accept an otpauth:// URL, spaces, dashes and lower case; refuse the 6-digit code
    people paste by mistake, with a reason that says what to paste instead (never echoes the value)."""
    import base64
    import re
    from urllib.parse import parse_qs, urlparse

    v = raw.strip()
    if v.lower().startswith("otpauth://"):
        q = parse_qs(urlparse(v).query)
        v = (q.get("secret") or [""])[0]
    v = re.sub(r"[\s\-_]", "", v).upper().rstrip("=")
    if re.fullmatch(r"\d{6,8}", v):
        raise RuntimeError("KITE_TOTP_SECRET is a 6-digit code, not the key: on Console > Password & Security > External 2FA TOTP, "
                           "set TOTP up again and copy the long key under the QR code ('Can't scan? Copy the key')")
    bad = sorted(set(v) - set("ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"))
    if bad or len(v) < 16:
        raise RuntimeError("KITE_TOTP_SECRET is not a base32 key (it should be 16-64 letters A-Z and digits 2-7): "
                           "copy the key shown under the QR code when External 2FA TOTP is set up on Console")
    try:
        base64.b32decode(v + "=" * (-len(v) % 8))
    except (ValueError, TypeError) as e:
        raise RuntimeError(f"KITE_TOTP_SECRET does not decode as base32: {e}") from None
    return v


def _log(line: str) -> None:
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a") as f:
            f.write(f"{dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')} {line}\n")
    except OSError:
        pass


def _ntfy(text: str) -> None:
    """Phone nudge through the same ntfy topic the Jarvis alerts use (name read from the agent .env; never a secret)."""
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


def _json(r: requests.Response) -> dict:
    try:
        return r.json()
    except ValueError:
        return {"status": "error", "message": f"HTTP {r.status_code}, not JSON"}


def _request_token_from_redirects(s: requests.Session, url: str, hops: int = 8) -> str:
    """Follow the Kite Connect redirect chain by hand until a URL carries request_token (the owner's callback is never
    actually opened, so the Jarvis service need not be running)."""
    from urllib.parse import parse_qs, urljoin, urlparse
    last = 0
    for _ in range(hops):
        r = s.get(url, allow_redirects=False, timeout=30)
        last = r.status_code
        loc = r.headers.get("Location", "")
        for candidate in (loc, r.url):
            q = parse_qs(urlparse(candidate).query)
            if q.get("request_token"):
                return q["request_token"][0]
        if r.status_code in (301, 302, 303, 307, 308) and loc:
            url = urljoin(url, loc)
            continue
        break
    raise RuntimeError(f"no request_token in the Kite redirect chain (last status {last}); the Kite Connect app's redirect URL or the session may have changed")


def auto(force: bool = False, min_left: int = 1800) -> dict:
    """Sign in with no browser. Skipped when the stored token still has more than min_left seconds, unless force.
    Returns status() plus an 'auto' line; raises RuntimeError with the reason when a step is refused."""
    import fcntl
    import time

    import pyotp

    st = status()
    if st["connected"] and st["seconds_left"] > min_left and not force:
        return {**st, "auto": "skipped: token still valid"}
    c = login_creds()
    pinned = pinned_user()
    if pinned and c["KITE_USER_ID"] != pinned:
        raise RuntimeError("the user id in kite_login.env is not the pinned owner; refused")
    PRIVATE.mkdir(exist_ok=True)
    with LOCK_FILE.open("w") as lk:
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {**status(), "auto": "another sign-in is running"}
        st = status()
        if st["connected"] and st["seconds_left"] > min_left and not force:
            return {**st, "auto": "skipped: token already refreshed"}
        key, _ = creds()
        connect_url = f"{KITE_WEB}/connect/login?v=3&api_key={key}"
        s = requests.Session()
        s.headers.update({"User-Agent": UA})
        s.get(connect_url, timeout=30)   # opens the Kite Connect session (sess_id) the way the browser would
        r = s.post(f"{KITE_WEB}/api/login", data={"user_id": c["KITE_USER_ID"], "password": c["KITE_PASSWORD"]}, timeout=30)
        j = _json(r)
        if j.get("status") != "success":
            raise RuntimeError(f"password step refused: {str(j.get('message', '?'))[:140]}")
        request_id = j["data"]["request_id"]
        refused = ""
        for attempt in range(2):
            code = pyotp.TOTP(c["KITE_TOTP_SECRET"]).now()
            r2 = s.post(f"{KITE_WEB}/api/twofa", data={"user_id": c["KITE_USER_ID"], "request_id": request_id, "twofa_value": code,
                                                      "twofa_type": "totp", "skip_session": "true"}, timeout=30)
            j2 = _json(r2)
            if j2.get("status") == "success":
                break
            refused = str(j2.get("message", "?"))[:140]
            if attempt == 0:
                time.sleep(31)   # a fresh 30-second code, in case the first fell on the boundary
        else:
            raise RuntimeError(f"two-factor step refused: {refused}")
        request_token = _request_token_from_redirects(s, connect_url + "&skip_session=true")
        out = exchange(request_token)
        _log(f"auto sign-in ok: user {out.get('user_id')} until {out.get('expires_at_ist')}")
        return {**out, "auto": "signed in"}


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(json.dumps(status()))
    elif cmd == "auto":
        if not LOGIN_ENV.exists():
            print(json.dumps({"ok": False, "why": "auto sign-in is off: no ~/ananta_private/kite_login.env"}))
            sys.exit(2)
        try:
            out = auto(force="--force" in sys.argv)
            print(json.dumps(out))
        except Exception as e:   # noqa: BLE001 - every reason goes to the log and the phone, never a secret
            why = str(e)[:300]
            _log(f"auto sign-in FAILED: {why}")
            _ntfy(f"Kite auto sign-in failed: {why}. Sign in by hand before 23:40 Toronto (09:10 IST) or the next NSE session is lost: open http://127.0.0.1:8100/kite/login on the Mac.")
            print(json.dumps({"ok": False, "why": why}))
            sys.exit(1)
    else:
        print("usage: python -m src.india.kite_auth [status|auto [--force]]")
        sys.exit(64)
