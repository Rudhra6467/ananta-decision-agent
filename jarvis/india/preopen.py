"""The 09:08 IST pre-open read (5 Nov 2026; Madhav: "yes to all", suggestion B of the trader review of his 10:44 chat: "you can start ... 30 minutes
before ... read the things ... and be ready for the market").

NSE's pre-open runs 09:00-09:08 IST: orders are collected and each stock's opening price is matched at 09:07-09:08. This is India's own first
price of the day. At 09:09 IST (com.ananta.india.preopen) this reads Zerodha's quotes for the two indexes and ten heavy stocks, and keeps them
in paper/preopen/<day>.json; the Ask's today block says it until the open settles.

9 Nov 2026 (Madhav: "yes, lets complete", the outsider readiness review's fix 1): the read is now sent to the phone, with the second look
(jarvis/india/recheck.py: what changed since the 08:30 view) and the row of the options line's own plan the indicated open points to. On 6 and
9 Nov the index quote at 09:09 matched the official open (to the rupee on the 6th), so it is the best sight of the gap before 09:15. A stock
half where every one of the ten equals its previous close (9 Nov) is said as not read, never as "0 higher, 0 lower".

Read only: nothing is placed.

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
    # 9 Nov 2026: all ten stocks came back equal to their previous close (0.0%) while the index quote had moved 0.4%; that is "no matched
    # price came through", not "0 of 10 higher, 0 lower"
    if ch and not any(x != 0.0 for x in ch):
        heavy = {"n": 0, "note": "the ten heavy stocks' quotes still showed their previous closes; no matched price came through"}
    else:
        heavy = {"n": len(ch), "up": sum(1 for x in ch if x > 0), "down": sum(1 for x in ch if x < 0),
                 "avg_pct": round(sum(ch) / len(ch), 2) if ch else None, "banks_avg_pct": round(sum(bk) / len(bk), 2) if bk else None}
    return {"day": now.date().isoformat(), "taken_at": now.isoformat(timespec="seconds"), "error": q.get("error"),
            "indexes": idx, "stocks": stocks, "index_moved": bool(moved), "heavy": heavy, "paper": True}


def second_look(d: dict, clk: dict | None = None, view: dict | None = None) -> dict:
    """Adds to the read what it means against the 08:30 view (recheck.at_preopen) and the row of the options line's plan it points to."""
    from jarvis.india import livesession, recheck
    ix = d.get("indexes") or {}
    indicated = {k: (ix.get(n) or {}).get("chg_pct") for k, n in (("NIFTY", "NIFTY 50"), ("BANKNIFTY", "NIFTY BANK")) if (ix.get(n) or {}).get("chg_pct") is not None}
    plan = None
    if d.get("index_moved") and indicated:
        try:
            plan = livesession.options_plan(clk or livesession.clock(None), indicated)
        except Exception:  # noqa: BLE001
            plan = None
    if view is None:
        try:
            from jarvis.india import views
            view = views._mv_latest()
        except Exception:  # noqa: BLE001
            view = None
    d["options_plan"] = {k: plan.get(k) for k in ("row", "short", "missing", "made_at")} if plan else None
    d["recheck"] = recheck.at_preopen(view, d, plan)
    return d


def push_words(d: dict) -> str | None:
    """The phone note: the indicated open, whether it changes the 08:30 view, and what the options line's plan says for that open."""
    ix = d.get("indexes") or {}
    n, b = (ix.get("NIFTY 50") or {}).get("chg_pct"), (ix.get("NIFTY BANK") or {}).get("chg_pct")
    if not d.get("index_moved") or n is None:
        return None
    s = f"Indicated open at {str(d.get('taken_at') or '')[11:16]} IST: Nifty {n:+.1f}%" + (f", Bank Nifty {b:+.1f}%" if b is not None else "") + ". "
    rc = d.get("recheck") or {}
    s += "This changes the 08:30 view. " if rc.get("changed") else "In line with the 08:30 view. "
    rows = (d.get("options_plan") or {}).get("row") or {}
    if rows:
        def short(c: str) -> str:
            return "no trade" if c == "no trade" else ("a short (put)" if c.startswith("a short") else "a long (call)")
        s += "Options line for that open: " + ", ".join(f"{ {'NIFTY': 'Nifty', 'BANKNIFTY': 'Bank Nifty'}[k] } {short(v['choice'])}" for k, v in rows.items()) + "."
    return s


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
    rc = (d.get("recheck") or {}).get("words")
    return (f"Pre-open read at {t} IST, before the 09:15 open: " + "; ".join(parts)
            + ". These are pre-open matched prices, an indication of the gap; the 09:15 open can differ, and nothing trades on them."
            + (f" Against the 08:30 morning view: {rc}" if rc else ""))


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


def opening_look(live: dict | None = None) -> dict | None:
    """The 10:20 IST second look (recheck.at_opening): the first hour against the pre-open, and the options line's own read of the 09:15 open
    against the pre-open's matched open. Kept in the day's file; None when there is nothing to compare."""
    from jarvis.india import livesession, recheck
    try:
        from jarvis.india import views
        view = views._mv_latest()
    except Exception:  # noqa: BLE001
        view = None
    day = dt.datetime.now(IST).date().isoformat()
    f = OUT / f"{day}.json"
    try:
        pre = json.loads(f.read_text())
    except (OSError, ValueError):
        pre = None
    live = live or livesession.today()
    rows = (live.get("index_now") or {}).get("rows") or {}
    d0 = [r for r in livesession._jsonl(DATA / "paper" / "sp1" / "decisions.jsonl") if r.get("date") == day and r.get("kind") == "decision" and r.get("point") == "D0"]
    out = recheck.at_opening(view, pre, rows, d0)
    if pre is not None and (out.get("points") or out.get("crosscheck")):
        pre["opening_look"] = out
        f.write_text(json.dumps(pre, indent=1))
    return out if out.get("points") or out.get("crosscheck") else None


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
    try:
        d = second_look(d)
    except Exception as exc:  # noqa: BLE001  the read itself still stands
        d["recheck"] = {"changed": False, "points": [], "words": None, "note": f"the second look could not run: {type(exc).__name__}"}
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / f"{d['day']}.json"
    already = False
    try:
        already = bool(json.loads(f.read_text()).get("pushed_at"))
    except (OSError, ValueError):
        pass
    note = push_words(d)
    if note and not already:              # one phone note a session
        try:
            from src.intelligence.paper_watch import push_phone
            print("push:", push_phone(f"Pre-open · {d['day'][5:]}", note[:300], level="EVENT"))
            d["pushed_at"] = dt.datetime.now(IST).isoformat(timespec="seconds")
        except Exception as exc:  # noqa: BLE001
            print(f"push skipped: {exc}")
    f.write_text(json.dumps(d, indent=1))
    print(f"{now:%F %T} IST: {words(d) or 'no prices came back: ' + str(d.get('error'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
