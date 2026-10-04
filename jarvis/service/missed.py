"""What did we miss today? (Madhav, 2026-10-04: "make sure the bot knows what it is missing and how to keep a track of good ones
next time").

Every day after the daily close (00:00 UTC), for the day that just closed:

  1. the day's biggest up-moves: per coin, the largest rise from a low to a later high on 15-minute candles, in daily ranges
     (ATR) so a 4% move in Bitcoin and a 4% move in Dogecoin are not treated the same; a move counts when it is at least one
     daily range and 3%; at most 5 a day.
  2. what we saw at its start (3 hours before the low to 2 hours after): the Explorer's sightings and orders (blocked ones
     too), Hunter's decisions, the eye's zone entries, the daily watches' evidence trades, and Jarvis's own decisions.
  3. a label: CAUGHT (a paper trade of ours was in it), SEEN (something noticed it but nothing traded) or MISSED (nothing
     looked), with why: the market regime, whether the low was at a support zone, and the kind of move (rebound from a recent
     low, breakout over the recent high, or a swing in between).
  4. the casebook (table missed_moves); the same kind of miss repeating (5 in 30 days) becomes a repair-shop request (an idea
     to test) and a pattern Jarvis's brain sees as knowledge with the status CANDIDATE.

Picked after the fact: a list of missed moves always looks like a strategy. A pattern only counts after it is traded forward on
paper (the brain) or tested in the repair shop against the times the same start led nowhere.
"""
from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

DAY = 86400
MIN_PCT, MIN_ATR, MAX_MOVES = 3.0, 1.0, 5
BEFORE, AFTER = 3 * 3600, 2 * 3600
REPEAT_N, REPEAT_DAYS = 5, 30
KIND_WORDS = {"rebound": "a rebound from a recent low", "breakout": "a breakout over the recent high", "swing": "a swing up in the middle of the range"}


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS missed_moves (id TEXT PRIMARY KEY, day TEXT, coin TEXT, low_t INTEGER, high_t INTEGER, low REAL, high REAL, "
                 "move_pct REAL, move_atr REAL, label TEXT, saw TEXT, kind TEXT, at_zone TEXT, regime TEXT, pattern TEXT, why TEXT)")
    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")


def _bars(j, coin: str, tf: str, t0: int, t1: int) -> list[tuple]:
    p = Path(j.dir) / "explorer_bars.sqlite"
    if not p.exists():
        return []
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)
    try:
        return [tuple(r) for r in con.execute("SELECT t, o, h, l, c, v FROM bars WHERE coin=? AND tf=? AND t >= ? AND t < ? ORDER BY t", (coin, tf, t0, t1))]
    finally:
        con.close()


def biggest_rise(B: list[tuple]) -> tuple[int, int] | None:
    """(index of the low bar, index of the later high bar) with the largest rise high/low."""
    best, lo_i, out = 0.0, None, None
    for k, b in enumerate(B):
        if lo_i is None or b[3] < B[lo_i][3]:
            lo_i = k
        r = b[2] / B[lo_i][3] - 1 if B[lo_i][3] else 0
        if r > best:
            best, out = r, (lo_i, k)
    return out


def moves(j, day_t: int) -> list[dict]:
    """The day's biggest up-moves (day_t = 00:00 UTC of the closed day)."""
    from jarvis.service.reads_watch import _daily
    from src.research import reads as R

    out = []
    for c in R.COINS:
        B = _bars(j, c, "15m", day_t, day_t + DAY)
        D = [d for d in _daily(j, c) if d[0] < day_t]
        if len(B) < 48 or len(D) < 30:
            continue
        atr = R.Series(D).atr[-1]
        br = biggest_rise(B)
        if not br or not atr:
            continue
        lo, hi = B[br[0]][3], B[br[1]][2]
        pct = 100 * (hi / lo - 1)
        k_atr = (hi - lo) / atr
        if pct >= MIN_PCT and k_atr >= MIN_ATR:
            out.append({"coin": c, "low_t": B[br[0]][0], "high_t": B[br[1]][0] + 900, "low": lo, "high": hi, "move_pct": round(pct, 2),
                        "move_atr": round(k_atr, 2), "D": D, "atr": atr})
    out.sort(key=lambda m: -m["move_atr"])
    return out[:MAX_MOVES]


def _hunter(j, coin: str, a: int, b: int) -> list[str]:
    p = Path(j.dir) / "agent_decisions.sqlite"
    if not p.exists():
        return []
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)
    try:
        fa = datetime.fromtimestamp(a, timezone.utc).isoformat()
        fb = datetime.fromtimestamp(b, timezone.utc).isoformat()
        return [f"Hunter {d.lower()} ({(s or '').split('.')[1] if s and '.' in s else s})" for d, s in
                con.execute("SELECT decision, setup FROM decisions WHERE instrument=? AND ts_utc >= ? AND ts_utc <= ? AND decision IN ('TAKE','SHADOW_PAPER')",
                            (coin, fa, fb))]
    except sqlite3.Error:
        return []
    finally:
        con.close()


