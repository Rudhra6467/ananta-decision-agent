"""Execution realism (20 Oct 2026; Madhav graded execution realism D and asked what would make each area better). READ-ONLY REPORT.

Every paper fill of every book on an NDAX-listed coin is compared with an INDEPENDENT quote: the worker Mac's NDAX bid and ask for that
minute (pulled nightly into ~/ananta_worker_data), converted to USD with that day's USD/CAD where the book is priced in USD. The gate review
of 20 Oct found that the gate's engine_execution check cannot fail (the $500 book copies its fill price from the very quote it is checked
against), and that the other books never meet NDAX at all (they price from Binance candles plus a cost table). This report is the honest
version; it changes no reading, no rule and no cost.

  realism.report(j, since="2026-10-12")  per book: fills measured, fills with no worker quote, the share the book could really have had,
                                         the median and worst 'optimism' in basis points, and the cost the book charged against what NDAX
                                         would have charged at that minute

The test, per fill (NDAX fee 0.20% a side, as the books assume):
  achievable buy  = NDAX ask x (1 + fee)        the book's effective buy  = its price x (1 + the cost it charged itself)
  achievable sell = NDAX bid x (1 - fee)        the book's effective sell = its price x (1 - the cost it charged itself)
  optimism_bps    = how much better the book's effective price was than achievable (buy: (ach - eff) / ach; sell: (eff - ach) / ach) x 1e4
A fill is REALISTIC when optimism_bps <= TOLERANCE_BPS (5 bp covers the USD/CAD and Binance-vs-NDAX minute noise).
"""
from __future__ import annotations

import bisect
import calendar
import json
import sqlite3
import statistics
import time
from pathlib import Path

DEST = Path.home() / "ananta_worker_data"
DATA = Path.home() / "code" / "ananta-decision-agent"
NDAX_FEE = 0.0020
TOLERANCE_BPS = 5.0
MAX_QUOTE_GAP_S = 120


class Quotes:
    """The worker's NDAX minute quotes (CAD) and USD/CAD, loaded once per UTC day file."""

    def __init__(self, dest: Path | None = None):
        self.dest = dest or DEST
        self._days: dict[str, dict] = {}

    def _day(self, day: str) -> dict | None:
        if day in self._days:
            return self._days[day]
        f = self.dest / f"l1_{day}.sqlite"
        if not f.exists():
            self._days[day] = None
            return None
        con = sqlite3.connect(f"file:{f}?mode=ro", uri=True)
        try:
            q: dict[str, tuple[list[int], list[tuple[float, float]]]] = {}
            for t, c, b, a in con.execute("SELECT t, coin, bid, ask FROM ndax WHERE bid > 0 AND ask > 0 ORDER BY t"):
                ts, v = q.setdefault(c.upper(), ([], []))
                ts.append(int(t))
                v.append((float(b), float(a)))
            fx = [(int(t), float(u)) for t, u in con.execute("SELECT t, usdcad FROM fx WHERE usdcad > 0 ORDER BY t")]
        finally:
            con.close()
        self._days[day] = {"q": q, "fx": fx}
        return self._days[day]

    def at(self, coin: str, t: int) -> dict | None:
        """The NDAX quote nearest to t (within MAX_QUOTE_GAP_S) and the USD/CAD in force (the last before t that day, else the first)."""
        d = self._day(time.strftime("%Y-%m-%d", time.gmtime(t)))
        if not d or coin.upper() not in d["q"]:
            return None
        ts, v = d["q"][coin.upper()]
        i = bisect.bisect_left(ts, t)
        best = min((k for k in (i - 1, i) if 0 <= k < len(ts)), key=lambda k: abs(ts[k] - t), default=None)
        if best is None or abs(ts[best] - t) > MAX_QUOTE_GAP_S:
            return None
        fx = None
        if d["fx"]:
            k = bisect.bisect_right([x[0] for x in d["fx"]], t) - 1
            fx = d["fx"][max(k, 0)][1]
        bid, ask = v[best]
        return {"bid": bid, "ask": ask, "usdcad": fx, "lag_s": abs(ts[best] - t)}


def optimism_bps(side: str, eff_px: float, bid: float, ask: float, fee: float = NDAX_FEE) -> float:
    """How much better (bp) the book's effective price was than what NDAX offered after its fee; positive = too optimistic."""
    if side == "BUY":
        ach = ask * (1 + fee)
        return (ach - eff_px) / ach * 1e4
    ach = bid * (1 - fee)
    return (eff_px - ach) / ach * 1e4


def _fill(book: str, coin: str, side: str, t: int, eff_usd: float | None = None, eff_cad: float | None = None) -> dict:
    return {"book": book, "coin": coin.upper(), "side": side, "t": int(t), "eff_usd": eff_usd, "eff_cad": eff_cad}


