"""Candidate paper runner: forward paper for the frozen v2 trend-dip candidate.

Operator 2026-09-29: venue NDAX, "paper-trade it" = yes. Pre-registration: docs/research/CANDIDATE_V3.md.
The one-time holdout FAILED (docs/research/CANDIDATE_V3_HOLDOUT_RESULT.md); paper-forward proceeds as
approved, and that failure travels with this evidence.

Frozen rules (v2 S3_TREND_CONTROL | E_DIP | X_TRAIL | LONG):
  setup  : at a closed 4h bar, daily trend UP and 4h trend UP (close > EMA50 and EMA20 > EMA50)
  entry  : limit buy at 4h close - 0.5*ATR4h, resting 24h; skip if 3*ATR4h/limit < 3%
  exit   : stop 1.5A; once +1.5A, trail 2.5A from the best price; time stop 14 days
  size   : $100 per position, one per coin, $1000 book
Differences from the 5m replay (stated, not hidden): fills and exits are checked on closed 1h bars;
prices are Hands' Kraken USD candles standing in for NDAX CAD; NDAX costs are applied.

Laws: evidence class CANDIDATE_PAPER. exec=False, live=False, counts_for_m2=False. Never touches Hands
positions or Mongo. Starts FORWARD only: the first tick sets its clocks to now and back-trades nothing.
"""
from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Callable

VERSION = "candidate.trend_dip.paper.v1"
COINS = ["BTC", "ETH", "SOL", "ADA", "DOGE", "AVAX", "BCH", "LINK", "LTC", "XRP"]
H_MS, H4_MS, D_MS = 3_600_000, 14_400_000, 86_400_000
NOTIONAL = 100.0
STARTING = 1000.0
NDAX_FEE = 0.0020
HALF_SPREAD = {"BTC": 0.00178, "ETH": 0.00084, "SOL": 0.00289, "ADA": 0.00273, "DOGE": 0.00307,
               "AVAX": 0.00370, "BCH": 0.00400, "LINK": 0.00341, "LTC": 0.00334, "XRP": 0.00251}
_T, _O, _H, _L, _C, _V = 0, 1, 2, 3, 4, 5
BOOK = "candidate_book.sqlite"          # V0: frozen v2 trend-dip (failed holdout + fresh coins) -> wind-down
BOOK_V1 = "candidate_v1_book.sqlite"    # V1: same entry, trend-ride exit (passed fresh coins; fragile, see STUDY_V3_FRESH_RESULTS)
RULES = ("V0_TRAIL", "V1_RIDE")
EVIDENCE_NOTE = {
    "V0_TRAIL": "FAILED holdout (CANDIDATE_V3_HOLDOUT_RESULT.md) and fresh coins (STUDY_V3_FRESH_RESULTS.md); wind-down",
    "V1_RIDE": "PASSED fresh coins by the rules; fragile: -61% from a 2025-01-01 fresh start (STUDY_V3_FRESH_RESULTS.md)",
}


# ---------------------------------------------------------------------------
# Indicators: pure python, identical to the research versions (pandas ewm, adjust=False)
# ---------------------------------------------------------------------------
def ema(xs: list[float], span: int) -> list[float]:
    a = 2.0 / (span + 1)
    out: list[float] = []
    for x in xs:
        out.append(x if not out else a * x + (1 - a) * out[-1])
    return out


def atr(bars: list[list[float]], n: int = 14) -> list[float]:
    out: list[float] = []
    for i, b in enumerate(bars):
        pc = bars[i - 1][_C] if i else b[_C]
        tr = max(b[_H] - b[_L], abs(b[_H] - pc), abs(b[_L] - pc))
        out.append(tr if not out else out[-1] + (tr - out[-1]) / n)
    return out


def trend(closes: list[float]) -> int:
    if len(closes) < 50:
        return 99
    e20, e50 = ema(closes, 20)[-1], ema(closes, 50)[-1]
    c = closes[-1]
    return 1 if (c > e50 and e20 > e50) else (-1 if (c < e50 and e20 < e50) else 0)


def setup_at(bars4h: list[list[float]], bars1d: list[list[float]], k: int) -> dict | None:
    """Setup decision at closed 4h bar k (uses only bars closed at or before its close)."""
    if k < 60:
        return None
    tc = bars4h[k][_T] + H4_MS
    daily = [b for b in bars1d if b[_T] + D_MS <= tc]
    if len(daily) < 51 or tc - (daily[-1][_T] + D_MS) > 2 * D_MS:
        return None
    if trend([b[_C] for b in daily]) != 1 or trend([b[_C] for b in bars4h[: k + 1]]) != 1:
        return None
    A = atr(bars4h[: k + 1])[-1]
    L = bars4h[k][_C] - 0.5 * A
    if L <= 0 or 3.0 * A / L < 0.03:
        return None
    return {"setup_ms": tc, "limit": L, "A": A, "expires_ms": tc + 24 * H_MS}


