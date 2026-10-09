"""What did we miss today? (Madhav, 2026-10-04: "make sure the bot knows what it is missing and how to keep a track of good ones
next time").

Every day after the daily close (00:00 UTC), for the day that just closed:

  1. the day's biggest up-moves: per coin, the largest rise from a low to a later high on 15-minute candles, in daily ranges
     (ATR) so a 4% move in Bitcoin and a 4% move in Dogecoin are not treated the same; a move counts when it is at least half
     a daily range and 3%; at most 5 a day.
  2. what we saw at its start (3 hours before the low to 2 hours after): the Explorer's sightings and orders (blocked ones
     too), Hunter's decisions, the eye's zone entries, the daily watches' evidence trades, and Jarvis's own decisions.
  3. a label: CAUGHT (a paper trade of ours was in it), SEEN (something noticed it but nothing traded) or MISSED (nothing
     looked), with why: the market regime, whether the low was at a support zone, and the kind of move (rebound from a recent
     low, breakout over the recent high, or a swing in between).
  4. the casebook (table missed_moves); the same kind of miss repeating (5 in 30 days) becomes a repair-shop request (an idea
     to test) and a pattern Jarvis's brain sees as knowledge with the status CANDIDATE.

The 30-coin paper tier (Madhav, request 11) is reviewed the same evening on its daily candles: each day's biggest up-days
(close over the previous close, at least 5% and one daily range, at most 5), CAUGHT when its trend book held the coin or a dip
trade was open, else SEEN with the trend book's own reason (it rates all 29 coins every day). Tier rows carry tier='T30' and
their patterns are counted separately from the live 10.

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
MIN_PCT, MIN_ATR, MAX_MOVES = 3.0, 0.5, 5
BEFORE, AFTER = 3 * 3600, 2 * 3600
REPEAT_N, REPEAT_DAYS = 5, 30
KIND_WORDS = {"rebound": "a rebound from a recent low", "breakout": "a breakout over the recent high", "swing": "a swing up in the middle of the range"}


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS missed_moves (id TEXT PRIMARY KEY, day TEXT, coin TEXT, low_t INTEGER, high_t INTEGER, low REAL, high REAL, "
                 "move_pct REAL, move_atr REAL, label TEXT, saw TEXT, kind TEXT, at_zone TEXT, regime TEXT, pattern TEXT, why TEXT)")
    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")
    cols = [r[1] for r in j.db.execute("PRAGMA table_info(missed_moves)")]
    if "tier" not in cols:
        j.db.execute("ALTER TABLE missed_moves ADD COLUMN tier TEXT DEFAULT 'LIVE10'")
    if "miss_class" not in cols:
        j.db.execute("ALTER TABLE missed_moves ADD COLUMN miss_class TEXT")


COLS = ("id", "day", "coin", "low_t", "high_t", "low", "high", "move_pct", "move_atr", "label", "saw", "kind", "at_zone", "regime", "pattern", "why", "tier",
        "miss_class")

# Miss classes (Madhav's acceptance framework, Oct 6): not every move we did not catch was a mistake. Decided by code, in this
# order (the first that fits); the class is also Jarvis's answer to "why didn't you buy?". Only DETECTION and KNOWLEDGE misses
# count toward a repeat pattern (5 in 30 days -> a repair-shop request).
MISS_CLASSES = {
    "DATA": "we could not see it: a part was down or the data was stale at the start of the move",
    "INTENTIONAL": "we saw it and a rule with supported evidence correctly said no (the market gate was shut)",
    "EXECUTION": "a trade was wanted but a limit or an unfilled order stopped it",
    "DECISION": "something noticed it and the decision was not to trade",
    "DETECTION": "nothing of ours recognised a kind of move our setups are meant to catch",
    "KNOWLEDGE": "a kind of move none of our setups covers",
}
REPEAT_CLASSES = ("DETECTION", "KNOWLEDGE")
WATCHED_PARTS = ("explorer", "hands_login", "eye", "hourly_watch", "candles", "jobs")


def _insert(j, r: dict) -> None:
    j.db.execute(f"INSERT OR REPLACE INTO missed_moves ({', '.join(COLS)}) VALUES ({', '.join('?' * len(COLS))})", tuple(r.get(c) for c in COLS))


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


def classify(j, label: str, saw: list[str], regime: str | None, kind: str | None, low_t: int | None, tier: str = "LIVE10") -> str | None:
    """The miss class of one move (None for a move we caught)."""
    if label == "CAUGHT":
        return None
    if low_t:
        try:
            q = ",".join("?" * len(WATCHED_PARTS))
            if j.db.execute(f"SELECT 1 FROM health_log WHERE part IN ({q}) AND down_t <= ? AND (up_t IS NULL OR up_t >= ?) LIMIT 1",
                            (*WATCHED_PARTS, low_t + AFTER, low_t - BEFORE)).fetchone():
                return "DATA"
        except sqlite3.Error:
            pass
    if (regime or "").upper() == "RISK_OFF":
        return "INTENTIONAL"
    if tier == "T30":
        return "DECISION" if label == "SEEN" else "DETECTION"
    low = " ".join(saw or []).lower()
    if any(w in low for w in ("rejected slot", "blocked: cap", "missed chase")):
        return "EXECUTION"
    if saw:
        return "DECISION"
    return "KNOWLEDGE" if kind == "swing" else "DETECTION"


def backfill_classes(j) -> int:
    """Class every move filed before classes existed (from what was stored with it)."""
    _table(j)
    n = 0
    for rid, label, saw, regime, kind, low_t, tier in j.db.execute(
            "SELECT id, label, saw, regime, kind, low_t, coalesce(tier, 'LIVE10') FROM missed_moves WHERE miss_class IS NULL AND label != 'CAUGHT'").fetchall():
        try:
            w = json.loads(saw or "{}")
        except (TypeError, ValueError):
            w = {}
        j.db.execute("UPDATE missed_moves SET miss_class=? WHERE id=?", (classify(j, label, w.get("saw") or [], regime, kind, low_t, tier), rid))
        n += 1
    j.db.commit()
    return n


def _day_str(t: int) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")


def run(j, day_t: int | None = None, log_request=None, force: bool = False) -> dict:
    """Review one closed day (default: yesterday UTC) once (force: again, replacing that day's rows)."""
    _table(j)
    now = int(j.now())
    day_t = day_t if day_t is not None else now - now % DAY - DAY
    day = _day_str(day_t)
    if not force and (j.db.execute("SELECT 1 FROM missed_moves WHERE day=? LIMIT 1", (day,)).fetchone() or
                      j.db.execute("SELECT 1 FROM engine_state WHERE k=?", (f"missed:{day}",)).fetchone()):
        return {"day": day, "done_before": True}
    rows = []
    for m in moves(j, day_t):
        w = what_we_saw(j, m["coin"], m["low_t"])
        cx = context(j, m)
        label = "CAUGHT" if w["traded"] else "SEEN" if w["saw"] else "MISSED"
        pattern = f"{cx['kind']}|{'zone' if cx['at_zone'] else 'no zone'}|{cx['regime'] or '?'}"
        why = ("in it: " + ", ".join(w["traded"]) if label == "CAUGHT" else
               "noticed by " + ", ".join(w["saw"][:3]) + ", but nothing traded" if label == "SEEN" else
               f"nothing of ours looked: {KIND_WORDS[cx['kind']]}, " + (f"starting at a support zone ({cx['at_zone'].replace('+', ' + ').replace('-', ' ')})" if cx["at_zone"] else "not at a support zone")
               + f", market {(cx['regime'] or 'unknown').lower().replace('_', '-')}")
        r = {"id": f"{day}:{m['coin']}", "day": day, "coin": m["coin"], "low_t": m["low_t"], "high_t": m["high_t"], "low": m["low"], "high": m["high"],
             "move_pct": m["move_pct"], "move_atr": m["move_atr"], "label": label, "saw": json.dumps(w), "kind": cx["kind"], "at_zone": cx["at_zone"],
             "regime": cx["regime"], "pattern": pattern, "why": why, "tier": "LIVE10",
             "miss_class": classify(j, label, w["saw"], cx["regime"], cx["kind"], m["low_t"])}
        _insert(j, r)
        rows.append(r)
    try:
        t30 = run_t30(j, day_t)
        rows += t30
        st = {"moves": len(t30)}
    except Exception as exc:  # noqa: BLE001  the live review never fails because of the tier
        rows.append({"coin": "-", "move_pct": 0, "label": "ERROR", "why": f"30-coin tier review failed: {str(exc)[:120]}", "tier": "T30"})
        st = {"error": str(exc)[:160]}
    # every 30-coin day leaves a trace, so an empty day (no qualifying up-move) is visible and a failing one is not silent (Oct 8)
    j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", (f"missed_t30:{day}", json.dumps(st)))
    j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", (f"missed:{day}", str(len(rows))))
    j.db.commit()
    flagged = _repeats(j, log_request)
    return {"day": day, "moves": [{k: r.get(k) for k in ("coin", "move_pct", "label", "why", "tier")} for r in rows], "flagged": flagged}


def run_t30(j, day_t: int) -> list[dict]:
    """The 30-coin tier's biggest up-days for the closed day day_t (daily candles), and whether its books were in them."""
    from jarvis.service import tier30, watch_engine
    from jarvis.service.reads_watch import _daily
    from src.research import reads as R
    from src.research import zones as Z

    day = _day_str(day_t)
    live = set(R.COINS)
    btc = [d for d in _daily(j, "BTC") if d[0] < day_t]
    reg = watch_engine.regime_at(R.Series(btc), btc[-1][0]) if len(btc) >= 60 else None
    p = Path(j.dir) / "portfolio_book_t30.sqlite"
    rating, held = {}, set()
    if p.exists():
        con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)
        try:
            row = con.execute("SELECT json FROM decisions WHERE day_t <= ? ORDER BY day_t DESC LIMIT 1", (day_t,)).fetchone()
        finally:
            con.close()
        if row:
            d = json.loads(row[0])
            rating = d.get("ratings") or {}
            held = {c for c, r in rating.items() if r.get("hold")}
    cands = []
    for c in tier30.COINS:
        if c in live:
            continue
        D = tier30.daily(j, c)
        k = next((i for i, b in enumerate(D) if b[0] == day_t), None)
        if k is None or k < 30:
            continue
        S = R.Series(D[:k])
        atr = S.atr[-1]
        prev, bar = D[k - 1], D[k]
        pct = 100 * (bar[4] / prev[4] - 1)
        if not atr or pct < 5 or (bar[4] - prev[4]) < atr:
            continue
        cands.append((pct, c, D[:k], bar, atr))
    out = []
    for pct, c, D, bar, atr in sorted(cands, reverse=True)[:MAX_MOVES]:
        h07 = j.db.execute("SELECT 1 FROM evidence_trades WHERE watch='H07-T30' AND coin=? AND entry_t IS NOT NULL AND entry_t <= ? "
                           "AND (exit_t IS NULL OR exit_t >= ?)", (c, day_t + DAY, day_t)).fetchone()
        traded = (["30-coin trend book (T3-B)"] if c in held else []) + (["H07-T30 dip trade"] if h07 else [])
        r = rating.get(c) or {}
        lo5, hi5 = min(x[3] for x in D[-5:]), max(x[2] for x in D[-5:])
        kind = "breakout" if bar[2] > hi5 else "rebound" if bar[3] <= lo5 + atr else "swing"
        zone = None
        if len(D) >= 260:
            try:
                for z in Z.live_zones(D)["zones"]:
                    if z["bot"] - 0.5 * atr <= bar[3] <= z["top"] + 0.5 * atr:
                        zone = "+".join(z["kinds"]).lower()
                        break
            except Exception:  # noqa: BLE001
                pass
        label = "CAUGHT" if traded else "SEEN" if r else "MISSED"
        why = ("30-coin tier, in it: " + ", ".join(traded) if traded else
               f"30-coin tier: the trend book rated it {r.get('rating')} ({'; '.join((r.get('why') or [])[:2])})" if r else
               "30-coin tier: not running yet that day (started Oct 4)")
        row = {"id": f"{day}:T30:{c}", "day": day, "coin": c, "low_t": day_t, "high_t": day_t + DAY, "low": bar[3], "high": bar[2],
               "move_pct": round(pct, 2), "move_atr": round((bar[4] - D[-1][4]) / atr, 2), "label": label,
               "saw": json.dumps({"traded": traded, "saw": [f"T3-B rated {r.get('rating')}"] if r and not traded else []}),
               "kind": kind, "at_zone": zone, "regime": reg, "pattern": f"{kind}|{'zone' if zone else 'no zone'}|{reg or '?'}", "why": why, "tier": "T30",
               "miss_class": classify(j, label, [], reg, kind, day_t, "T30")}
        _insert(j, row)
        out.append(row)
    j.db.commit()
    return out


