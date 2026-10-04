"""Reviews (Madhav's OK, 2026-10-04): every closed trade gets a review into the casebook, and every evening Jarvis reviews its own day.

Trade reviews (review_closed): every closed paper trade of the Explorer, Hunter's book, the evidence books and Jarvis's own book
(random baselines excluded), once: how far it went for and against us while open (best and worst), what the price did in the
3 days after the exit, and plain lessons from fixed rules (no AI, free):
  STOPPED_THEN_RAN  stopped out, then the price rose 3%+ over the entry within 3 days (stop too tight, or entered early)
  GAVE_BACK         was up 3% or more at some point and still closed at a loss (no plan to protect a winner)
  NEVER_WORKED      never got 0.5% above the entry (the entry timing was poor)
  LEFT_ON_TABLE     a win, but the price went another 5%+ above the exit within 3 days (sold too early)
  COSTS_ATE         the price moved less than the round-trip costs (the trade could not pay)
  CLEAN             a win that kept at least half of its best move
Jarvis's own trades also show the plan written before the trade (thesis, confidence, knowledge used) next to what happened.

Evening review (evening): after 20:30 Toronto time, once a day: what Jarvis decided, what closed and the lessons, which big
moves we caught, saw or missed, any outages, and what it is watching tomorrow. Kept (daily_reviews), shown in the feed and Ask,
and a short phone note.
"""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Toronto")
AFTER_S = 3 * 86400
EVENING_HOUR, EVENING_MIN = 20, 30
TAG_WORDS = {"STOPPED_THEN_RAN": "stopped out, then it ran", "GAVE_BACK": "was up and gave it back", "NEVER_WORKED": "never worked",
             "LEFT_ON_TABLE": "sold too early", "COSTS_ATE": "too small to pay the costs", "CLEAN": "clean win"}


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS trade_reviews (id TEXT PRIMARY KEY, t INTEGER, book TEXT, watch TEXT, coin TEXT, entry_t INTEGER, exit_t INTEGER, "
                 "entry REAL, exit REAL, net_usd REAL, best_pct REAL, worst_pct REAL, after_pct REAL, tags TEXT, text TEXT, plan TEXT)")
    j.db.execute("CREATE TABLE IF NOT EXISTS daily_reviews (day TEXT PRIMARY KEY, t INTEGER, text TEXT, json TEXT)")


def _bars(j, coin: str, t0: int, t1: int) -> list[tuple]:
    p = Path(j.dir) / "explorer_bars.sqlite"
    if not p.exists():
        return []
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)
    try:
        for tf, step in (("15m", 900), ("1h", 3600), ("1d", 86400)):
            rows = con.execute("SELECT t, h, l, c FROM bars WHERE coin=? AND tf=? AND t >= ? AND t < ? ORDER BY t", (coin, tf, t0 - step, t1)).fetchall()
            first = con.execute("SELECT MIN(t) FROM bars WHERE coin=? AND tf=?", (coin, tf)).fetchone()[0]
            if rows and first is not None and first <= t0:
                return rows
        return []
    finally:
        con.close()


def lessons(entry: float, exit_px: float, net: float, best: float | None, worst: float | None, after: float | None, why: str, cost_pct: float) -> list[str]:
    tags = []
    move = 100 * (exit_px / entry - 1)
    stopped = "stop" in (why or "").lower()
    if stopped and after is not None and after >= 3:
        tags.append("STOPPED_THEN_RAN")
    if best is not None and best >= 3 and net < 0:
        tags.append("GAVE_BACK")
    if best is not None and best < 0.5:
        tags.append("NEVER_WORKED")
    if net > 0 and after is not None and exit_px and 100 * ((1 + after / 100) * entry / exit_px - 1) >= 5:
        tags.append("LEFT_ON_TABLE")
    if abs(move) < cost_pct and not tags:
        tags.append("COSTS_ATE")
    if net > 0 and best and move >= best / 2 and not tags:
        tags.append("CLEAN")
    return tags


