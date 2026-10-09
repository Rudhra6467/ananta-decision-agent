"""Reaching people when the app is closed (build plan 1.7, D4).

  web push   the website (and the iPhone Home Screen app) can show notifications. Each device that says yes is stored with its
             account; a fired watch, an approval waiting or a warning reaches every device of that account. The keys (VAPID) are made
             once and kept outside the code folder (~/.ananta/vapid_*), never in git.
  email      optional: when an SMTP address is set in the service's .env (JARVIS_SMTP_URL, e.g. smtps://user:app-password@smtp.gmail.com:465)
             and the person turns "Email me" on, the same notes go by email. Without it, the switch says email is not set up yet.
Madhav's phone keeps its own push (paper_watch.push_phone) as well.
"""
from __future__ import annotations

import base64
import json
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

KEYS = Path.home() / ".ananta"
PRIV = KEYS / "vapid_private.pem"
PUB = KEYS / "vapid_public.txt"
CONTACT = "mailto:alerts@livetrading247.com"


def _table(db) -> None:
    db.execute("CREATE TABLE IF NOT EXISTS web_push_subs (endpoint TEXT PRIMARY KEY, sub TEXT, t INTEGER, device TEXT)")


def public_key() -> str:
    """The application server key the browser needs to subscribe (made once)."""
    if not PRIV.exists() or not PUB.exists():
        from cryptography.hazmat.primitives import serialization
        from py_vapid import Vapid

        KEYS.mkdir(parents=True, exist_ok=True)
        v = Vapid()
        v.generate_keys()
        v.save_key(str(PRIV))
        raw = v.public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
        PUB.write_text(base64.urlsafe_b64encode(raw).decode().rstrip("="))
        os.chmod(PRIV, 0o600)
    return PUB.read_text().strip()


def subscribe(j, sub: dict, device: str = "") -> dict:
    if not isinstance(sub, dict) or not str(sub.get("endpoint", "")).startswith("https://") or not (sub.get("keys") or {}).get("p256dh"):
        raise ValueError("not a push subscription")
    _table(j.db)
    j.db.execute("INSERT OR REPLACE INTO web_push_subs VALUES (?,?,?,?)", (sub["endpoint"], json.dumps(sub), int(j.now()), device[:80]))
    j.db.commit()
    return {"devices": devices(j)}


def devices(j) -> int:
    _table(j.db)
    return j.db.execute("SELECT COUNT(*) FROM web_push_subs").fetchone()[0]


def web_push(j, title: str, body: str, url: str = "/") -> int:
    """Send to every device of this account; devices that are gone (404/410) are forgotten. Returns how many got it."""
    _table(j.db)
    rows = j.db.execute("SELECT endpoint, sub FROM web_push_subs").fetchall()
    if not rows:
        return 0
    from pywebpush import WebPushException, webpush

    public_key()
    sent = 0
    for endpoint, sub in rows:
        try:
            webpush(json.loads(sub), json.dumps({"title": title[:120], "body": body[:300], "url": url}), vapid_private_key=str(PRIV),
                    vapid_claims={"sub": CONTACT}, timeout=10)
            sent += 1
        except WebPushException as exc:
            code = getattr(getattr(exc, "response", None), "status_code", None)
            if code in (404, 410):
                j.db.execute("DELETE FROM web_push_subs WHERE endpoint=?", (endpoint,))
                j.db.commit()
        except Exception:  # noqa: BLE001  one device never stops the others
            continue
    return sent


def email_ready() -> bool:
    return bool(os.getenv("JARVIS_SMTP_URL"))


def send_email(to: str, title: str, body: str) -> bool:
    url = os.getenv("JARVIS_SMTP_URL", "")
    if not url or "@" not in (to or ""):
        return False
    u = urlparse(url)
    msg = EmailMessage()
    msg["Subject"] = f"Ananta: {title}"[:150]
    msg["From"] = os.getenv("JARVIS_SMTP_FROM") or unquote(u.username or "")
    msg["To"] = to
    msg.set_content(f"{body}\n\nOpen Ananta: https://livetrading247.com\n\nPaper trading only. Turn these emails off in Cockpit.")
    try:
        cls = smtplib.SMTP_SSL if u.scheme == "smtps" else smtplib.SMTP
        with cls(u.hostname, u.port or (465 if u.scheme == "smtps" else 587), timeout=20) as s:
            if u.scheme != "smtps":
                s.starttls()
            s.login(unquote(u.username or ""), unquote(u.password or ""))
            s.send_message(msg)
        return True
    except Exception:  # noqa: BLE001
        return False


def notify(j, title: str, body: str, email: str = "", url: str = "/") -> dict[str, Any]:
    """Everything that should reach one account: web push to its devices, and email when it asked for it."""
    out = {"web": 0, "email": False}
    try:
        out["web"] = web_push(j, title, body, url)
    except Exception:  # noqa: BLE001
        pass
    try:
        from jarvis.service import account

        if email and account.profile(j.db).get("email_alerts"):
            out["email"] = send_email(email, title, body)
    except Exception:  # noqa: BLE001
        pass
    return out