def patterns(j, days: int = REPEAT_DAYS, tier: str = "LIVE10") -> list[dict]:
    """The kinds of moves we keep missing (MISSED or only SEEN) in the last N days, most frequent first."""
    _table(j)
    since = _day_str(int(j.now()) - days * DAY)
    out = []
    for pat, n, avg, coins in j.db.execute("SELECT pattern, COUNT(*), AVG(move_pct), GROUP_CONCAT(DISTINCT coin) FROM missed_moves "
                                           "WHERE day >= ? AND label != 'CAUGHT' AND coalesce(tier, 'LIVE10') = ? AND coalesce(miss_class, 'DETECTION') IN ('DETECTION', 'KNOWLEDGE') "
                                           "GROUP BY pattern ORDER BY 2 DESC",
                                           (since, tier)):
        kind, zone, reg = pat.split("|")
        out.append({"pattern": pat, "times": n, "avg_move_pct": round(avg, 1), "coins": coins,
                    "said": f"{KIND_WORDS.get(kind, kind)}, {'from a support zone' if zone == 'zone' else 'away from any support zone'}, "
                            f"market {reg.lower().replace('_', '-')}", "status": "CANDIDATE (picked after the fact; needs forward paper evidence)"})
    return out


def _repeats(j, log_request=None) -> list[dict]:
    """A miss pattern reaching 5 in 30 days becomes one repair-shop request (once per pattern)."""
    from jarvis.service import requests_log

    out = []
    for tier in ("LIVE10", "T30", "UNIV"):
        out += _repeats_tier(j, tier, log_request)
    j.db.commit()
    return out