def what_we_saw(j, coin: str, low_t: int) -> dict:
    """Everything of ours that noticed (or traded) the coin around the start of the move."""
    a, b = low_t - BEFORE, low_t + AFTER
    traded, saw = [], []
    try:
        ex = j._explorer()
    except Exception:  # noqa: BLE001
        ex = None
    if ex:
        for (js,) in ex.store.book.execute("SELECT json FROM events WHERE coin=? AND t >= ? AND t <= ? AND kind IN ('SIGHTING','ORDER','FILLED')", (coin, a, b)):
            e = json.loads(js)
            if e.get("shadow") == "RANDOM":
                continue
            if e["kind"] == "FILLED":
                traded.append(f"Explorer {e.get('setup')}")
            elif e["kind"] == "ORDER":
                (saw if e.get("shadow") else traded).append(f"Explorer {e.get('setup')}" + (f" order (blocked: {e['shadow'].lower().replace('_', ' ')})" if e.get("shadow") else " order"))
            else:
                saw.append(f"Explorer {e.get('setup')} sighting")
        for (js,) in ex.store.book.execute("SELECT json FROM trades WHERE coin=? AND shadow='' AND exit_t >= ?", (coin, low_t)):
            x = json.loads(js)
            if (x.get("entry_t") or 1e18) <= low_t:
                traded.append(f"Explorer {x.get('setup')} (already open)")
        for e in ex.st.get("engines", {}).values():
            for t in e.trades:
                if t.coin == coin and t.shadow is None and not t.actual.done and t.entry_t and t.entry_t <= low_t:
                    traded.append(f"Explorer {t.setup} (already open)")
    for h in _hunter(j, coin, a, b):
        (traded if "take" in h else saw).append(h)
    try:
        for (k, title) in j.db.execute("SELECT kind, title FROM eye_events WHERE coin=? AND t >= ? AND t <= ? AND kind IN ('ZONE_ENTRY','ZONE_TOUCH')",
                                       (coin, low_t - 6 * 3600, b)):
            saw.append("eye: " + title)
    except sqlite3.Error:
        pass
    try:
        for (w, et, xt) in j.db.execute("SELECT watch, entry_t, exit_t FROM evidence_trades WHERE coin=? AND watch NOT LIKE 'RANDOM%' AND watch != 'JARVIS_RANDOM' "
                                        "AND entry_t IS NOT NULL AND entry_t <= ? AND (exit_t IS NULL OR exit_t >= ?)", (coin, b, low_t)):
            traded.append(f"{'Jarvis' if w == 'JARVIS' else w} evidence trade")
    except sqlite3.Error:
        pass
    try:
        for (act, conf) in j.db.execute("SELECT action, confidence FROM brain_decisions WHERE coin=? AND t >= ? AND t <= ? AND action='PASS'", (coin, a, b)):
            saw.append(f"Jarvis passed (confidence {conf:.0f}%)")
    except sqlite3.Error:
        pass
    return {"traded": sorted(set(traded)), "saw": sorted(set(saw) - set(traded))}


def context(j, m: dict) -> dict:
    """Why it may have been missed: the market regime, a support zone at the low, the kind of move."""
    from jarvis.service import watch_engine
    from jarvis.service.reads_watch import _daily
    from src.research import reads as R
    from src.research import zones as Z

    D, atr = m["D"], m["atr"]
    btc = [d for d in _daily(j, "BTC") if d[0] < m["low_t"] - m["low_t"] % DAY]
    reg = watch_engine.regime_at(R.Series(btc), btc[-1][0]) if len(btc) >= 60 else None
    lo5, hi5 = min(d[3] for d in D[-5:]), max(d[2] for d in D[-5:])
    kind = "breakout" if m["high"] > hi5 else "rebound" if m["low"] <= lo5 + atr else "swing"
    zone = None
    if len(D) >= 260:
        try:
            for z in Z.live_zones(D)["zones"]:
                if z["bot"] - 0.5 * atr <= m["low"] <= z["top"] + 0.5 * atr:
                    zone = "+".join(z["kinds"]).lower()
                    break
        except Exception:  # noqa: BLE001
            pass
    return {"regime": reg, "kind": kind, "at_zone": zone}


def _day_str(t: int) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")


