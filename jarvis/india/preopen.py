"""The 09:08 IST pre-open read (5 Nov 2026; Madhav: "yes to all", suggestion B of the trader review of his 10:44 chat: "you can start ... 30 minutes
before ... read the things ... and be ready for the market").

NSE's pre-open runs 09:00-09:08 IST: orders are collected and each stock's opening price is matched at 09:07-09:08. Ananta has no GIFT Nifty and
no live Asian feed, but this is India's own first price of the day. At 09:09 IST (com.ananta.india.preopen) this reads Zerodha's quotes for the
two indexes and ten heavy stocks, and keeps them in paper/preopen/<day>.json; the Ask's today block says it until the open settles.

Whether Zerodha's index quote moves in the pre-open is not known yet; the file says what it saw ("index_moved"), and the heavy stocks' matched
prices are read either way. Read only: nothing is placed.

  python -m jarvis.india.preopen          take the read now (for the job)
  python -m jarvis.india.preopen show     print today's file
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

DATA = Path(os.getenv("ANANTA_INDIA_DATA", os.path.expanduser("~/ananta_data/india")))
OUT = DATA / "paper" / "preopen"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
INDEXES = {"NIFTY 50": "NSE:NIFTY 50", "NIFTY BANK": "NSE:NIFTY BANK"}
# the heaviest Nifty names; the first five banks also carry most of Bank Nifty
HEAVY = ["HDFCBANK", "ICICIBANK", "RELIANCE", "INFY", "BHARTIARTL", "TCS", "LT", "ITC", "SBIN", "AXISBANK"]
BANKS = {"HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK"}


def _pct(a, b):
    return round(100 * (a / b - 1), 2) if isinstance(a, (int, float)) and isinstance(b, (int, float)) and b else None


def read(fetch=None, now: dt.datetime | None = None) -> dict:
    from jarvis.india import livesession
    now = now or dt.datetime.now(IST)
    syms = list(INDEXES.values()) + [f"NSE:{s}" for s in HEAVY]
    q = livesession.quotes(syms, fetch)
    rows = q.get("rows") or {}
    idx = {}
    for name, sym in INDEXES.items():
        r = rows.get(sym) or {}
        idx[name] = {"last": r.get("last"), "prev_close": r.get("prev_close"), "chg_pct": _pct(r.get("last"), r.get("prev_close"))}
    stocks = {}
    for s in HEAVY:
        r = rows.get(f"NSE:{s}") or {}
        stocks[s] = {"last": r.get("last"), "prev_close": r.get("prev_close"), "chg_pct": _pct(r.get("last"), r.get("prev_close"))}
    ch = [v["chg_pct"] for v in stocks.values() if v["chg_pct"] is not None]
    bk = [stocks[s]["chg_pct"] for s in BANKS if stocks[s]["chg_pct"] is not None]
    moved = [v for v in idx.values() if v["chg_pct"] not in (None, 0.0)]
    return {"day": now.date().isoformat(), "taken_at": now.isoformat(timespec="seconds"), "error": q.get("error"),
            "indexes": idx, "stocks": stocks, "index_moved": bool(moved),
            "heavy": {"n": len(ch), "up": sum(1 for x in ch if x > 0), "down": sum(1 for x in ch if x < 0),
                      "avg_pct": round(sum(ch) / len(ch), 2) if ch else None, "banks_avg_pct": round(sum(bk) / len(bk), 2) if bk else None},
            "paper": True}


def words(d: dict | None) -> str | None:
    """The read in one plain sentence, or None when there is nothing to say."""
    if not d or d.get("error") and not d.get("heavy", {}).get("n"):
        return None
    t = str(d.get("taken_at") or "")[11:16]
    parts = []
    if d.get("index_moved"):
        for name, label in (("NIFTY 50", "Nifty"), ("NIFTY BANK", "Bank Nifty")):
            v = (d.get("indexes") or {}).get(name) or {}
            if v.get("chg_pct") is not None:
                parts.append(f"{label} indicated near {v['last']:,.0f} ({v['chg_pct']:+.1f}% on yesterday's close)")
    h = d.get("heavy") or {}
    if h.get("n"):
        parts.append(f"{h['up']} of {h['n']} heavy stocks indicated higher, {h['down']} lower, {h['avg_pct']:+.1f}% on average"
                     + (f" (the four big banks {h['banks_avg_pct']:+.1f}%)" if h.get("banks_avg_pct") is not None else ""))
    if not parts:
        return None
    return (f"Pre-open read at {t} IST, before the 09:15 open: " + "; ".join(parts)
            + ". These are pre-open matched prices, an indication of the gap; the 09:15 open can differ, and nothing trades on them.")


def today(clk: dict) -> dict | None:
    """Today's read for the Ask, from the pre-open until an hour after the open; None at other times or when there is no file."""
    if clk.get("state") not in ("pre_open", "open", "before_open") or dt.datetime.now(IST).strftime("%H:%M") > "10:30":
        return None
    p = OUT / f"{clk.get('today_india')}.json"
    try:
        d = json.loads(p.read_text())
    except (OSError, ValueError):
        return None
    w = words(d)
    return {**d, "words": w} if w else None


def main(argv: list[str]) -> int:
    if argv[:1] == ["show"]:
        p = OUT / f"{dt.datetime.now(IST).date().isoformat()}.json"
        print(p.read_text() if p.exists() else "no pre-open read today")
        return 0
    from jarvis.india import livesession
    now = dt.datetime.now(IST)
    if not livesession.is_session(now.date()):
        print(f"{now:%F %T} IST: no session today; no pre-open read")
        return 0
    d = read(now=now)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{d['day']}.json").write_text(json.dumps(d, indent=1))
    print(f"{now:%F %T} IST: {words(d) or 'no prices came back: ' + str(d.get('error'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