# ---------------------------------------------------------------------------
# Book
# ---------------------------------------------------------------------------
class Book:
    def __init__(self, path: str | Path = BOOK):
        self.con = sqlite3.connect(str(path))
        self.con.executescript("""
        CREATE TABLE IF NOT EXISTS coin_state (coin TEXT PRIMARY KEY, json TEXT);
        CREATE TABLE IF NOT EXISTS trades (id TEXT PRIMARY KEY, coin TEXT, status TEXT, json TEXT);
        CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, coin TEXT, kind TEXT, json TEXT);
        """)

    def state(self, coin: str) -> dict | None:
        r = self.con.execute("SELECT json FROM coin_state WHERE coin=?", (coin,)).fetchone()
        return json.loads(r[0]) if r else None

    def put_state(self, coin: str, st: dict) -> None:
        self.con.execute("INSERT OR REPLACE INTO coin_state VALUES (?,?)", (coin, json.dumps(st)))

    def put_trade(self, t: dict) -> None:
        self.con.execute("INSERT OR REPLACE INTO trades VALUES (?,?,?,?)", (t["id"], t["coin"], t["status"], json.dumps(t)))

    def event(self, coin: str, kind: str, payload: dict) -> None:
        self.con.execute("INSERT INTO events (ts, coin, kind, json) VALUES (?,?,?,?)",
                         (time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), coin, kind, json.dumps(payload)))

    def trades(self) -> list[dict]:
        return [json.loads(r[0]) for r in self.con.execute("SELECT json FROM trades ORDER BY id")]

    def commit(self) -> None:
        self.con.commit()

    def close(self) -> None:
        self.con.commit()
        self.con.close()

    def ledger(self, evidence_note: str = "holdout FAIL (CANDIDATE_V3_HOLDOUT_RESULT.md)") -> dict[str, Any]:
        ts = self.trades()
        closed = [t for t in ts if t["status"] == "CLOSED"]
        open_ = [t for t in ts if t["status"] == "OPEN"]
        realized = sum(t.get("net_usd") or 0.0 for t in closed) - sum(t["entry_fee_usd"] for t in open_)
        return {"version": VERSION, "venue_costs": "NDAX", "starting": STARTING,
                "cash": round(STARTING + realized - NOTIONAL * len(open_), 4), "realized_usd": round(realized, 4),
                "open": [{"coin": t["coin"], "entry": t["entry"], "stop": t.get("stop")} for t in open_],
                "closed": len(closed), "wins": sum(1 for t in closed if t["net_usd"] > 0),
                "losses": sum(1 for t in closed if t["net_usd"] <= 0),
                "evidence_class": "CANDIDATE_PAPER", "prior_evidence": evidence_note,
                "exec": False, "live": False, "counts_for_m2": False}


# ---------------------------------------------------------------------------
# Engine: process closed bars forward
# ---------------------------------------------------------------------------
def _exit_check(pos: dict, bar: list[float], partial: bool) -> tuple[float, str] | None:
    """Trail exit on one closed 1h bar using the state known before the bar."""
    e, A = pos["entry"], pos["A"]
    s0 = e - 1.5 * A
    best_prev = pos["best"]
    stop = max(s0, best_prev - 2.5 * A) if best_prev >= e + 1.5 * A else s0
    pos["stop"] = stop
    if bar[_L] <= stop:
        return (stop if partial else min(stop, bar[_O])), "STOP_OR_TRAIL"
    pos["best"] = max(best_prev, max(e, bar[_C]) if partial else bar[_H])
    if bar[_T] + H_MS - pos["entry_ms"] >= 14 * D_MS:
        return bar[_C], "TIME_14D"
    return None


def _exit_check_ride(pos: dict, bar: list[float], partial: bool, dmap: dict) -> tuple[float, str] | None:
    """V1 ride exit on one closed 1h bar, identical to study_v3.sim_ride:
    daily close below the daily EMA20 (a daily close strictly after entry) -> exit at the next open;
    else stop 2.5*A4 (gap -> open); else 60-day time stop at the close."""
    e, A = pos["entry"], pos["A"]
    stop = e - 2.5 * A
    pos["stop"] = stop
    d = dmap.get(bar[_T])  # the daily bar that closed exactly at this hour's open
    if d is not None and bar[_T] > pos["entry_ms"] and not partial and d[0] < d[1]:
        return bar[_O], "DAILY_EMA20"
    if bar[_L] <= stop:
        return (stop if partial else min(stop, bar[_O])), "STOP"
    if bar[_T] + H_MS - pos["entry_ms"] >= 60 * D_MS:
        return bar[_C], "TIME_60D"
    return None