def _closed_trades(j, since: int) -> list[dict]:
    """Every closed trade worth a review, from every book, in one shape."""
    out = []
    try:
        for (tid, w, coin, et, xt, en, xp, net, xw, src, dj) in j.db.execute(
                "SELECT id, watch, coin, entry_t, exit_t, entry, exit, net_usd, exit_why, source, detail FROM evidence_trades WHERE status='CLOSED' AND exit_t >= ? "
                "AND watch NOT LIKE 'RANDOM%' AND watch != 'JARVIS_RANDOM'", (since,)):
            d = json.loads(dj or "{}") if src == "brain" else {}
            out.append({"id": f"ev:{tid}", "book": "Jarvis" if w == "JARVIS" else "evidence", "watch": w, "coin": coin, "entry_t": et, "exit_t": xt,
                        "entry": en, "exit": xp, "net": net or 0.0, "why": xw or "",
                        "plan": {k: d.get(k) for k in ("thesis", "confidence", "size_pct", "knowledge", "stop0", "target", "trail_atr", "days")} if d else None})
    except sqlite3.Error:
        pass
    try:
        ex = j._explorer()
    except Exception:  # noqa: BLE001
        ex = None
    if ex:
        for (js,) in ex.store.book.execute("SELECT json FROM trades WHERE shadow='' AND exit_t >= ?", (since,)):
            x = json.loads(js)
            if x.get("ACTUAL_net") is None or not x.get("entry"):
                continue
            net = float(x["ACTUAL_net"])
            out.append({"id": f"ex:{x['id']}", "book": "Explorer", "watch": x.get("setup"), "coin": x["coin"], "entry_t": x.get("entry_t"),
                        "exit_t": x.get("ACTUAL_exit_t"), "entry": x["entry"], "exit": x["entry"] * (1 + net / 100 + 0.006), "net": net,   # exit about: net per $100 plus ~0.6% costs
                        "why": (x.get("ACTUAL_bell") or "").replace("_", " ").lower(), "plan": None,
                        "alt": {k[3:-4].lower().replace("_", "-"): x.get(k) for k in x if k.startswith("AS_") and k.endswith("_net") and x.get(k) is not None}})
    p = Path(j.dir) / "paper_book.sqlite"
    if p.exists():
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)
        try:
            for (js,) in con.execute("SELECT payload_json FROM positions WHERE status='CLOSED'"):
                d = json.loads(js)
                xt = (d.get("exit_bar_open_ms") or 0) / 1000 + 3600 if d.get("exit_bar_open_ms") else None
                if not xt or xt < since or not d.get("entry_fill"):
                    continue
                net = float(d.get("realized_pnl_usd") or 0)
                en = float(d["entry_fill"])
                out.append({"id": f"sd6:{d['id']}", "book": "Hunter", "watch": (d.get("core") or "").upper(), "coin": d.get("asset"),
                            "entry_t": int((d.get("entry_bar_close_ms") or 0) / 1000), "exit_t": int(xt), "entry": en,
                            "exit": en * (1 + net / float(d.get("notional_usd") or 100)), "net": net, "why": str(d.get("exit_reason") or d.get("exit_kind") or ""), "plan": None})
        except sqlite3.Error:
            pass
        finally:
            con.close()
    return out