def run(j, day_t: int | None = None, log_request=None) -> dict:
    """Review one closed day (default: yesterday UTC) once."""
    _table(j)
    now = int(j.now())
    day_t = day_t if day_t is not None else now - now % DAY - DAY
    day = _day_str(day_t)
    if j.db.execute("SELECT 1 FROM missed_moves WHERE day=? LIMIT 1", (day,)).fetchone() or \
            j.db.execute("SELECT 1 FROM engine_state WHERE k=?", (f"missed:{day}",)).fetchone():
        return {"day": day, "done_before": True}
    rows = []
    for m in moves(j, day_t):
        w = what_we_saw(j, m["coin"], m["low_t"])
        cx = context(j, m)
        label = "CAUGHT" if w["traded"] else "SEEN" if w["saw"] else "MISSED"
        pattern = f"{cx['kind']}|{'zone' if cx['at_zone'] else 'no zone'}|{cx['regime'] or '?'}"
        why = ("in it: " + ", ".join(w["traded"]) if label == "CAUGHT" else
               "noticed by " + ", ".join(w["saw"][:3]) + ", but nothing traded" if label == "SEEN" else
               f"nothing of ours looked: {KIND_WORDS[cx['kind']]}, " + (f"from a {cx['at_zone']} zone" if cx["at_zone"] else "not at a support zone")
               + f", market {(cx['regime'] or 'unknown').lower().replace('_', '-')}")
        r = {"id": f"{day}:{m['coin']}", "day": day, "coin": m["coin"], "low_t": m["low_t"], "high_t": m["high_t"], "low": m["low"], "high": m["high"],
             "move_pct": m["move_pct"], "move_atr": m["move_atr"], "label": label, "saw": json.dumps(w), "kind": cx["kind"], "at_zone": cx["at_zone"],
             "regime": cx["regime"], "pattern": pattern, "why": why}
        j.db.execute("INSERT OR REPLACE INTO missed_moves VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", tuple(r.values()))
        rows.append(r)
    j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", (f"missed:{day}", str(len(rows))))
    j.db.commit()
    flagged = _repeats(j, log_request)
    return {"day": day, "moves": [{k: r[k] for k in ("coin", "move_pct", "label", "why")} for r in rows], "flagged": flagged}


def patterns(j, days: int = REPEAT_DAYS) -> list[dict]:
    """The kinds of moves we keep missing (MISSED or only SEEN) in the last N days, most frequent first."""
    _table(j)
    since = _day_str(int(j.now()) - days * DAY)
    out = []
    for pat, n, avg, coins in j.db.execute("SELECT pattern, COUNT(*), AVG(move_pct), GROUP_CONCAT(DISTINCT coin) FROM missed_moves "
                                           "WHERE day >= ? AND label != 'CAUGHT' GROUP BY pattern ORDER BY 2 DESC", (since,)):
        kind, zone, reg = pat.split("|")
        out.append({"pattern": pat, "times": n, "avg_move_pct": round(avg, 1), "coins": coins,
                    "said": f"{KIND_WORDS.get(kind, kind)}, {'from a support zone' if zone == 'zone' else 'away from any support zone'}, "
                            f"market {reg.lower().replace('_', '-')}", "status": "CANDIDATE (picked after the fact; needs forward paper evidence)"})
    return out


def _repeats(j, log_request=None) -> list[dict]:
    """A miss pattern reaching 5 in 30 days becomes one repair-shop request (once per pattern)."""
    from jarvis.service import requests_log

    out = []
    for p in patterns(j):
        if p["times"] < REPEAT_N:
            continue
        key = f"missed:flag:{p['pattern']}"
        if j.db.execute("SELECT 1 FROM engine_state WHERE k=?", (key,)).fetchone():
            continue
        text = (f"Moves we keep missing: {p['said']} ({p['times']} times in {REPEAT_DAYS} days, about +{p['avg_move_pct']}% each; {p['coins']}). "
                "Idea: a paper rule for this start, tested against the times the same start led nowhere (picked after the fact, so not proof).")
        r = (log_request or (lambda t: requests_log.add(j, "idea", t, "missed moves", by="ananta-auto")))(text)
        j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", (key, str(r.get("num") if isinstance(r, dict) else "")))
        out.append({"pattern": p["pattern"], "request": r.get("num") if isinstance(r, dict) else None})
    j.db.commit()
    return out


def recent(j, days: int = 7) -> dict:
    """For the app, Ask and the evening review."""
    _table(j)
    since = _day_str(int(j.now()) - days * DAY)
    rows = [dict(zip(("day", "coin", "move_pct", "move_atr", "label", "why", "kind", "at_zone", "regime", "low_t"), r)) for r in
            j.db.execute("SELECT day, coin, move_pct, move_atr, label, why, kind, at_zone, regime, low_t FROM missed_moves WHERE day >= ? ORDER BY day DESC, move_atr DESC",
                         (since,))]
    counts = {k: sum(1 for r in rows if r["label"] == k) for k in ("CAUGHT", "SEEN", "MISSED")}
    return {"days": days, "counts": counts, "moves": rows, "patterns": patterns(j),
            "how_to_read": "Each day's biggest rises (at least one daily range and 3%), and whether we were in them (caught), noticed them "
                           "without trading (seen) or never looked (missed). Patterns are picked after the fact: ideas to test, not proof."}
