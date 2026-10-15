"""Jarvis service core: the owner-only view of the Agent, and the few actions the owner can take.

Plain Python (tested without a web framework). `app.py` puts it on HTTP.

Reads the Agent's own files in AGENT_DIR (the ananta-decision-agent folder):
  explorer_state.pkl / explorer_book.sqlite   live Explorer (paper trades, sightings)
  portfolio_book.sqlite                       portfolio manager (ratings, proposals, books)
  watch_alerts.jsonl, explorer_daily/, explorer_weekly/, breaker_state.json, docs/variable_registry.json
Actions (each written to the audit log): approve / reject proposals, change portfolio mode, kill switch on / off,
register a phone for push. Paper only: nothing here can place a real order.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

VERSION = "jarvis.service.v0.3"
TOKEN_TTL_S = 12 * 3600
MAX_FAILED, FAIL_WINDOW_S = 5, 15 * 60
# Madhav, Oct 12: every sign-in ends after 3 hours without use (quiet background refreshes do not count as use), and every
# visitor account created from Oct 12 lasts 3 days; after that, signing in shows a short feedback form instead of the app.
IDLE_S = int(os.getenv("JARVIS_IDLE_S", str(3 * 3600)))
GUEST_DAYS = float(os.getenv("JARVIS_GUEST_DAYS", "3"))
TOUCH_EVERY_S = 60
FEEDBACK_QUESTIONS = [
    {"id": "used_for", "q": "What did you use Ananta for in these 3 days?", "kind": "text", "required": True},
    {"id": "easy", "q": "How easy was Ananta to use?", "kind": "scale", "low": "Hard", "high": "Very easy", "required": True},
    {"id": "clear", "q": "Did Ananta's answers and explanations make sense to you?", "kind": "scale", "low": "Not at all", "high": "Completely",
     "required": True},
    {"id": "best", "q": "What was the most useful thing Ananta did for you?", "kind": "text"},
    {"id": "worst", "q": "What confused you, felt wrong, or did not work?", "kind": "text"},
    {"id": "trust", "q": "Would you trust Ananta's reasons for a trade? Why or why not?", "kind": "text"},
    {"id": "again", "q": "Would you keep using Ananta if you could?", "kind": "choice", "options": ["Yes", "Maybe", "No"], "required": True},
    {"id": "else", "q": "Anything else you want Madhav to know?", "kind": "text"},
]


class AccountExpired(Exception):
    """A visitor's practice days are over: signing in gives a feedback form instead of the app."""

    def __init__(self, email: str, name: str, form_token: str | None, answered: bool):
        super().__init__("your practice days are over")
        self.email, self.name, self.form_token, self.answered = email, name, form_token, answered


class _Rows:
    """A fully-read result (so the lock is never held while the caller iterates)."""

    def __init__(self, rows: list, lastrowid=None, rowcount: int = -1):
        self._rows, self.lastrowid, self.rowcount = rows, lastrowid, rowcount

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)

    def __iter__(self):
        return iter(self._rows)


class SafeDB:
    """One SQLite connection shared by the web threads, the 15-minute background job and Ask: every call is serialized.
    (sqlite3 connections are not safe to use from two threads at the same moment: found by the stability tests.)"""

    def __init__(self, con: sqlite3.Connection):
        import threading

        self.con, self.lock = con, threading.RLock()

    def execute(self, sql: str, params=()):
        with self.lock:
            cur = self.con.execute(sql, params)
            return _Rows(cur.fetchall(), cur.lastrowid, cur.rowcount)

    def executemany(self, sql: str, seq):
        with self.lock:
            self.con.executemany(sql, seq)

    def executescript(self, sql: str):
        with self.lock:
            self.con.executescript(sql)

    def commit(self):
        with self.lock:
            self.con.commit()


class AuthError(Exception):
    pass


class ConfirmRequired(Exception):
    pass


def docs_dir(base) -> Path:
    """Ananta's knowledge documents. They ship with this service's code (the jarvis branch checkout), which is newer than the
    agent folder's copy until a merge is pulled there; fall back to the agent folder's docs."""
    own = Path(__file__).resolve().parents[2] / "docs"
    return own if (own / "KNOWLEDGE_INDEX.md").exists() else Path(base) / "docs"