def review_closed(j, days: int = 10) -> list[dict]:
    """Review every trade closed in the last N days that has no review yet (and whose 3 days after the exit have passed, or
    10 days at most)."""
    from src.research import reads as R

    _table(j)
    now = int(j.now())
    done = {r[0] for r in j.db.execute("SELECT id FROM trade_reviews")}
    out = []
    for x in _closed_trades(j, now - days * 86400):
        if x["id"] in done or not x.get("entry_t") or not x.get("exit_t"):
            continue
        if now < x["exit_t"] + AFTER_S:
            continue                                         # wait for the 3 days after the exit
        B = _bars(j, x["coin"], int(x["entry_t"]), int(x["exit_t"]) + AFTER_S)
        inside = [b for b in B if x["entry_t"] - 900 <= b[0] <= x["exit_t"]]
        later = [b for b in B if b[0] > x["exit_t"]]
        best = round(100 * (max(b[1] for b in inside) / x["entry"] - 1), 2) if inside else None
        worst = round(100 * (min(b[2] for b in inside) / x["entry"] - 1), 2) if inside else None
        after = round(100 * (max(b[1] for b in later) / x["entry"] - 1), 2) if later else None
        cost = 200 * R.cost(x["coin"])
        tags = lessons(x["entry"], x["exit"], x["net"], best, worst, after, x["why"], cost)
        txt = (f"{x['book']} {x['watch']} on {x['coin']}: {'+' if x['net'] >= 0 else '-'}${abs(x['net']):.2f}, closed by {x['why'] or 'its rule'}. "
               + (f"Best {best:+.1f}%, worst {worst:+.1f}% while open. " if best is not None else "")
               + (f"In the 3 days after: up to {after:+.1f}% over the entry. " if after is not None else "")
               + ("Lesson: " + "; ".join(TAG_WORDS[t] for t in tags) + "." if tags else ""))
        if x.get("alt"):
            alt = {k: v for k, v in x["alt"].items() if v is not None}
            if alt:
                k, v = max(alt.items(), key=lambda kv: kv[1])
                txt += f" As a {k} trade it would have made {'+' if v >= 0 else '-'}${abs(v):.2f}."
        if x.get("plan") and x["plan"].get("thesis"):
            pl = x["plan"]
            txt += (f" The plan before the trade: \"{pl['thesis'][:200]}\" (confidence {pl.get('confidence') or 0:.0f}%, size {pl.get('size_pct') or 0:.0f}%, "
                    f"knowledge {', '.join(pl.get('knowledge') or []) or 'none cited'}).")
        row = (x["id"], now, x["book"], x["watch"], x["coin"], int(x["entry_t"]), int(x["exit_t"]), x["entry"], x["exit"], x["net"], best, worst, after,
               json.dumps(tags), txt, json.dumps(x.get("plan")) if x.get("plan") else None)
        j.db.execute("INSERT OR REPLACE INTO trade_reviews VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
        out.append({"id": x["id"], "coin": x["coin"], "tags": tags})
    j.db.commit()
    return out


def recent_reviews(j, days: int = 7, book: str | None = None) -> dict:
    _table(j)
    q = "SELECT book, watch, coin, net_usd, tags, text, exit_t FROM trade_reviews WHERE exit_t >= ?" + (" AND book=?" if book else "") + " ORDER BY exit_t DESC LIMIT 40"
    rows = [dict(zip(("book", "watch", "coin", "net_usd", "tags", "text", "exit_t"), r)) for r in
            j.db.execute(q, (int(j.now()) - days * 86400, *((book,) if book else ())))]
    counts: dict[str, int] = {}
    for r in rows:
        r["tags"] = json.loads(r["tags"] or "[]")
        for t in r["tags"]:
            counts[TAG_WORDS[t]] = counts.get(TAG_WORDS[t], 0) + 1
    return {"reviews": rows, "lessons_count": counts,
            "how_to_read": "Every closed paper trade, reviewed 3 days after its exit: its best and worst while open, what came after, and "
                           "plain lessons from fixed rules. A lesson that keeps repeating in one book is a question for the repair shop."}


# ---------------------------------------------------------------------------
# the evening self-review
# ---------------------------------------------------------------------------
def _day0(j) -> int:
    return int(datetime.fromtimestamp(j.now(), TZ).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())


def build(j) -> dict:
    """Today's review as data plus the text."""
    from jarvis.service import brain, health, missed

    now, d0 = int(j.now()), _day0(j)
    day = datetime.fromtimestamp(now, TZ).strftime("%Y-%m-%d")
    out: dict = {"day": day}
    parts = []
    try:
        brain._table(j)
        dec = j.db.execute("SELECT coin, action, confidence, thesis FROM brain_decisions WHERE t >= ? AND action IN ('TAKE','PASS') ORDER BY t", (d0,)).fetchall()
        takes = [d for d in dec if d[1] == "TAKE"]
        out["decisions"] = {"take": len(takes), "pass": len(dec) - len(takes)}
        if dec:
            parts.append(f"I made {len(dec)} decision{'s' if len(dec) != 1 else ''}: {len(takes)} paper trade{'s' if len(takes) != 1 else ''}"
                         + (f" ({', '.join(f'{c} at {k:.0f}%' for c, _, k, _ in takes[:4])})" if takes else "") + f" and {len(dec) - len(takes)} pass{'es' if len(dec) - len(takes) != 1 else ''}.")
        else:
            parts.append("I made no trade decisions today.")
        rec = brain.record(j)
        if rec["closed"]:
            parts.append(f"My book so far: {rec['closed']} closed, average {rec['avg_usd_per_100']:+.2f} dollars per $100"
                         + (f" against {rec['random_twin_avg_usd']:+.2f} for the random twins." if rec.get("random_twin_avg_usd") is not None else "."))
    except Exception as exc:  # noqa: BLE001
        out["decisions_error"] = str(exc)[:120]
    try:
        closed = j.db.execute("SELECT watch, coin, net_usd FROM evidence_trades WHERE status='CLOSED' AND exit_t >= ? AND watch NOT LIKE 'RANDOM%' AND watch != 'JARVIS_RANDOM'",
                              (d0,)).fetchall()
        rv = recent_reviews(j, 1)
        out["closed"] = len(closed)
        if closed:
            tot = sum(n or 0 for _, _, n in closed)
            parts.append(f"{len(closed)} evidence trade{'s' if len(closed) != 1 else ''} closed, {'+' if tot >= 0 else '-'}${abs(tot):.2f} in total.")
        if rv["lessons_count"]:
            parts.append("Lessons from reviewed trades: " + ", ".join(f"{k} ({v})" for k, v in rv["lessons_count"].items()) + ".")
    except Exception as exc:  # noqa: BLE001
        out["closed_error"] = str(exc)[:120]
    try:
        m = missed.recent(j, 1)
        out["moves"] = m["counts"]
        if m["moves"]:
            c = m["counts"]
            top = next((x for x in m["moves"] if x["label"] == "MISSED"), m["moves"][0])
            parts.append(f"Yesterday's biggest moves: caught {c['CAUGHT']}, saw {c['SEEN']}, missed {c['MISSED']}. "
                         f"Biggest {top['label'].lower()}: {top['coin']} +{top['move_pct']:.1f}% ({top['why']}).")
        pats = [p for p in m["patterns"] if p["times"] >= 3]
        if pats:
            parts.append(f"A miss that keeps coming back: {pats[0]['said']} ({pats[0]['times']} times in 30 days).")
    except Exception as exc:  # noqa: BLE001
        out["moves_error"] = str(exc)[:120]
    try:
        outs = health.outages(j, d0)
        out["outages"] = len(outs)
        if outs:
            def _dur(o):
                return "still down" if not o["up_t"] else f"{(o['up_t'] - o['down_t']) / 60:.0f} min"

            parts.append("Outages today: " + ", ".join(f"{o['name']} ({_dur(o)})" for o in outs[:4]) + ".")
    except Exception as exc:  # noqa: BLE001
        out["health_error"] = str(exc)[:120]
    try:
        from jarvis.service import zones_watch

        hi = [r["coin"] for r in zones_watch.board(j).get("coins", []) if (r.get("attention") or {}).get("level") == "HIGH"]
        from jarvis.service import eye

        reg = (eye.STATE.get("armed") or {}).get("regime")
        parts.append((f"Market {reg.lower().replace('_', '-')}. " if reg else "") + (f"Tomorrow I'm watching {', '.join(hi[:4])} closely." if hi else "No coin is at a high-attention zone tonight."))
    except Exception:  # noqa: BLE001
        pass
    out["text"] = " ".join(parts)
    return out


def evening(j, push=None, force: bool = False) -> dict | None:
    """Once a day after 20:30 Toronto time."""
    _table(j)
    now = datetime.fromtimestamp(j.now(), TZ)
    day = now.strftime("%Y-%m-%d")
    if not force and ((now.hour, now.minute) < (EVENING_HOUR, EVENING_MIN) or j.db.execute("SELECT 1 FROM daily_reviews WHERE day=?", (day,)).fetchone()):
        return None
    r = build(j)
    j.db.execute("INSERT OR REPLACE INTO daily_reviews VALUES (?,?,?,?)", (day, int(j.now()), r["text"], json.dumps(r, default=str)))
    j.db.commit()
    if push:
        try:
            push("Jarvis: my day in review", r["text"][:480])
        except Exception:  # noqa: BLE001
            pass
    return r


def latest(j, n: int = 3) -> list[dict]:
    _table(j)
    return [{"day": d, "t": t, "text": tx} for d, t, tx in j.db.execute("SELECT day, t, text FROM daily_reviews ORDER BY day DESC LIMIT ?", (n,))]
