"""Portfolio manager layer (paper): Review #4's T3 rule as a daily portfolio with ratings, suggestions and approvals.

Rule T3 (docs/repair_shop/REVIEW_4_RESULTS.md): hold a coin while its daily close > daily EMA50 AND > daily EMA20
AND BTC's daily close > BTC's EMA50. Equal target share per available coin, reset weekly and on every change.

Two books, same rules:
  * MAIN   : follows the mode. SUGGEST (default) = changes wait for the operator's approval; AUTO = acts itself.
  * SHADOW : always AUTO. The gap between the two measures what waiting for approval costs.
Ratings: STRONG / OK / WEAK / OUT with reasons, every day, for every coin.
Paper only: no orders anywhere. Evidence class PAPER_PORTFOLIO.
"""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "portfolio.layer.v1"
RULE = "T3"
EVIDENCE_CLASS = "PAPER_PORTFOLIO"
START = 2000.0
FEE = 0.0020
HALF_SPREAD = {"BTC": 0.00178, "ETH": 0.00084, "SOL": 0.00289, "ADA": 0.00273, "DOGE": 0.00307,
               "AVAX": 0.00370, "BCH": 0.00400, "LINK": 0.00341, "LTC": 0.00334, "XRP": 0.00251}


def _utc(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M")


def daily_view(tf1d) -> dict | None:
    """From an explorer TfState('1d'): the numbers the rule and the ratings need (closed days only)."""
    if tf1d.n < 50 or not tf1d.bars:
        return None
    bars = list(tf1d.bars)
    c = bars[-1][4]
    e20, e50 = tf1d.e20h[-1], tf1d.e50h[-1]
    e20_5 = tf1d.ema_ago("20", 5)
    atr = tf1d.atrh[-1]
    ret30 = c / bars[-31][4] - 1 if len(bars) > 30 else None
    return {"day_close_t": bars[-1][0] + 86400, "close": c, "ema20": e20, "ema50": e50, "ema20_slope5": (e20 / e20_5 - 1) if e20_5 else 0.0,
            "atr": atr, "ret30": ret30, "rsi": tf1d.rsi}


def rate(coin: str, v: dict, btc_on: bool, mom_rank: float | None) -> tuple[str, bool, list[str]]:
    """(rating, rule_on, reasons). mom_rank: 0 (weakest 30-day return) .. 1 (strongest) among available coins."""
    reasons = []
    above50, above20 = v["close"] > v["ema50"], v["close"] > v["ema20"]
    on = above50 and above20 and btc_on
    if not btc_on:
        reasons.append("BTC below its 50-day average (market gate off)")
    if not above50:
        reasons.append("closed below its 50-day average")
    elif not above20:
        reasons.append("closed below its 20-day average (fast exit)")
    if not on:
        return "OUT", False, reasons
    cushion = (v["close"] - v["ema20"]) / v["atr"] if v["atr"] > 0 else 0.0
    reasons.append(f"above both averages; {cushion:.1f} ATR above the 20-day")
    if mom_rank is not None:
        reasons.append(f"30-day momentum rank {mom_rank:.0%}")
    if v["ema20_slope5"] <= 0:
        reasons.append("20-day average no longer rising")
    if cushion < 0.5 or (mom_rank is not None and mom_rank < 0.25) or v["ema20_slope5"] <= 0:
        return "WEAK", True, reasons
    if cushion >= 1.0 and (mom_rank is None or mom_rank >= 0.5) and v["ema20_slope5"] > 0:
        return "STRONG", True, reasons
    return "OK", True, reasons


class Book:
    def __init__(self, con: sqlite3.Connection, name: str):
        self.con, self.name = con, name
        row = con.execute("SELECT json FROM books WHERE name=?", (name,)).fetchone()
        self.s = json.loads(row[0]) if row else {"cash": START, "units": {}, "costs": 0.0, "trades": 0}

    def save(self) -> None:
        self.con.execute("INSERT OR REPLACE INTO books VALUES (?,?)", (self.name, json.dumps(self.s)))

    def equity(self, px: dict[str, float]) -> float:
        return self.s["cash"] + sum(u * px.get(c, 0.0) for c, u in self.s["units"].items())

    def apply(self, targets: dict[str, float], px: dict[str, float], t: int) -> list[dict]:
        """Move to target values (in $) at prices px, paying NDAX market costs. Returns the fills."""
        fills = []
        for coin in sorted(set(targets) | set(self.s["units"])):
            if coin not in px:
                continue
            cur = self.s["units"].get(coin, 0.0) * px[coin]
            delta = targets.get(coin, 0.0) - cur
            if abs(delta) < 1.0:     # ignore dust (< $1)
                continue
            cost = abs(delta) * (FEE + HALF_SPREAD.get(coin, 0.004))
            self.s["cash"] -= delta + cost
            self.s["units"][coin] = (cur + delta) / px[coin]
            if self.s["units"][coin] * px[coin] < 1.0:
                self.s["units"].pop(coin)
            self.s["costs"] += cost
            self.s["trades"] += 1
            fills.append({"t": t, "book": self.name, "coin": coin, "side": "BUY" if delta > 0 else "SELL", "usd": round(abs(delta), 2),
                          "px": px[coin], "cost": round(cost, 4)})
        self.save()
        return fills


class PortfolioLayer:
    def __init__(self, base: Path | str = ".", db: str = "portfolio_book.sqlite"):
        self.base = Path(base)
        self.con = sqlite3.connect(str(self.base / db))
        self.con.executescript("""
            CREATE TABLE IF NOT EXISTS books (name TEXT PRIMARY KEY, json TEXT);
            CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
            CREATE TABLE IF NOT EXISTS decisions (day_t INTEGER PRIMARY KEY, json TEXT);
            CREATE TABLE IF NOT EXISTS proposals (id TEXT PRIMARY KEY, day_t INTEGER, status TEXT, json TEXT);
            CREATE TABLE IF NOT EXISTS fills (seq INTEGER PRIMARY KEY AUTOINCREMENT, t INTEGER, json TEXT);
        """)

    # -- settings --
    def _meta(self, k: str, default: str) -> str:
        r = self.con.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
        return r[0] if r else default

    @property
    def mode(self) -> str:
        return self._meta("mode", "SUGGEST")

    def set_mode(self, mode: str, by: str) -> None:
        mode = mode.upper()
        if mode not in ("SUGGEST", "AUTO"):
            raise ValueError("mode must be SUGGEST or AUTO")
        if not by.strip():
            raise ValueError("record who changed the mode")
        self.con.execute("INSERT OR REPLACE INTO meta VALUES ('mode', ?)", (mode,))
        self.con.execute("INSERT OR REPLACE INTO meta VALUES ('mode_changed', ?)", (json.dumps({"by": by, "at": _utc(time.time()), "mode": mode}),))
        self.con.commit()

    # -- the daily decision --
    def decide(self, views: dict[str, dict], px: dict[str, float], t_now: int, weekly: bool | None = None) -> dict:
        """Run once per new UTC daily close. views: coin -> daily_view(); px: coin -> current price (paper fills)."""
        views = {k: v for k, v in views.items() if v}
        if "BTC" not in views:
            return {"skip": "BTC daily view not ready"}
        day_t = int(views["BTC"]["day_close_t"])
        if self.con.execute("SELECT 1 FROM decisions WHERE day_t=?", (day_t,)).fetchone():
            return {"skip": "already decided for this day"}
        btc_on = views["BTC"]["close"] > views["BTC"]["ema50"]
        rets = sorted((v["ret30"], k) for k, v in views.items() if v["ret30"] is not None)
        rank = {k: (i / (len(rets) - 1) if len(rets) > 1 else 0.5) for i, (_, k) in enumerate(rets)}
        ratings = {}
        for coin, v in views.items():
            r, on, why = rate(coin, v, btc_on, rank.get(coin))
            ratings[coin] = {"rating": r, "hold": on, "why": why, "close": v["close"]}
        n = len(views)
        weekly = (datetime.fromtimestamp(day_t, timezone.utc).weekday() == 0) if weekly is None else weekly
        out = {"day": _utc(day_t), "rule": RULE, "mode": self.mode, "btc_gate": btc_on, "ratings": ratings, "proposals": [], "fills": []}
        for name in ("SHADOW", "MAIN"):
            book = Book(self.con, name)
            eq = book.equity(px)
            held = {c for c, u in book.s["units"].items() if u > 0}
            want = {c for c, r in ratings.items() if r["hold"]}
            targets = {c: eq / n for c in want}
            if not (weekly or held != want):
                continue
            if name == "SHADOW" or self.mode == "AUTO":
                out["fills"] += book.apply(targets, px, t_now)
            else:
                # SUGGEST: one proposal per change (ENTER / EXIT) + a rebalance proposal; nothing moves until approved
                for c in sorted(want - held):
                    out["proposals"].append(self._propose(day_t, "ENTER", c, n, ratings[c]["why"]))
                for c in sorted(held - want):
                    out["proposals"].append(self._propose(day_t, "EXIT", c, n, ratings[c]["why"]))
                if weekly and want and want == held:
                    out["proposals"].append(self._propose(day_t, "REBALANCE", "ALL", n, ["weekly reset to equal shares"]))
        # proposals from earlier days that were never approved expire: the rule has moved on
        self.con.execute("UPDATE proposals SET status='EXPIRED' WHERE status='PENDING' AND day_t < ?", (day_t,))
        for f in out["fills"]:
            self.con.execute("INSERT INTO fills (t, json) VALUES (?,?)", (f["t"], json.dumps(f)))
        self.con.execute("INSERT INTO decisions VALUES (?,?)", (day_t, json.dumps(out, default=str)))
        self.con.commit()
        return out

    def _propose(self, day_t: int, action: str, coin: str, n_slots: int, why: list[str]) -> dict:
        """Target size is decided at approval time: 1/n_slots of the MAIN book's equity then (0 for EXIT)."""
        p = {"id": f"P{day_t // 86400}-{action[:2]}-{coin}", "day_t": day_t, "action": action, "coin": coin,
             "n_slots": n_slots, "why": why}
        self.con.execute("INSERT OR REPLACE INTO proposals VALUES (?,?,?,?)", (p["id"], day_t, "PENDING", json.dumps(p)))
        return p

    def pending(self) -> list[dict]:
        return [json.loads(j) for (j,) in self.con.execute("SELECT json FROM proposals WHERE status='PENDING' ORDER BY id")]

    def approve(self, ids: list[str] | str, px: dict[str, float], t_now: int, by: str) -> list[dict]:
        """Operator approval (command today; the app's approve button later). Executes on the MAIN book at px."""
        if not by.strip():
            raise ValueError("record who approved")
        pend = {p["id"]: p for p in self.pending()}
        chosen = list(pend) if ids == "all" else [i for i in ids if i in pend]
        book = Book(self.con, "MAIN")
        eq = book.equity(px)
        fills = []
        for pid in chosen:
            p = pend[pid]
            slot = eq / max(1, p["n_slots"])
            targets = {c: u * px.get(c, 0.0) for c, u in book.s["units"].items()}
            if p["action"] == "REBALANCE":
                targets = {c: slot for c in targets}
            elif p["action"] == "ENTER":
                targets[p["coin"]] = slot
            else:
                targets[p["coin"]] = 0.0
            fills += book.apply(targets, px, t_now)
            self.con.execute("UPDATE proposals SET status=?, json=? WHERE id=?",
                             ("APPROVED", json.dumps({**p, "approved_by": by, "approved_at": _utc(t_now)}), pid))
        for f in fills:
            self.con.execute("INSERT INTO fills (t, json) VALUES (?,?)", (f["t"], json.dumps(f)))
        self.con.commit()
        return fills

    def reject(self, ids: list[str] | str, by: str) -> int:
        pend = [p["id"] for p in self.pending()]
        chosen = pend if ids == "all" else [i for i in ids if i in pend]
        for pid in chosen:
            self.con.execute("UPDATE proposals SET status='REJECTED' WHERE id=?", (pid,))
        self.con.commit()
        return len(chosen)

    def status(self, px: dict[str, float]) -> dict:
        last = self.con.execute("SELECT json FROM decisions ORDER BY day_t DESC LIMIT 1").fetchone()
        out = {"version": VERSION, "rule": RULE, "mode": self.mode, "evidence": EVIDENCE_CLASS, "books": {}, "pending": self.pending(),
               "last_decision": json.loads(last[0]) if last else None}
        for name in ("MAIN", "SHADOW"):
            b = Book(self.con, name)
            out["books"][name] = {"equity": round(b.equity(px), 2), "return_pct": round(100 * (b.equity(px) / START - 1), 2),
                                  "cash": round(b.s["cash"], 2), "costs": round(b.s["costs"], 2), "trades": b.s["trades"],
                                  "holdings": {c: round(u * px.get(c, 0), 2) for c, u in b.s["units"].items()}}
        return out