def _close(book: Book, coin: str, pos: dict, px: float, reason: str, bar_ms: float) -> dict:
    qty = pos["qty"]
    exit_fee = qty * px * (NDAX_FEE + HALF_SPREAD[coin])
    gross = qty * (px - pos["entry"])
    pos.update(status="CLOSED", exit=px, exit_reason=reason, exit_ms=bar_ms + H_MS,
               net_usd=round(gross - pos["entry_fee_usd"] - exit_fee, 6),
               net_pct=round((gross - pos["entry_fee_usd"] - exit_fee) / NOTIONAL * 100, 4),
               hold_h=round((bar_ms + H_MS - pos["entry_ms"]) / H_MS, 2))
    book.put_trade(pos)
    book.event(coin, "CLOSED", {k: pos[k] for k in ("id", "exit", "exit_reason", "net_usd", "hold_h")})
    return pos


def step_coin(book: Book, coin: str, bars1d: list, bars4h: list, bars1h: list, now_ms: float,
              rules: str = "V0_TRAIL", new_entries: bool = True) -> list[dict]:
    """Advance one coin through every newly closed 1h bar. Returns events for alerts.
    rules: V0_TRAIL (v2 trail exit) or V1_RIDE (trend-ride exit). new_entries=False: wind-down, no new setups."""
    if rules not in RULES:
        raise ValueError(f"unknown rules {rules!r}")
    ev: list[dict] = []
    dcl = [b[_C] for b in bars1d]
    de20 = ema(dcl, 20) if dcl else []
    dmap = {b[_T] + D_MS: (dcl[i], de20[i]) for i, b in enumerate(bars1d)}

    def exit_check(p, b, partial):
        return _exit_check_ride(p, b, partial, dmap) if rules == "V1_RIDE" else _exit_check(p, b, partial)

    st = book.state(coin)
    if not bars1h or not bars4h:
        return ev
    if st is None:  # forward only: start the clocks at the latest closed bars, trade nothing historical
        st = {"last_1h": bars1h[-1][_T], "last_4h": bars4h[-1][_T], "orders": [], "open_id": None, "started_ms": now_ms}
        book.put_state(coin, st)
        book.event(coin, "STARTED", {"from_1h": st["last_1h"], "from_4h": st["last_4h"]})
        return ev
    new_1h = [b for b in bars1h if b[_T] > st["last_1h"]]
    new_4h = [k for k, b in enumerate(bars4h) if b[_T] > st["last_4h"]]
    pos = None
    if st["open_id"]:
        r = book.con.execute("SELECT json FROM trades WHERE id=?", (st["open_id"],)).fetchone()
        pos = json.loads(r[0]) if r else None
    # timeline: 4h setups become active at their close; 1h bars are processed after any setup closed by their open
    for bar in new_1h:
        for k in [k for k in new_4h if bars4h[k][_T] + H4_MS <= bar[_T]]:
            new_4h.remove(k)
            st["last_4h"] = bars4h[k][_T]
            if pos is None and new_entries:
                s = setup_at(bars4h, bars1d, k)
                if s:
                    st["orders"].append(s)
                    book.event(coin, "ARMED", s)
                    ev.append({"kind": "ARMED", "coin": coin, "limit": s["limit"]})
        st["orders"] = [o for o in st["orders"] if bar[_T] < o["expires_ms"]]
        if pos is None and st["orders"]:
            o = st["orders"][0]  # oldest setup first, as in the replay
            if bar[_L] < o["limit"]:
                px = min(o["limit"], bar[_O])
                partial = not (bar[_O] < o["limit"])
                qty = NOTIONAL / px
                pos = {"id": f"cand.{coin}.{int(bar[_T])}.{uuid.uuid4().hex[:5]}", "coin": coin, "status": "OPEN",
                       "entry": px, "qty": qty, "A": o["A"], "best": px, "entry_ms": bar[_T], "setup_ms": o["setup_ms"],
                       "entry_fee_usd": round(qty * px * NDAX_FEE, 6), "evidence_class": "CANDIDATE_PAPER",
                       "exec": False, "live": False, "counts_for_m2": False, "version": VERSION, "rules": rules}
                st["orders"], st["open_id"] = [], pos["id"]
                book.put_trade(pos)
                book.event(coin, "FILLED", {"id": pos["id"], "entry": px})
                ev.append({"kind": "FILLED", "coin": coin, "entry": px})
                hit = exit_check(pos, bar, partial)
                if hit:
                    _close(book, coin, pos, hit[0], hit[1], bar[_T])
                    ev.append({"kind": "CLOSED", "coin": coin, "net_usd": pos["net_usd"], "reason": hit[1]})
                    pos, st["open_id"] = None, None
                else:
                    book.put_trade(pos)
                st["last_1h"] = bar[_T]
                continue
        if pos is not None:
            hit = exit_check(pos, bar, False)
            if hit:
                _close(book, coin, pos, hit[0], hit[1], bar[_T])
                ev.append({"kind": "CLOSED", "coin": coin, "net_usd": pos["net_usd"], "reason": hit[1]})
                pos, st["open_id"] = None, None
            else:
                book.put_trade(pos)
        st["last_1h"] = bar[_T]
    # 4h bars closed after the last processed hour still count as seen once their close has passed
    for k in new_4h:
        if bars4h[k][_T] + H4_MS <= (st["last_1h"] + H_MS):
            st["last_4h"] = bars4h[k][_T]
            if pos is None and new_entries:
                s = setup_at(bars4h, bars1d, k)
                if s:
                    st["orders"].append(s)
                    book.event(coin, "ARMED", s)
                    ev.append({"kind": "ARMED", "coin": coin, "limit": s["limit"]})
    book.put_state(coin, st)
    return ev


