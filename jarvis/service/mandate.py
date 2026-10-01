"""The owner's mandate (what Ananta is for, what is allowed) and the pending-actions inbox.

Mandate: short sections of plain sentences. Ananta reads it before every answer. Only the owner changes it: directly in the
app, or by confirming a change Ananta proposed. Every version is kept.

Pending actions: anything Ananta prepares that changes something (a mandate edit now; alerts and paper orders later) waits
here until the owner confirms it in the app. Ananta itself can only create pending items, never execute them.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, Callable

DEFAULT_MANDATE = {
    "goal": [
        "Build Ananta into an autonomous trading assistant (Jarvis) that earns trust with evidence before it trades real money.",
        "Prove it on paper first, then go live with $500, then grow to larger markets.",
        "Long term: an Aladdin-style knowledge base. Carry forward only what proves itself.",
    ],
    "markets_now": [
        "Crypto spot, 10 coins: BTC ETH SOL ADA DOGE AVAX BCH LINK LTC XRP.",
        "Buying only for now (no shorting). Costs measured at NDAX rates (0.20% fee + spread).",
    ],
    "markets_later": [
        "Crypto ~150, India 500-600, Canada 600-800, US 1000-1100 instruments; options, futures and commodities later.",
    ],
    "styles": [
        "Short-term: hours to days. Context from daily / 4h / 1h, timing from 5m-15m.",
        "Portfolio (T3): hold coins in multi-week uptrends, go to cash in slides.",
        "Intraday: idle; keep collecting evidence and probabilities only.",
    ],
    "setups": [
        "Explorer E1-E5 (pullback, breakout, bounce, momentum, squeeze) on paper; E6-E8 dips watched only.",
        "Hunter (reversal) and Squeeze (compression) in the hourly watch.",
        "T3 portfolio trend rule for the basket.",
    ],
    "limits": [
        "Paper only. No exchange connected; live trading locked.",
        "$100 per Explorer paper trade; at most 20 open and 30 new per day.",
        "Portfolio in Suggest mode unless the owner switches Autopilot on.",
        "Anything that changes something needs the owner's confirmation in the app (Face ID).",
        "Live rules (size, stops, daily loss limit) must be written and approved before the first real order.",
    ],
    "how_to_talk": [
        "Plain language first, numbers second. Say when the evidence is thin.",
        "Ask when a request is unclear. Never invent facts.",
    ],
}
SECTION_NAMES = {"goal": "Goal", "markets_now": "Markets now", "markets_later": "Markets later", "styles": "Trading styles",
                 "setups": "Setups we look for", "limits": "Limits and permissions", "how_to_talk": "How to talk to me"}


class Mandate:
    def __init__(self, db, now: Callable[[], float] = time.time):
        self.db, self.now = db, now
        db.executescript("""
            CREATE TABLE IF NOT EXISTS mandate (version INTEGER PRIMARY KEY AUTOINCREMENT, t INTEGER, by TEXT, why TEXT, json TEXT);
            CREATE TABLE IF NOT EXISTS pending_actions (id TEXT PRIMARY KEY, t INTEGER, kind TEXT, summary TEXT, payload TEXT,
                status TEXT, by TEXT, decided_t INTEGER, result TEXT, thread TEXT);
        """)
        db.commit()

    # ---- mandate ----
    def get(self) -> dict:
        row = self.db.execute("SELECT version, t, by, json FROM mandate ORDER BY version DESC LIMIT 1").fetchone()
        if not row:
            return {"version": 0, "updated": None, "by": "default", "sections": DEFAULT_MANDATE, "names": SECTION_NAMES}
        return {"version": row[0], "updated": row[1], "by": row[2], "sections": json.loads(row[3]), "names": SECTION_NAMES}

    def set(self, who: str, sections: dict, why: str = "") -> dict:
        clean = {}
        for k, items in sections.items():
            if k not in SECTION_NAMES:
                raise ValueError(f"unknown section {k}")
            items = [str(x).strip()[:300] for x in (items or []) if str(x).strip()]
            if len(items) > 12:
                raise ValueError(f"too many lines in {k}")
            clean[k] = items
        for k in SECTION_NAMES:
            clean.setdefault(k, self.get()["sections"].get(k, []))
        self.db.execute("INSERT INTO mandate (t, by, why, json) VALUES (?,?,?,?)", (int(self.now()), who, why[:300], json.dumps(clean)))
        self.db.commit()
        return self.get()

    def text(self) -> str:
        m = self.get()
        return "\n".join(f"{SECTION_NAMES[k]}: " + " | ".join(v) for k, v in m["sections"].items() if v)

    def history(self, n: int = 10) -> list[dict]:
        return [{"version": v, "t": t, "by": b, "why": w} for v, t, b, w in
                self.db.execute("SELECT version, t, by, why FROM mandate ORDER BY version DESC LIMIT ?", (n,))]

    # ---- pending actions ----
    def propose(self, kind: str, summary: str, payload: dict, thread: str | None = None) -> dict:
        aid = "A" + uuid.uuid4().hex[:10]
        self.db.execute("INSERT INTO pending_actions (id, t, kind, summary, payload, status, thread) VALUES (?,?,?,?,?,?,?)",
                        (aid, int(self.now()), kind, summary[:300], json.dumps(payload), "PENDING", thread))
        self.db.commit()
        return {"id": aid, "kind": kind, "summary": summary, "status": "PENDING"}

    def pending(self) -> list[dict]:
        return [{"id": i, "t": t, "kind": k, "summary": s, "payload": json.loads(p), "status": st}
                for i, t, k, s, p, st in self.db.execute(
                    "SELECT id, t, kind, summary, payload, status FROM pending_actions WHERE status='PENDING' ORDER BY t DESC")]

    def action(self, aid: str) -> dict | None:
        r = self.db.execute("SELECT id, t, kind, summary, payload, status, result FROM pending_actions WHERE id=?", (aid,)).fetchone()
        return None if not r else {"id": r[0], "t": r[1], "kind": r[2], "summary": r[3], "payload": json.loads(r[4]), "status": r[5], "result": r[6]}

    def decide(self, who: str, aid: str, confirm: bool, executors: dict[str, Callable[[str, dict], Any]]) -> dict:
        a = self.action(aid)
        if not a:
            raise ValueError("unknown action")
        if a["status"] != "PENDING":
            raise ValueError(f"already {a['status'].lower()}")
        if not confirm:
            self.db.execute("UPDATE pending_actions SET status='CANCELLED', by=?, decided_t=? WHERE id=?", (who, int(self.now()), aid))
            self.db.commit()
            return {**a, "status": "CANCELLED"}
        fn = executors.get(a["kind"])
        if not fn:
            raise ValueError(f"no executor for {a['kind']}")
        result = fn(who, a["payload"])
        self.db.execute("UPDATE pending_actions SET status='DONE', by=?, decided_t=?, result=? WHERE id=?",
                        (who, int(self.now()), json.dumps(result, default=str)[:2000], aid))
        self.db.commit()
        return {**a, "status": "DONE", "result": result}

    def apply_mandate_change(self, who: str, p: dict) -> dict:
        m = self.get()["sections"]
        sec, op, text = p.get("section"), p.get("op", "add"), str(p.get("text", "")).strip()
        if sec not in SECTION_NAMES:
            raise ValueError(f"unknown section {sec}")
        items = list(m.get(sec, []))
        if op == "add":
            items.append(text)
        elif op == "remove":
            items = [x for x in items if x != p.get("old")]
        elif op == "replace":
            items = [text if x == p.get("old") else x for x in items]
            if p.get("old") not in m.get(sec, []):
                items.append(text)
        else:
            raise ValueError("op is add, remove or replace")
        out = self.set(who, {**m, sec: items}, why=f"confirmed Ananta's proposal: {op} in {sec}")
        return {"version": out["version"]}
