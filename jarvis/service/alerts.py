"""Alerts you create by talking ("tell me if BTC drops below 80k", "tell me when AVAX's breakout completes") and daily briefings.

Alerts are plain rules checked every 15 minutes with no AI cost. Ananta only PREPARES an alert (pending action); it becomes
active when the owner confirms. When one fires, the phone gets a short notification (ntfy) and the Home feed shows it.
Briefings (morning 08:00 and evening 21:30 Toronto) are written once each by the free model and pushed in one line.
"""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from typing import Any, Callable

KINDS = {
    "price_above": "price rises above",
    "price_below": "price falls below",
    "setup": "a setup completes",
    "move_pct": "moves more than",
}


def _tz():
    from zoneinfo import ZoneInfo

    return ZoneInfo("America/Toronto")


class Alerts:
    def __init__(self, db, now: Callable[[], float] = time.time):
        self.db, self.now = db, now
        db.executescript("""
            CREATE TABLE IF NOT EXISTS alerts (id TEXT PRIMARY KEY, t INTEGER, kind TEXT, coin TEXT, value REAL, setup TEXT, note TEXT,
                status TEXT, fired_t INTEGER, message TEXT, by TEXT);
            CREATE TABLE IF NOT EXISTS briefings (id TEXT PRIMARY KEY, t INTEGER, kind TEXT, day TEXT, text TEXT, reply TEXT);
        """)
        db.commit()

    # ---- alerts ----
    @staticmethod
    def describe(kind: str, coin: str, value: float | None, setup: str | None) -> str:
        if kind == "price_above":
            return f"{coin} price rises above ${value:,.6g}"
        if kind == "price_below":
            return f"{coin} price falls below ${value:,.6g}"
        if kind == "setup":
            return f"{coin}: {'any Explorer setup' if setup in (None, '', 'ANY') else setup} completes"
        if kind == "move_pct":
            return f"{coin} moves more than {value:g}% in a day"
        return kind

    @staticmethod
    def validate(p: dict) -> dict:
        kind = p.get("kind")
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {', '.join(KINDS)}")
        coin = str(p.get("coin") or "").upper().replace("/USD", "")
        if not coin.isalnum() or len(coin) > 6:
            raise ValueError("coin is required, e.g. BTC")
        value = p.get("value")
        if kind in ("price_above", "price_below", "move_pct"):
            try:
                value = float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError("a number is required for this alert") from exc
            if value <= 0:
                raise ValueError("the number must be positive")
        setup = (p.get("setup") or "ANY").upper() if kind == "setup" else None
        if setup and setup != "ANY" and setup not in ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"):
            raise ValueError("setup must be E1-E8 or ANY")
        return {"kind": kind, "coin": coin, "value": value, "setup": setup, "note": str(p.get("note") or "")[:200]}

    def create(self, who: str, p: dict) -> dict:
        v = self.validate(p)
        aid = "L" + uuid.uuid4().hex[:9]
        self.db.execute("INSERT INTO alerts (id, t, kind, coin, value, setup, note, status, by) VALUES (?,?,?,?,?,?,?,?,?)",
                        (aid, int(self.now()), v["kind"], v["coin"], v["value"], v["setup"], v["note"], "ACTIVE", who))
        self.db.commit()
        return {"id": aid, "status": "ACTIVE", "what": self.describe(v["kind"], v["coin"], v["value"], v["setup"])}

    def list(self, include_done: bool = True) -> list[dict]:
        q = "SELECT id, t, kind, coin, value, setup, note, status, fired_t, message FROM alerts"
        q += "" if include_done else " WHERE status='ACTIVE'"
        out = []
        for i, t, k, c, v, s, n, st, ft, msg in self.db.execute(q + " ORDER BY t DESC LIMIT 100"):
            out.append({"id": i, "t": t, "kind": k, "coin": c, "value": v, "setup": s, "note": n, "status": st, "fired_t": ft,
                        "message": msg, "what": self.describe(k, c, v, s)})
        return out

    def turn_off(self, who: str, aid: str) -> None:
        self.db.execute("UPDATE alerts SET status='OFF' WHERE id=? AND status='ACTIVE'", (aid,))
        self.db.commit()

    def check(self, ex, push: Callable[[str, str], Any] | None = None) -> list[dict]:
        """Evaluate active alerts against the Explorer's latest prices and setup checklists. One-shot: fired alerts stop."""
        from src.intelligence import setup_checklist as sc

        if not ex:
            return []
        fired = []
        px = ex.prices()
        for a in self.list(include_done=False):
            eng = ex.st["engines"].get(a["coin"])
            if not eng or a["coin"] not in px:
                continue
            p = px[a["coin"]]
            msg = None
            if a["kind"] == "price_above" and p > a["value"]:
                msg = f"{a['coin']} is at ${p:,.6g}, above your ${a['value']:,.6g} line."
            elif a["kind"] == "price_below" and p < a["value"]:
                msg = f"{a['coin']} is at ${p:,.6g}, below your ${a['value']:,.6g} line."
            elif a["kind"] == "move_pct":
                d1 = list(eng.tf["1d"].bars)
                if d1:
                    ch = 100 * (p / d1[-1][4] - 1)
                    if abs(ch) >= a["value"]:
                        msg = f"{a['coin']} has moved {ch:+.1f}% today (your line: {a['value']:g}%)."
            elif a["kind"] == "setup" and eng.last_scan is not None and eng.ready():
                rows = sc.checklist(eng, eng.state(eng.last_scan))
                done = [r for r in rows if r["complete"] and (a["setup"] in ("ANY", None) and r["traded"] or r["setup"] == a["setup"])]
                if done:
                    msg = f"{a['coin']}: {done[0]['name']} ({done[0]['setup']}) has all its conditions met."
            if msg:
                self.db.execute("UPDATE alerts SET status='FIRED', fired_t=?, message=? WHERE id=?", (int(self.now()), msg, a["id"]))
                self.db.commit()
                fired.append({**a, "message": msg})
                if push:
                    try:
                        push(f"Ananta alert: {a['coin']}", msg + (f" Note: {a['note']}" if a["note"] else ""))
                    except Exception:  # noqa: BLE001  never break the loop
                        pass
        return fired

    # ---- briefings ----
    def latest_brief(self) -> dict | None:
        r = self.db.execute("SELECT id, t, kind, day, text, reply FROM briefings ORDER BY t DESC LIMIT 1").fetchone()
        return None if not r else {"id": r[0], "t": r[1], "kind": r[2], "day": r[3], "text": r[4], "reply": json.loads(r[5] or "{}")}

    def due_brief(self) -> str | None:
        """'morning' after 08:00 and 'evening' after 21:30 Toronto time, once per day each."""
        now = datetime.fromtimestamp(self.now(), _tz())
        day = now.strftime("%Y-%m-%d")
        kind = "evening" if (now.hour, now.minute) >= (21, 30) else "morning" if now.hour >= 8 else None
        if not kind:
            return None
        if self.db.execute("SELECT 1 FROM briefings WHERE day=? AND kind=?", (day, kind)).fetchone():
            return None
        return kind

    def write_brief(self, kind: str, ask_fn: Callable[[str], dict], push: Callable[[str, str], Any] | None = None) -> dict | None:
        day = datetime.fromtimestamp(self.now(), _tz()).strftime("%Y-%m-%d")
        q = ("Give me my morning briefing: what changed overnight, the portfolio, open trades, setups that are close, active alerts, "
             "and anything waiting for my approval. Keep the answer to 3 short sentences.") if kind == "morning" else \
            ("Give me my evening wrap-up: what happened today (buys, sells, portfolio, evidence collected), what is close to triggering, "
             "and anything waiting for me. Keep the answer to 3 short sentences.")
        r = ask_fn(q)
        if r.get("error"):
            return None
        bid = "B" + uuid.uuid4().hex[:9]
        self.db.execute("INSERT INTO briefings VALUES (?,?,?,?,?,?)", (bid, int(self.now()), kind, day, r.get("answer", ""), json.dumps(r, default=str)))
        self.db.commit()
        if push:
            try:
                push(f"Ananta {kind} brief", r.get("answer", "")[:400])
            except Exception:  # noqa: BLE001
                pass
        return {"id": bid, "kind": kind, "text": r.get("answer")}