def _utc(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ---------------------------------------------------------------------------
# passwords (scrypt, standard library) and tokens (HMAC-signed, standard library)
# ---------------------------------------------------------------------------
def hash_password(pw: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    # ':' separators (not '$'), so a shell loading the .env file cannot mangle the value
    return "scrypt:" + base64.b64encode(salt).decode() + ":" + base64.b64encode(h).decode()


def verify_password(pw: str, stored: str) -> bool:
    try:
        kind, s, h = stored.replace("$", ":").split(":")
        if kind != "scrypt":
            return False
        cand = hashlib.scrypt(pw.encode(), salt=base64.b64decode(s), n=2 ** 14, r=8, p=1, dklen=32)
        return hmac.compare_digest(cand, base64.b64decode(h))
    except Exception:  # noqa: BLE001
        return False


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_token(secret: str, sub: str, now: float, ttl: int = TOKEN_TTL_S, **extra: Any) -> str:
    """extra claims: sid (the sign-in session, required for the app's tokens) or svc=1 (a script on this Mac, no session)."""
    body = _b64(json.dumps({"sub": sub, "exp": int(now + ttl), "iat": int(now), **extra}).encode())
    sig = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def read_token(secret: str, token: str, now: float) -> dict:
    try:
        body, sig = token.split(".")
    except ValueError as exc:
        raise AuthError("bad token") from exc
    good = _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(good, sig):
        raise AuthError("bad token")
    p = json.loads(_unb64(body))
    if p.get("exp", 0) < now:
        raise AuthError("token expired")
    return p


def gmail_key(email: str) -> str:
    """Gmail ignores dots and anything after + in the name part; so do we when matching a sign-in."""
    e = (email or "").strip().lower()
    name, _, dom = e.partition("@")
    if dom in ("gmail.com", "googlemail.com"):
        return name.split("+")[0].replace(".", "") + "@gmail.com"
    return e


# ---------------------------------------------------------------------------
class Jarvis:
    def __init__(self, agent_dir: Path | str, *, owner_email: str, password_hash: str, secret: str,
                 hands: Any = None, now: Callable[[], float] = time.time, db_file: str = "jarvis.sqlite"):
        if not (owner_email and password_hash and secret and len(secret) >= 32):
            raise ValueError("owner email, password hash and a secret of at least 32 characters are required")
        self.dir = Path(agent_dir)
        self.owner, self.pw_hash, self.secret = owner_email.strip().lower(), password_hash, secret
        self.now = now
        self._hands = hands
        # db_file: the owner's jarvis.sqlite, or a guest's own practice copy (jarvis_guest_<name>.sqlite): a guest's questions,
        # paper orders, alerts and mandate edits live there and never touch the owner's books.
        self.sandbox = db_file != "jarvis.sqlite"
        self.db = SafeDB(sqlite3.connect(str(self.dir / db_file), check_same_thread=False, timeout=30))
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY AUTOINCREMENT, t INTEGER, who TEXT, action TEXT, detail TEXT, result TEXT);
            CREATE TABLE IF NOT EXISTS failed_logins (t INTEGER);
            CREATE TABLE IF NOT EXISTS push_tokens (token TEXT PRIMARY KEY, device TEXT, t INTEGER);
            CREATE TABLE IF NOT EXISTS snapshots (t INTEGER PRIMARY KEY, explorer REAL, main REAL, shadow REAL, btc REAL);
        """)

    # -- auth --
    # Accounts (Madhav, 2026-10-06): one main account (the owner: email, name and password in the .env) and visitor accounts
    # he invites. An invite is a one-time link (livetrading247.com/join?code=...): the visitor picks their own name and
    # password, and starts in their own empty practice book. The owner lists and removes visitors in the app (People).
    # Accounts live in the owner's database; a sandbox (a visitor's copy) points users_db at it.
    def _auth_tables(self) -> None:
        d = self.users_db
        if getattr(self, "_auth_done", None) is d:                  # once per database (check() runs on every request)
            return
        d.executescript("""
            CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, name TEXT, pw_hash TEXT, created_t INTEGER, invite TEXT);
            CREATE TABLE IF NOT EXISTS invites (code TEXT PRIMARY KEY, name TEXT, email TEXT, created_t INTEGER, expires_t INTEGER,
                                                used_t INTEGER, used_by TEXT);
        """)
        if "email" not in [c[1] for c in d.execute("PRAGMA table_info(failed_logins)")]:
            d.execute("ALTER TABLE failed_logins ADD COLUMN email TEXT")
        if "expires_t" not in [c[1] for c in d.execute("PRAGMA table_info(users)")]:
            d.execute("ALTER TABLE users ADD COLUMN expires_t INTEGER")          # NULL: no end (accounts made before Oct 12)
        d.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (sid TEXT PRIMARY KEY, sub TEXT, created_t INTEGER, last_t INTEGER);
            CREATE TABLE IF NOT EXISTS owner_auth (k TEXT PRIMARY KEY, v TEXT);
            CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, name TEXT, t INTEGER, answers TEXT);
        """)
        d.commit()
        self._auth_done = d

    # -- sign-in sessions (Oct 12): a token carries a session id; 3 hours without use ends the session --
    def _session(self, sub: str, ttl: int) -> str:
        now = int(self.now())
        sid = secrets.token_urlsafe(16)
        self.users_db.execute("DELETE FROM sessions WHERE last_t < ?", (now - IDLE_S,))
        self.users_db.execute("INSERT INTO sessions VALUES (?,?,?,?)", (sid, sub, now, now))
        self.users_db.commit()
        return make_token(self.secret, sub, now, ttl=ttl, sid=sid)

    def logout(self, token: str) -> bool:
        try:
            p = read_token(self.secret, token or "", self.now())
        except AuthError:
            return False
        self._auth_tables()
        n = self.users_db.execute("DELETE FROM sessions WHERE sid = ?", (str(p.get("sid") or ""),)).rowcount
        self.users_db.commit()
        return bool(n)

    def _owner_hash(self) -> str:
        """The owner's password: the one changed in the app (Cockpit › Additional features) wins over the .env value."""
        try:
            r = self.users_db.execute("SELECT v FROM owner_auth WHERE k = 'pw_hash'").fetchone()
        except Exception:  # noqa: BLE001  the table appears with the first sign-in
            r = None
        return r[0] if r and r[0] else self.pw_hash

    def change_password(self, current: str, new: str, keep_token: str = "") -> dict:
        """Owner only (app.py checks): the current password, then a new one of at least 10 characters. Every other signed-in
        device is signed out."""
        self._auth_tables()
        now = int(self.now())
        if self._locked(self.owner, now):
            raise AuthError("too many wrong passwords; wait 15 minutes")
        if not verify_password(current or "", self._owner_hash()):
            self.users_db.execute("INSERT INTO failed_logins (t, email) VALUES (?,?)", (now, self.owner))
            self.users_db.commit()
            self.audit(self.owner, "password.change", "", "WRONG_CURRENT")
            raise ValueError("the current password is not right")
        new = new or ""
        if len(new) < 10:
            raise ValueError("the new password needs at least 10 characters")
        if new == current:
            raise ValueError("the new password is the same as the current one")
        self.users_db.execute("INSERT OR REPLACE INTO owner_auth VALUES ('pw_hash', ?)", (hash_password(new),))
        self.users_db.execute("INSERT OR REPLACE INTO owner_auth VALUES ('changed_t', ?)", (str(now),))
        keep = ""
        try:
            keep = str(read_token(self.secret, keep_token, now).get("sid") or "")
        except AuthError:
            pass
        n = self.users_db.execute("DELETE FROM sessions WHERE sub = ? AND sid != ?", (self.owner, keep)).rowcount
        self.users_db.commit()
        self.audit(self.owner, "password.change", f"{n} other sign-ins ended", "OK")
        return {"ok": True, "signed_out_elsewhere": n, "changed_t": now}

    # -- visitor feedback (Oct 12) --
    def _expired(self, em: str) -> bool:
        r = self.users_db.execute("SELECT expires_t FROM users WHERE email = ?", (em,)).fetchone()
        return bool(r and r[0] and r[0] <= self.now())

    def submit_feedback(self, form_token: str, answers: dict) -> dict:
        p = read_token(self.secret, form_token or "", self.now())
        sub = str(p.get("sub") or "")
        if not sub.startswith("feedback:"):
            raise AuthError("this form link is not valid; sign in again")
        self._auth_tables()
        em = sub[9:]
        if self.users_db.execute("SELECT 1 FROM feedback WHERE email = ?", (em,)).fetchone():
            return {"ok": True, "already": True}
        ids = {q["id"]: q for q in FEEDBACK_QUESTIONS}
        clean = {k: str(v).strip()[:2000] for k, v in (answers or {}).items() if k in ids and str(v or "").strip()}
        missing = [ids[k]["q"] for k in ids if ids[k].get("required") and k not in clean]
        if missing:
            raise ValueError("please answer: " + missing[0])
        self.users_db.execute("INSERT INTO feedback (email, name, t, answers) VALUES (?,?,?,?)",
                              (em, self.name_of("guest:" + em), int(self.now()), json.dumps(clean, ensure_ascii=False)))
        self.users_db.commit()
        self.audit("guest:" + em, "feedback", f"{len(clean)} answers", "OK")
        return {"ok": True}

    def feedback(self) -> dict:
        self._auth_tables()
        rows = [{"id": i, "email": e, "name": n, "t": t, "answers": json.loads(a or "{}")} for i, e, n, t, a in
                self.users_db.execute("SELECT id, email, name, t, answers FROM feedback ORDER BY t DESC")]
        return {"questions": FEEDBACK_QUESTIONS, "responses": rows}

    def extend(self, email: str, days: float = GUEST_DAYS) -> dict:
        """Owner only: give a visitor more days from now."""
        self._auth_tables()
        em = (email or "").strip().lower()
        until = int(self.now() + float(days) * 86400)
        n = self.users_db.execute("UPDATE users SET expires_t = ? WHERE email = ?", (until, em)).rowcount
        self.users_db.commit()
        self.audit(self.owner, "people.extend", f"{em} {days}d", "OK" if n else "NONE")
        if not n:
            raise ValueError("no such visitor")
        return {"email": em, "expires_t": until}

    @property
    def users_db(self):
        return getattr(self, "_users_db", None) or self.db

    @users_db.setter
    def users_db(self, db) -> None:
        self._users_db = db

    @property
    def owner_name(self) -> str:
        return os.getenv("JARVIS_OWNER_NAME", "").strip() or "Madhav"

    def _fail(self, em: str, now: float, why: str = "wrong email or password") -> None:
        self.users_db.execute("INSERT INTO failed_logins (t, email) VALUES (?,?)", (int(now), em))
        self.users_db.commit()
        self.audit("?", "login", em, "FAILED")
        raise AuthError(why)

    def _locked(self, em: str, now: float) -> bool:
        """Per account: 5 wrong passwords on one email lock that email for 15 minutes (a visitor's typos never lock the owner
        out); 30 wrong tries across all emails lock everything (someone guessing)."""
        since = int(now - FAIL_WINDOW_S)
        mine = self.users_db.execute("SELECT count(*) FROM failed_logins WHERE t > ? AND email = ?", (since, em)).fetchone()[0]
        every = self.users_db.execute("SELECT count(*) FROM failed_logins WHERE t > ?", (since,)).fetchone()[0]
        return mine >= MAX_FAILED or every >= 6 * MAX_FAILED

    def _resolve(self, typed: str) -> str:
        """Who is signing in (build plan 1.9: 25 failed sign-ins in 3 days were names typed instead of emails, or Gmail dots):
        an email as typed, the same Gmail address with or without dots, or an account's name."""
        t = (typed or "").strip().lower()
        accounts = [self.owner] + [e for (e,) in self.users_db.execute("SELECT email FROM users").fetchall()]
        if "@" in t:
            if t in accounts:
                return t
            return next((a for a in accounts if gmail_key(a) == gmail_key(t)), t)
        names = {(self.owner_name or "").strip().lower(): self.owner}
        for e, n in self.users_db.execute("SELECT email, name FROM users").fetchall():
            names.setdefault((n or "").strip().lower(), e)
        return names.get(" ".join(t.split()), t)

    def login(self, email: str, password: str) -> str:
        self._auth_tables()
        now = self.now()
        em = self._resolve(email)
        if self._locked(em, now):
            self.audit("?", "login", em, "LOCKED")
            raise AuthError("too many wrong passwords for this account; wait 15 minutes")
        if em == self.owner:
            if not verify_password(password or "", self._owner_hash()):
                self._fail(em, now)
            self.users_db.execute("DELETE FROM failed_logins WHERE email = ?", (em,))
            self.users_db.commit()
            self.audit(self.owner, "login", "", "OK")
            return self._session(self.owner, TOKEN_TTL_S)
        row = self.users_db.execute("SELECT pw_hash FROM users WHERE email = ?", (em,)).fetchone()
        if not row or not verify_password(password or "", row[0]):
            self._fail(em, now, "wrong email or password (sign in with the email you joined with, or your name)")
        self.users_db.execute("DELETE FROM failed_logins WHERE email = ?", (em,))
        self.users_db.commit()
        if self._expired(em):                                       # the practice days are over: the feedback form, not the app
            answered = bool(self.users_db.execute("SELECT 1 FROM feedback WHERE email = ?", (em,)).fetchone())
            self.audit("guest:" + em, "login", "", "EXPIRED")
            raise AccountExpired(em, self.name_of("guest:" + em), None if answered else
                                 make_token(self.secret, "feedback:" + em, now, ttl=86400), answered)
        self.audit("guest:" + em, "login", "", "OK")
        return self._session("guest:" + em, 7 * 86400)

    def check(self, token: str, touch: bool = False) -> str:
        """Who a token belongs to. touch=True (a request the person made, not a quiet background refresh) counts as use."""
        now = self.now()
        p = read_token(self.secret, token or "", now)
        sub = str(p.get("sub") or "")
        if p.get("svc") and sub == self.owner:                       # a script on this Mac (the evals), signed with the secret
            return sub
        if not (sub == self.owner or sub.startswith("guest:")):
            raise AuthError("not signed in")
        self._auth_tables()
        if sub.startswith("guest:"):
            if not self.users_db.execute("SELECT 1 FROM users WHERE email = ?", (sub[6:],)).fetchone():
                raise AuthError("this account was removed")
            if self._expired(sub[6:]):
                raise AuthError("your practice days are over; sign in to share your feedback")
        sid = str(p.get("sid") or "")
        row = self.users_db.execute("SELECT sub, last_t FROM sessions WHERE sid = ?", (sid,)).fetchone() if sid else None
        if not row or row[0] != sub:
            raise AuthError("signed out; please sign in again")
        if now - row[1] > IDLE_S:
            self.users_db.execute("DELETE FROM sessions WHERE sid = ?", (sid,))
            self.users_db.commit()
            raise AuthError(f"signed out after {IDLE_S // 3600} hours without use; please sign in again")
        if touch and now - row[1] >= TOUCH_EVERY_S:
            self.users_db.execute("UPDATE sessions SET last_t = ? WHERE sid = ?", (int(now), sid))
            self.users_db.commit()
        return sub

    def name_of(self, who: str) -> str:
        if who == self.owner:
            return self.owner_name
        r = self.users_db.execute("SELECT name FROM users WHERE email = ?", (who.split(":", 1)[-1],)).fetchone()
        return (r[0] if r else "") or who.split(":", 1)[-1].split("@")[0]

    # -- visitors (owner only; app.py checks who is asking) --
    def invite(self, name: str = "", email: str = "", days: int = 7) -> dict:
        self._auth_tables()
        now, code = int(self.now()), secrets.token_urlsafe(12)
        em = (email or "").strip().lower()
        if em and (em == self.owner or self.users_db.execute("SELECT 1 FROM users WHERE email = ?", (em,)).fetchone()):
            raise ValueError("that email already has an account")
        self.users_db.execute("INSERT INTO invites VALUES (?,?,?,?,?,NULL,NULL)", (code, (name or "").strip()[:60], em, now, now + days * 86400))
        self.users_db.commit()
        self.audit(self.owner, "people.invite", f"{name} {em}".strip(), "OK")
        return {"code": code, "name": name, "email": em, "expires_t": now + days * 86400}

    def invite_info(self, code: str) -> dict:
        self._auth_tables()
        r = self.users_db.execute("SELECT name, email, expires_t, used_t FROM invites WHERE code = ?", (code or "",)).fetchone()
        if not r:
            raise AuthError("this invite link is not valid")
        if r[3]:
            raise AuthError("this invite link was already used; sign in instead")
        if r[2] < self.now():
            raise AuthError("this invite link has expired; ask for a new one")
        return {"name": r[0] or "", "email": r[1] or "", "expires_t": r[2]}

    def join(self, code: str, name: str, email: str, password: str) -> str:
        now = self.now()
        if self._locked("join", now):
            raise AuthError("too many tries; wait 15 minutes")
        try:
            inv = self.invite_info(code)
        except AuthError as exc:
            self._fail("join", now, str(exc))
        em = (inv["email"] or email or "").strip().lower()
        nm = (name or inv["name"] or "").strip()[:60]
        if "@" not in em or "." not in em.split("@")[-1]:
            raise ValueError("enter a valid email")
        if not nm:
            raise ValueError("enter your name")
        if len(password or "") < 8:
            raise ValueError("the password needs at least 8 characters")
        if em == self.owner or self.users_db.execute("SELECT 1 FROM users WHERE email = ?", (em,)).fetchone():
            raise ValueError("that email already has an account; sign in instead")
        self.users_db.execute("INSERT INTO users (email, name, pw_hash, created_t, invite, expires_t) VALUES (?,?,?,?,?,?)",
                              (em, nm, hash_password(password), int(now), code, int(now + GUEST_DAYS * 86400)))   # Oct 12: 3 days
        self.users_db.execute("UPDATE invites SET used_t = ?, used_by = ? WHERE code = ?", (int(now), em, code))
        self.users_db.commit()
        self.audit("guest:" + em, "people.join", nm, "OK")
        return self._session("guest:" + em, 7 * 86400)

    def people(self) -> dict:
        self._auth_tables()
        users = []
        answered = {e for (e,) in self.users_db.execute("SELECT email FROM feedback")}
        for em, nm, t, x in self.users_db.execute("SELECT email, name, created_t, expires_t FROM users ORDER BY created_t"):
            last = self.users_db.execute("SELECT max(t) FROM audit WHERE who = ? AND action = 'login' AND result = 'OK'",
                                         ("guest:" + em,)).fetchone()[0]
            users.append({"email": em, "name": nm, "joined_t": t, "last_login_t": last or t, "expires_t": x,
                          "expired": bool(x and x <= self.now()), "feedback": em in answered})
        inv = [{"code": c, "name": n, "email": e, "expires_t": x} for c, n, e, x in self.users_db.execute(
            "SELECT code, name, email, expires_t FROM invites WHERE used_t IS NULL AND expires_t > ? ORDER BY created_t DESC",
            (int(self.now()),))]
        return {"owner": {"email": self.owner, "name": self.owner_name}, "visitors": users, "invites": inv}

    def remove_person(self, email: str) -> bool:
        """Removes a visitor (their sign-in stops working at once) or cancels an invite (by code)."""
        self._auth_tables()
        em = (email or "").strip().lower()
        n = self.users_db.execute("DELETE FROM users WHERE email = ?", (em,)).rowcount
        n += self.users_db.execute("DELETE FROM invites WHERE code = ? AND used_t IS NULL", (email or "",)).rowcount
        self.users_db.commit()
        self.audit(self.owner, "people.remove", em, "OK" if n else "NONE")
        return bool(n)

    def audit(self, who: str, action: str, detail: str, result: str) -> None:
        self.db.execute("INSERT INTO audit (t, who, action, detail, result) VALUES (?,?,?,?,?)",
                        (int(self.now()), who, action, str(detail)[:500], str(result)[:500]))
        self.db.commit()

    # -- the Agent's data --
    def _explorer(self):
        from src.intelligence import explorer_live as xl

        if not (self.dir / "explorer_state.pkl").exists():
            return None
        return xl.Explorer(self.dir, hands=self.hands, now=self.now, alert=lambda *a: None)

    def _layer(self):
        from src.intelligence import portfolio_layer as pl

        return pl.PortfolioLayer(self.dir)

    @property
    def hands(self):
        if self._hands is None:
            from src.intelligence.explorer_live import Hands

            self._hands = Hands()
        return self._hands

    def prices(self) -> dict[str, float]:
        ex = self._explorer()
        return ex.prices() if ex else {}

    def _alerts(self, n: int = 20) -> list[dict]:
        p = self.dir / "watch_alerts.jsonl"
        if not p.exists():
            return []
        rows = [json.loads(x) for x in p.read_text().splitlines()[-400:] if x.strip()]
        return [r for r in rows if r.get("level") != "PHONE"][-n:][::-1]

    def _latest(self, folder: str) -> dict | None:
        d = self.dir / folder
        files = sorted(d.glob("*.md")) if d.exists() else []
        return {"name": files[-1].stem, "markdown": files[-1].read_text()} if files else None

    def today(self) -> dict:
        ex = self._explorer()
        xs = ex.status() if ex else None
        px = ex.prices() if ex else {}
        ps = self._layer().status(px)
        return {
            "as_of": _utc(self.now()), "version": VERSION, "paper_only": True,
            "explorer": ({"equity": xs["equity"], "realized_usd": xs["realized_usd"], "unrealized_usd": xs["unrealized_usd"],
                          "open_trades": len(xs["open"]), "pending_orders": len(xs["pending_orders"])} if xs else None),
            "portfolio": {"mode": ps["mode"], "main": ps["books"]["MAIN"], "shadow": ps["books"]["SHADOW"],
                          "btc_gate": (ps.get("last_decision") or {}).get("btc_gate"), "pending": ps["pending"]},
            "alerts": self._alerts(),
            "daily_report": self._latest("explorer_daily"),
        }

    def portfolio(self) -> dict:
        ps = self._layer().status(self.prices())
        last = ps.get("last_decision") or {}
        order = {"STRONG": 0, "OK": 1, "WEAK": 2, "OUT": 3}
        ratings = sorted(({"coin": c, **r} for c, r in (last.get("ratings") or {}).items()), key=lambda r: (order.get(r["rating"], 9), r["coin"]))
        ex = self._explorer()
        for r in ratings:   # 60 daily closes per coin for the sparkline
            eng = ex.st["engines"].get(r["coin"]) if ex else None
            r["spark"] = [b[4] for b in list(eng.tf["1d"].bars)[-60:]] if eng else []
        return {"mode": ps["mode"], "rule": ps["rule"], "books": ps["books"], "pending": ps["pending"],
                "decided": last.get("day"), "btc_gate": last.get("btc_gate"), "ratings": ratings}

    def evidence(self) -> dict:
        ex = self._explorer()
        out: dict[str, Any] = {"open_trades": ex.status()["open"] if ex else [], "recent_closed": [], "sightings_today": {},
                               "weekly": self._latest("explorer_weekly"), "registry": None}
        if ex:
            rows = [json.loads(j) for (j,) in ex.store.book.execute(
                "SELECT json FROM trades WHERE shadow='' ORDER BY exit_t DESC LIMIT 30")]
            out["recent_closed"] = [{"coin": r["coin"], "setup": r["setup"], "type": r["type"], "net_usd": r.get("ACTUAL_net"),
                                     "bell": r.get("ACTUAL_bell"), "closed": _utc(r["ACTUAL_exit_t"]) if r.get("ACTUAL_exit_t") else None} for r in rows]
            since = int(self.now() - 86400)
            for (j,) in ex.store.book.execute("SELECT json FROM events WHERE kind='SIGHTING' AND t >= ?", (since,)):
                e = json.loads(j)
                s = out["sightings_today"].setdefault(e["setup"], {"seen": 0, "p_target": [], "net_pct": [], "reliable": False})
                s["seen"] += 1
                if e.get("p_target_3_before_1.5") is not None:
                    s["p_target"].append(e["p_target_3_before_1.5"])
                if e.get("net_pct_3_1.5_24h") is not None:
                    s["net_pct"].append(e["net_pct_3_1.5_24h"])
                s["reliable"] |= bool(e.get("stable_positive_after_costs"))
            allc = [json.loads(j) for (j,) in ex.store.book.execute("SELECT json FROM trades WHERE shadow=''")]

            def agg(key):
                g: dict[str, list] = {}
                for r in allc:
                    if r.get("ACTUAL_net") is not None:
                        g.setdefault(str(r.get(key)), []).append(r["ACTUAL_net"])
                return [{"name": k, "n": len(v), "win_rate": round(sum(1 for x in v if x > 0) / len(v), 3), "net_usd": round(sum(v), 2)}
                        for k, v in sorted(g.items())]
            out["by_setup"], out["by_exit"], out["by_type"] = agg("setup"), agg("ACTUAL_bell"), agg("type")
            out["closed_total"] = {"n": len(allc), "net_usd": round(sum(r.get("ACTUAL_net") or 0 for r in allc), 2),
                                   "win_rate": round(sum(1 for r in allc if (r.get("ACTUAL_net") or 0) > 0) / len(allc), 3) if allc else None}
            for s in out["sightings_today"].values():
                s["p_target"] = round(sum(s["p_target"]) / len(s["p_target"]), 3) if s["p_target"] else None
                s["net_pct"] = round(sum(s["net_pct"]) / len(s["net_pct"]), 3) if s["net_pct"] else None
        reg = docs_dir(self.dir) / "variable_registry.json"
        if reg.exists():
            r = json.loads(reg.read_text())
            out["registry"] = {"counts": {st: sum(1 for v in r["variables"] if v["status"] == st) for st in ("KEEP", "WATCH", "DROP")},
                               "variables": r["variables"], "untested": r["untested"]}
        return out

    def safety(self) -> dict:
        out: dict[str, Any] = {"paper_only": True, "live_trading": "not connected (paper only)"}
        try:
            out["kill_switch_on"] = bool(self.hands.kill_switch_on())
            out["hands_reachable"] = True
        except Exception as exc:  # noqa: BLE001
            out["kill_switch_on"], out["hands_reachable"], out["hands_error"] = None, False, str(exc)[:160]
        bp = self.dir / "breaker_state.json"
        out["circuit_breakers"] = json.loads(bp.read_text()) if bp.exists() else {}
        hb = self.dir / "watch_heartbeat.jsonl"
        if hb.exists():
            last = [x for x in hb.read_text().splitlines() if x.strip()][-1:]
            out["hourly_watch_last"] = json.loads(last[0]).get("ts") if last else None
        dec = self.dir / "explorer_decisions.jsonl"
        out["explorer_last_scan"] = _utc(dec.stat().st_mtime) if dec.exists() else None
        out["explorer_stale"] = bool(dec.exists() and self.now() - dec.stat().st_mtime > 40 * 60)
        out["recent_actions"] = [dict(zip(("time", "who", "action", "detail", "result"), (_utc(t), w, a, d, r)))
                                 for t, w, a, d, r in self.db.execute("SELECT t, who, action, detail, result FROM audit ORDER BY seq DESC LIMIT 15")]
        return out

    # -- history and charts --
    def record_snapshot(self) -> dict | None:
        """One point of value history (run every 15 minutes by the service)."""
        ex = self._explorer()
        if not ex:
            return None
        px = ex.prices()
        ps = self._layer().status(px)
        row = (int(self.now()), ex.status()["equity"], ps["books"]["MAIN"]["equity"], ps["books"]["SHADOW"]["equity"], px.get("BTC"))
        self.db.execute("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?)", row)
        self.db.commit()
        return dict(zip(("t", "explorer", "main", "shadow", "btc"), row))

    def history(self, days: float = 30) -> dict:
        lo = int(self.now() - days * 86400)
        rows = self.db.execute("SELECT t, explorer, main, shadow, btc FROM snapshots WHERE t >= ? ORDER BY t", (lo,)).fetchall()
        return {"points": [dict(zip(("t", "explorer", "main", "shadow", "btc"), r)) for r in rows]}

    def coin(self, sym: str) -> dict:
        sym = sym.upper()
        ex = self._explorer()
        if not ex or sym not in ex.st["engines"]:
            raise ValueError(f"unknown coin {sym}")
        eng = ex.st["engines"][sym]

        def series(tf: str, n: int) -> list[dict]:
            s = eng.tf[tf]
            out, a20, a50 = [], None, None   # averages recomputed over the stored bars (up to 260) for the chart
            k20, k50 = 2 / 21, 2 / 51
            for b in list(s.bars):
                a20 = b[4] if a20 is None else a20 + k20 * (b[4] - a20)
                a50 = b[4] if a50 is None else a50 + k50 * (b[4] - a50)
                out.append({"t": b[0], "c": b[4], "ema20": a20, "ema50": a50})
            return out[-n:]

        ps = self.portfolio()
        rating = next((r for r in ps["ratings"] if r["coin"] == sym), None)
        trades = [t for t in ex.status()["open"] if t["coin"] == sym]
        closed = [json.loads(j) for (j,) in ex.store.book.execute(
            "SELECT json FROM trades WHERE shadow='' AND coin=? ORDER BY exit_t DESC LIMIT 20", (sym,))]
        return {"coin": sym, "price": eng.tf["5m"].last[4] if eng.tf["5m"].last else None, "rating": rating,
                "held_usd": ps["books"]["MAIN"]["holdings"].get(sym, 0.0),
                "daily": series("1d", 120), "hourly": series("1h", 96),
                "open_trades": trades,
                "closed_trades": [{"setup": r["setup"], "type": r["type"], "net_usd": r.get("ACTUAL_net"), "bell": r.get("ACTUAL_bell"),
                                   "closed": _utc(r["ACTUAL_exit_t"]) if r.get("ACTUAL_exit_t") else None} for r in closed]}

    # -- actions --
    def approve(self, who: str, ids: list[str] | str) -> list[dict]:
        """The trend portfolio's suggestions, approved. Buys pass the trade guard (the kill switch, the Explorer's price at most
        15 minutes old); a suggestion it holds back stays open."""
        from jarvis.service import trade_guard as tg

        px = self.prices()
        seen, L = tg.times(px) or {}, self._layer()
        fills = L.approve(ids, px, int(self.now()), by=f"{who} (Jarvis app)", guard=lambda book, coin: tg.blocked(
            self, f"T3-{book}", coin, price_t=seen.get(coin, 0), max_age_s=tg.BAR_PRICE_S))
        held = L.blocked
        self.audit(who, "portfolio.approve", ids, f"{len(fills)} paper fills" + (f"; held back: {held[0]['why']}" if held else ""))
        if held and not fills:
            raise ValueError(f"Nothing was bought: {held[0]['why']}. The suggestion stays open.")
        return fills

    def reject(self, who: str, ids: list[str] | str) -> int:
        n = self._layer().reject(ids, by=who)
        self.audit(who, "portfolio.reject", ids, f"{n} rejected")
        return n

    def set_mode(self, who: str, mode: str, confirm: bool) -> str:
        if not confirm:
            raise ConfirmRequired("changing the portfolio mode needs confirm=true")
        L = self._layer()
        L.set_mode(mode, by=f"{who} (Jarvis app)")
        self.audit(who, "portfolio.mode", mode, "OK")
        return L.mode

    def set_kill(self, who: str, on: bool, confirm: bool) -> dict:
        if not confirm:
            raise ConfirmRequired("the kill switch needs confirm=true")
        import requests

        from src.tools import ananta_api

        tok = ananta_api.login()
        r = requests.put(f"{ananta_api.BASE_URL}/api/settings", json={"manual_kill_switch": bool(on)},
                         headers=ananta_api.get_headers(tok.get("token")), timeout=20)
        res = {"status_code": r.status_code, "ok": r.status_code == 200, "kill_switch_on": bool(on)}
        self.audit(who, "safety.kill_switch", "ON" if on else "OFF", res)
        return res

    def register_push(self, who: str, token: str, device: str) -> None:
        if not (token or "").startswith("ExponentPushToken["):
            raise ValueError("not an Expo push token")
        self.db.execute("INSERT OR REPLACE INTO push_tokens VALUES (?,?,?)", (token, device[:80], int(self.now())))
        self.db.commit()
        self.audit(who, "push.register", device, "OK")

    def push_tokens(self) -> list[str]:
        return [t for (t,) in self.db.execute("SELECT token FROM push_tokens")]


def from_env(db_file: str = "jarvis.sqlite") -> Jarvis:
    from dotenv import load_dotenv

    load_dotenv()
    return Jarvis(os.getenv("JARVIS_AGENT_DIR", "."), owner_email=os.getenv("JARVIS_OWNER_EMAIL", ""),
                  password_hash=os.getenv("JARVIS_PASSWORD_HASH", ""), secret=os.getenv("JARVIS_SECRET", ""), db_file=db_file)


if __name__ == "__main__":
    import getpass
    import sys

    if sys.argv[1:] == ["hash-password"]:
        pw = getpass.getpass("New Jarvis password: ")
        if pw != getpass.getpass("Again: ") or len(pw) < 10:
            raise SystemExit("passwords differ or shorter than 10 characters")
        print(hash_password(pw))
    elif sys.argv[1:] == ["new-secret"]:
        print(secrets.token_urlsafe(48))
    else:
        raise SystemExit("usage: python -m jarvis.service.core hash-password | new-secret")