def fills(j=None, since_t: int = 0, data: Path | None = None, cost_fn=None) -> list[dict]:
    """Every paper fill since since_t with its effective price (after the cost the book charged itself). Read-only."""
    data = data or DATA
    if cost_fn is None:
        from jarvis.service import registry

        cost_fn = registry.cost
    out: list[dict] = []
    jdb = data / "jarvis.sqlite"
    if jdb.exists():
        con = sqlite3.connect(f"file:{jdb}?mode=ro", uri=True)
        try:
            names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "book500_fills" in names:                                   # NDAX-priced in CAD; fee in CAD on the fill
                for t, coin, side, qty, px, fee in con.execute("SELECT t, coin, side, qty, px, fee FROM book500_fills WHERE t >= ?", (since_t,)):
                    per = (fee or 0.0) / qty if qty else 0.0
                    eff = px + per if side == "BUY" else px - per
                    out.append(_fill("BOOK500", coin, side, t, eff_cad=eff))
            if "evidence_trades" in names:                                 # USD from candles; the cost table charged on each side
                for watch, coin, et, entry, xt, xp in con.execute(
                        "SELECT watch, coin, entry_t, entry, exit_t, exit FROM evidence_trades WHERE entry_t >= ? AND entry > 0", (since_t,)):
                    c = cost_fn(coin)
                    out.append(_fill(watch, coin, "BUY", et, eff_usd=entry * (1 + c)))
                    if xt and xp:
                        out.append(_fill(watch, coin, "SELL", xt, eff_usd=xp * (1 - c)))
        finally:
            con.close()
    for f, book in ((data / "portfolio_book.sqlite", "T3"), (data / "portfolio_book_t30.sqlite", "T30")):
        if not f.exists():
            continue
        con = sqlite3.connect(f"file:{f}?mode=ro", uri=True)
        try:
            for t, js in con.execute("SELECT t, json FROM fills WHERE t >= ?", (since_t,)):
                r = json.loads(js)
                usd, px, cost = float(r.get("usd") or 0), float(r.get("px") or 0), float(r.get("cost") or 0)
                if px <= 0 or usd <= 0:
                    continue
                side = str(r.get("side", "")).upper()
                c = cost / usd
                sub = r.get("book") or "MAIN"
                out.append(_fill(book if sub == "MAIN" else f"{book}-{sub}", r.get("coin", ""), side, t,
                                 eff_usd=px * (1 + c) if side == "BUY" else px * (1 - c)))
        finally:
            con.close()
    return out


def score(fs: list[dict], quotes: Quotes) -> list[dict]:
    rows = []
    for f in fs:
        q = quotes.at(f["coin"], f["t"])
        if q is None:
            rows.append({**f, "measured": False})
            continue
        if f["eff_cad"] is not None:
            eff, bid, ask = f["eff_cad"], q["bid"], q["ask"]
        elif q["usdcad"]:
            eff, bid, ask = f["eff_usd"], q["bid"] / q["usdcad"], q["ask"] / q["usdcad"]
        else:
            rows.append({**f, "measured": False})
            continue
        o = optimism_bps(f["side"], eff, bid, ask)
        mid = (bid + ask) / 2
        rows.append({**f, "measured": True, "optimism_bps": round(o, 1), "realistic": o <= TOLERANCE_BPS,
                     "ndax_half_spread_pct": round(100 * (ask - bid) / 2 / mid, 3), "lag_s": q["lag_s"]})
    return rows


def report(j=None, since: str = "2026-10-12", dest: Path | None = None, data: Path | None = None, cost_fn=None) -> dict:
    since_t = calendar.timegm(time.strptime(since, "%Y-%m-%d"))
    rows = score(fills(j, since_t, data, cost_fn), Quotes(dest))
    books: dict[str, dict] = {}
    for r in rows:
        b = books.setdefault(r["book"], {"fills": 0, "measured": 0, "realistic": 0, "opt": []})
        b["fills"] += 1
        if r["measured"]:
            b["measured"] += 1
            b["realistic"] += int(r["realistic"])
            b["opt"].append(r["optimism_bps"])
    out = {}
    for k, b in sorted(books.items()):
        o = sorted(b.pop("opt"))
        out[k] = {**b, "no_quote": b["fills"] - b["measured"],
                  "realistic_share": round(b["realistic"] / b["measured"], 3) if b["measured"] else None,
                  "median_optimism_bps": round(statistics.median(o), 1) if o else None,
                  "worst_optimism_bps": o[-1] if o else None}
    m = [r for r in rows if r["measured"]]
    return {"since": since, "tolerance_bps": TOLERANCE_BPS, "fills": len(rows), "measured": len(m),
            "realistic": sum(r["realistic"] for r in m), "books": out,
            "worst": sorted(m, key=lambda r: -r["optimism_bps"])[:10],
            "line": (f"{sum(r['realistic'] for r in m)} of {len(m)} paper fills since {since} were achievable at NDAX's own quote that minute "
                     f"({len(rows) - len(m)} fills had no worker quote)") if m else f"no paper fill since {since} has a worker quote yet"}


if __name__ == "__main__":
    import sys

    r = report(since=sys.argv[1] if len(sys.argv) > 1 else "2026-10-12")
    print(r["line"])
    for k, b in r["books"].items():
        print(f"  {k:16s} fills {b['fills']:4d}  measured {b['measured']:4d}  realistic {b['realistic_share']}  median optimism {b['median_optimism_bps']} bp  worst {b['worst_optimism_bps']} bp")