def fetch_http(asset: str, tf: str, limit: int) -> list[list[float]]:
    import requests

    from src.tools import ananta_api

    tok = ananta_api.login()
    r = requests.get(f"{ananta_api.BASE_URL}/api/market/candles", params={"symbol": f"{asset}/USD", "timeframe": tf, "limit": limit},
                     headers=ananta_api.get_headers(tok.get("token") if isinstance(tok, dict) else None), timeout=30)
    r.raise_for_status()
    return [[float(c["t"]), float(c["open"]), float(c["high"]), float(c["low"]), float(c["close"]), float(c["volume"])]
            for c in r.json().get("candles") or []]


def tick(*, fetch: Callable[[str, str, int], list] = fetch_http, now_ms: float | None = None,
         book_path: str | Path = BOOK, rules: str = "V0_TRAIL", new_entries: bool = True) -> dict[str, Any]:
    now_ms = now_ms if now_ms is not None else time.time() * 1000
    book = Book(book_path)
    out: dict[str, Any] = {"version": VERSION, "rules": rules, "new_entries": new_entries, "events": [], "errors": []}
    try:
        for coin in COINS:
            try:
                d = [b for b in fetch(coin, "1d", 200) if b[_T] + D_MS <= now_ms]
                h4 = [b for b in fetch(coin, "4h", 200) if b[_T] + H4_MS <= now_ms]
                h1 = [b for b in fetch(coin, "1h", 72) if b[_T] + H_MS <= now_ms]
                out["events"] += [{**e, "rules": rules} for e in step_coin(book, coin, d, h4, h1, now_ms, rules, new_entries)]
            except Exception as exc:  # noqa: BLE001  one coin failing never stops the others
                book.event(coin, "ERROR", {"error": str(exc)[:200]})
                out["errors"].append({"coin": coin, "error": str(exc)[:200]})
        out["ledger"] = book.ledger(EVIDENCE_NOTE[rules])
    finally:
        book.close()
    return out


def print_status(book_path: str | Path = BOOK, label: str = "V0_TRAIL (wind-down)") -> dict:
    b = Book(book_path)
    try:
        led = b.ledger(EVIDENCE_NOTE["V1_RIDE" if str(book_path).endswith(BOOK_V1) else "V0_TRAIL"])
        armed = {c: len((b.state(c) or {}).get("orders") or []) for c in COINS}
        closed = [t for t in b.trades() if t["status"] == "CLOSED"][-10:]
    finally:
        b.close()
    print(f"\nCANDIDATE PAPER  {label}  {VERSION}  (NDAX costs, $100/position, one per coin)")
    print("=" * 64)
    print(f"  cash={led['cash']:.2f} realized={led['realized_usd']:+.2f} open={len(led['open'])} closed={led['closed']} W/L={led['wins']}/{led['losses']}")
    print(f"  armed limit orders: {{{', '.join(f'{c}:{n}' for c, n in armed.items() if n)}}}")
    for t in led["open"]:
        print(f"  OPEN   {t['coin']:<5} entry={t['entry']:.6g} stop={t['stop']}")
    for t in closed:
        print(f"  CLOSED {t['coin']:<5} {t['exit_reason']:<14} net=${t['net_usd']:+.2f} hold={t['hold_h']}h")
    print(f"  evidence: {led['prior_evidence']}")
    print("  exec=False live=False m2=False")
    print("=" * 64)
    return led


if __name__ == "__main__":
    import sys

    if (sys.argv[1:] or ["status"])[0] == "status":
        print_status()
        print_status(BOOK_V1, "V1_RIDE")
    else:
        print(json.dumps(tick(), indent=1, default=str))
