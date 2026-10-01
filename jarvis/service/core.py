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


class AuthError(Exception):
    pass


class ConfirmRequired(Exception):
    pass


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


def make_token(secret: str, sub: str, now: float, ttl: int = TOKEN_TTL_S) -> str:
    body = _b64(json.dumps({"sub": sub, "exp": int(now + ttl), "iat": int(now)}).encode())
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


# ---------------------------------------------------------------------------
class Jarvis:
    def __init__(self, agent_dir: Path | str, *, owner_email: str, password_hash: str, secret: str,
                 hands: Any = None, now: Callable[[], float] = time.time):
        if not (owner_email and password_hash and secret and len(secret) >= 32):
            raise ValueError("owner email, password hash and a secret of at least 32 characters are required")
        self.dir = Path(agent_dir)
        self.owner, self.pw_hash, self.secret = owner_email.strip().lower(), password_hash, secret
        self.now = now
        self._hands = hands
        self.db = sqlite3.connect(str(self.dir / "jarvis.sqlite"), check_same_thread=False)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS audit (seq INTEGER PRIMARY KEY AUTOINCREMENT, t INTEGER, who TEXT, action TEXT, detail TEXT, result TEXT);
            CREATE TABLE IF NOT EXISTS failed_logins (t INTEGER);
            CREATE TABLE IF NOT EXISTS push_tokens (token TEXT PRIMARY KEY, device TEXT, t INTEGER);
            CREATE TABLE IF NOT EXISTS snapshots (t INTEGER PRIMARY KEY, explorer REAL, main REAL, shadow REAL, btc REAL);
        """)

    # -- auth --
    def login(self, email: str, password: str) -> str:
        now = self.now()
        recent = self.db.execute("SELECT count(*) FROM failed_logins WHERE t > ?", (int(now - FAIL_WINDOW_S),)).fetchone()[0]
        if recent >= MAX_FAILED:
            self.audit("?", "login", email, "LOCKED")
            raise AuthError("too many failed logins; wait 15 minutes")
        if (email or "").strip().lower() != self.owner or not verify_password(password or "", self.pw_hash):
            self.db.execute("INSERT INTO failed_logins VALUES (?)", (int(now),))
            self.db.commit()
            self.audit("?", "login", email, "FAILED")
            raise AuthError("wrong email or password")
        self.db.execute("DELETE FROM failed_logins")
        self.audit(self.owner, "login", "", "OK")
        return make_token(self.secret, self.owner, now)

    def check(self, token: str) -> str:
        p = read_token(self.secret, token or "", self.now())
        if p.get("sub") != self.owner:
            raise AuthError("not the owner")
        return p["sub"]

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
        reg = self.dir / "docs" / "variable_registry.json"
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
        fills = self._layer().approve(ids, self.prices(), int(self.now()), by=f"{who} (Jarvis app)")
        self.audit(who, "portfolio.approve", ids, f"{len(fills)} paper fills")
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


def from_env() -> Jarvis:
    from dotenv import load_dotenv

    load_dotenv()
    return Jarvis(os.getenv("JARVIS_AGENT_DIR", "."), owner_email=os.getenv("JARVIS_OWNER_EMAIL", ""),
                  password_hash=os.getenv("JARVIS_PASSWORD_HASH", ""), secret=os.getenv("JARVIS_SECRET", ""))


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