def _repeats_tier(j, tier: str, log_request=None) -> list[dict]:
    from jarvis.service import requests_log

    out = []
    for p in patterns(j, tier=tier):
        if p["times"] < REPEAT_N:
            continue
        key = f"missed:flag:{p['pattern']}" + ("" if tier == "LIVE10" else f":{tier}")
        if j.db.execute("SELECT 1 FROM engine_state WHERE k=?", (key,)).fetchone():
            continue
        text = ({"T30": "30-coin tier: ", "UNIV": "Whole universe (tier A and B coins): "}.get(tier, "") +
                f"Moves we keep missing: {p['said']} ({p['times']} times in {REPEAT_DAYS} days, about +{p['avg_move_pct']}% each; {p['coins']}). "
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
    backfill_classes(j)
    rows = [dict(zip(("day", "coin", "move_pct", "move_atr", "label", "why", "kind", "at_zone", "regime", "low_t", "tier", "miss_class"), r)) for r in
            j.db.execute("SELECT day, coin, move_pct, move_atr, label, why, kind, at_zone, regime, low_t, coalesce(tier, 'LIVE10'), miss_class FROM missed_moves "
                         "WHERE day >= ? ORDER BY day DESC, move_atr DESC", (since,))]
    live = [r for r in rows if r["tier"] == "LIVE10"]
    counts = {k: sum(1 for r in live if r["label"] == k) for k in ("CAUGHT", "SEEN", "MISSED")}
    t30 = [r for r in rows if r["tier"] == "T30"]
    for r in rows:
        r["class_why"] = MISS_CLASSES.get(r["miss_class"] or "", "")
    classes = {k: sum(1 for r in rows if r["miss_class"] == k) for k in MISS_CLASSES}
    return {"days": days, "counts": counts, "classes": classes, "class_meaning": MISS_CLASSES, "moves": live, "patterns": patterns(j),
            "tier30": {"counts": {k: sum(1 for r in t30 if r["label"] == k) for k in ("CAUGHT", "SEEN", "MISSED")}, "moves": t30,
                       "patterns": patterns(j, tier="T30")},
            "universe": {"counts": {k: sum(1 for r in rows if r["tier"] == "UNIV" and r["label"] == k) for k in ("CAUGHT", "SEEN", "MISSED")},
                         "moves": [r for r in rows if r["tier"] == "UNIV"][:25], "patterns": patterns(j, tier="UNIV"),
                         "meaning": "each day's biggest up-days across every tier A and B coin (at least 5% and one daily range), from the universe feed"},
            "how_to_read": "Each day's biggest rises (at least one daily range and 3%), and whether we were in them (caught), noticed them "
                           "without trading (seen) or never looked (missed). Patterns are picked after the fact: ideas to test, not proof."}
