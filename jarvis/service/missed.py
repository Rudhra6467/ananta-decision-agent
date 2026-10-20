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

Each CAUGHT row also records which books were in the move and whether each book is allowed to trade (Madhav, Oct 20: "score every
catch by its profit, and keep watches that only monitor separate from ones that trade"), with each holding's profit or loss,
realised or marked (score_catches). The P&L is recorded per row only: no summary shows a P&L total or average before
PNL_SHOWN_FROM (pre-registered review #38, forward window 21 Oct to 14 Dec); until then the summaries count catches only.

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
    # the catch's books and P&L (Oct 20). Added by ALTER only, after the older columns and in this order, so a table made fresh and a
    # table migrated in place have the same column order (the guest copy in app.py also copies by name).
    for c, typ in SCORE_COLS:
        if c not in cols:
            j.db.execute(f"ALTER TABLE missed_moves ADD COLUMN {c} {typ}")


SCORE_COLS = (("caught_books", "TEXT"), ("caught_allowed", "INTEGER"), ("caught_pnl_usd", "REAL"), ("caught_scored_t", "INTEGER"))
COLS = ("id", "day", "coin", "low_t", "high_t", "low", "high", "move_pct", "move_atr", "label", "saw", "kind", "at_zone", "regime", "pattern", "why", "tier",
        "miss_class") + tuple(c for c, _ in SCORE_COLS)
# Pre-registered review #38 (docs/research/REVIEW_38.md): forward window 2026-10-21 to 2026-12-14, one look after the 2026-12-15 close.
# Catch P&L is recorded per row from now on, but no summary, page, answer or review shows a P&L total or average before this UTC day.
REVIEW38_FROM, PNL_SHOWN_FROM = "2026-10-21", "2026-12-15"
# universe_watch.missed() (tier UNIV, dfb84fe) started writing its rows for the day on Oct 9; the old once-a-day guard took them for
# the live review's own and skipped it (silent-failure audit Oct 20, issue 2). backfill() re-runs the skipped days from here.
SKIP_SINCE = "2026-10-09"

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


def _done(j, day: str, tier: str) -> bool:
    """Has this tier's review of the day run? Its own rows or its own record only: another writer's rows for the same day (UNIV, from
    universe_watch.missed) say nothing about it. Before Oct 20 any row counted, so the live and 30-coin reviews were skipped on 9 of 11
    nights from Oct 9 (silent-failure audit, issue 2)."""
    if j.db.execute("SELECT 1 FROM missed_moves WHERE day=? AND coalesce(tier, 'LIVE10')=? LIMIT 1", (day, tier)).fetchone():
        return True
    return bool(j.db.execute("SELECT 1 FROM engine_state WHERE k=?", ((f"missed:{day}" if tier == "LIVE10" else f"missed_t30:{day}"),)).fetchone())


def run(j, day_t: int | None = None, log_request=None, force: bool = False) -> dict:
    """Review one closed day (default: yesterday UTC) once per tier, the live 10 and the 30-coin tier each guarded on its own rows and
    record (force: both again, replacing that day's rows of the same id)."""
    _table(j)
    now = int(j.now())
    day_t = day_t if day_t is not None else now - now % DAY - DAY
    day = _day_str(day_t)
    live_done = not force and _done(j, day, "LIVE10")
    t30_done = not force and _done(j, day, "T30")
    if live_done and t30_done:
        return {"day": day, "done_before": True}
    rows = []
    for m in ([] if live_done else moves(j, day_t)):
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
    n_live = len(rows)
    if not t30_done:
        try:
            t30 = run_t30(j, day_t)
            rows += t30
            st = {"moves": len(t30)}
        except Exception as exc:  # noqa: BLE001  the live review never fails because of the tier
            rows.append({"coin": "-", "move_pct": 0, "label": "ERROR", "why": f"30-coin tier review failed: {str(exc)[:120]}", "tier": "T30"})
            st = {"error": str(exc)[:160]}
        # every 30-coin day leaves a trace, so an empty day (no qualifying up-move) is visible and a failing one is not silent (Oct 8)
        j.db.execute("INSERT OR REPLACE INTO engine_state (k, v) VALUES (?,?)", (f"missed_t30:{day}", json.dumps(st)))
    if not live_done:
        j.db.execute("INSERT OR REPLACE INTO engine_state (k, v) VALUES (?,?)", (f"missed:{day}", str(n_live)))
    j.db.commit()
    try:
        scored = score_catches(j)
    except Exception as exc:  # noqa: BLE001  scoring is reporting: it never stops the review
        scored = {"error": str(exc)[:160]}
    flagged = _repeats(j, log_request)
    return {"day": day, "ran": [t for t, done in (("LIVE10", live_done), ("T30", t30_done)) if not done],
            "moves": [{k: r.get(k) for k in ("coin", "move_pct", "label", "why", "tier")} for r in rows], "flagged": flagged, "scored": scored}


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


# ---------------------------------------------------------------------------
# which book caught it, may that book trade, and what it made (Madhav, Oct 20). Reporting only: reads the books, writes missed_moves.
# ---------------------------------------------------------------------------
RANDOM_WATCHES = ("JARVIS_RANDOM",)
BOOK_HOME = {"explorer": "15-minute Explorer", "hunter": "Hourly watch", "t3_t30": "30-coin trend book"}


def _sid_of_watch(watch: str) -> str | None:
    from jarvis.service import strategy_status as SS

    if watch.startswith("RANDOM") or watch in RANDOM_WATCHES:
        return "RANDOM"
    e = SS.of_watch(watch)
    return e[0] if e else None


def _sid_of_book(key: str) -> str | None:
    from jarvis.service import strategy_status as SS

    e = SS.of_book(BOOK_HOME[key])
    return e[0] if e else None


def book_allowed(sid: str | None) -> tuple[bool, str | None]:
    """(allowed to trade, why not) for one strategy of the register (docs/knowledge/strategy_status.json, read, never changed).
    Monitor-only: verdict won't take again, a random baseline, a parked or retired book, or a book the register does not know. Whether a
    book wakes the brain does not decide it: allowed is whether its trades are real decisions (the bold book is allowed), matching
    review #38's frozen list of allowed books."""
    from jarvis.service import strategy_status as SS

    s = (SS.load().get("strategies") or {}).get(sid) if sid else None
    if s is None:
        return False, "not in the strategy register"
    if sid == "RANDOM":
        return False, "a random baseline"
    if s.get("verdict") == "wont_take_again":
        return False, "won't take again"
    if s.get("status") in ("PARKED", "RETIRED"):
        return False, f"{str(s.get('status')).lower()}: takes no new trades"
    return True, None


def _mark_price(j, coin: str, ex=None, cache: dict | None = None) -> float | None:
    """The coin's latest price for marking an open holding: the eye's live price, the Explorer's last 5-minute close, the universe
    feed's last price, else the last daily close we store."""
    cache = {} if cache is None else cache
    if coin in cache:
        return cache[coin]
    px = None
    try:
        from jarvis.service import eye

        px = (eye.STATE.get("prices") or {}).get(coin)
    except Exception:  # noqa: BLE001
        px = None
    if not px and ex is not None:
        try:
            e = ex.st["engines"].get(coin)
            px = e.tf["5m"].last[4] if e and e.tf["5m"].last else None
        except Exception:  # noqa: BLE001
            px = None
    if not px:
        p = Path(j.dir) / "universe_bars.sqlite"
        if p.exists():
            con = sqlite3.connect(f"file:{p}?mode=ro", uri=True, timeout=10)
            try:
                r = con.execute("SELECT price FROM px WHERE coin=?", (coin,)).fetchone() or con.execute(
                    "SELECT c FROM d1 WHERE coin=? ORDER BY t DESC LIMIT 1", (coin,)).fetchone()
                px = r[0] if r else None
            except sqlite3.Error:
                px = None
            finally:
                con.close()
    if not px:
        try:
            from jarvis.service.reads_watch import _daily

            D = _daily(j, coin)
            px = D[-1][4] if D else None
        except Exception:  # noqa: BLE001
            px = None
    cache[coin] = float(px) if px else None
    return cache[coin]


def _hold(book: str, sid: str | None, hid: str, entry_t, exit_t, pnl, kind: str | None) -> dict:
    ok, why = book_allowed(sid)
    return {"book": book, "sid": sid, "id": hid, "entry_t": entry_t, "exit_t": exit_t,
            "status": "NO_FILL" if kind is None and pnl is None and exit_t is None and entry_t is None else "OPEN" if exit_t is None else "CLOSED",
            "pnl_usd": None if pnl is None else round(float(pnl), 2), "pnl": kind, "allowed": ok, "monitor_why": why}


def _t3_spell(path: Path, coin: str, day_t: int, mark: float | None) -> dict | None:
    """The 30-coin trend book's holding of the coin that spans the day, from its MAIN fills at average cost: realised on what it sold,
    marked on what it still holds."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10)
    try:
        fills = [json.loads(x) for (x,) in con.execute("SELECT json FROM fills ORDER BY t, seq")]
    finally:
        con.close()
    spells, cur = [], None
    for f in fills:
        if f.get("book") != "MAIN" or f.get("coin") != coin or not f.get("px"):
            continue
        u, cost = f["usd"] / f["px"], f.get("cost") or 0.0
        if f["side"] == "BUY":
            if cur is None:
                cur = {"start": f["t"], "end": None, "units": 0.0, "basis": 0.0, "realised": 0.0}
                spells.append(cur)
            cur["units"] += u
            cur["basis"] += f["usd"] + cost
        elif cur is not None:
            sold = min(u, cur["units"])
            avg = cur["basis"] / cur["units"] if cur["units"] else 0.0
            cur["realised"] += f["usd"] - cost - avg * sold
            cur["basis"] -= avg * sold
            cur["units"] -= sold
            if cur["units"] * f["px"] < 1.0:                                # the book drops a holding under $1
                cur["end"], cur["units"], cur["basis"] = f["t"], 0.0, 0.0
                cur = None
    sp = next((x for x in reversed(spells) if x["start"] <= day_t + DAY and (x["end"] is None or x["end"] >= day_t)), None)
    if sp is None:
        return None
    hid = f"T3_T30:{coin}:{sp['start']}"
    if sp["end"] is not None:
        return {"id": hid, "entry_t": sp["start"], "exit_t": sp["end"], "pnl": sp["realised"], "kind": "realised"}
    if not mark:
        return {"id": hid, "entry_t": sp["start"], "exit_t": None, "pnl": None, "kind": None}
    return {"id": hid, "entry_t": sp["start"], "exit_t": None, "pnl": sp["realised"] + sp["units"] * mark - sp["basis"], "kind": "marked"}


def holdings(j, r: dict, ex=None, cache: dict | None = None) -> list[dict]:
    """Every book that was in a CAUGHT move, by the same windows that made it CAUGHT: the live 10 from 3 hours before the low to 2 hours
    after (an evidence trade not closed before the low); the 30-coin tier and the universe over the move's day."""
    tier, coin, low_t = r.get("tier") or "LIVE10", r["coin"], int(r.get("low_t") or 0)
    day_t = low_t - low_t % DAY
    a, b, frm = (low_t - BEFORE, low_t + AFTER, low_t) if tier == "LIVE10" else (day_t, day_t + DAY, day_t)
    out: dict = {}
    try:
        q = ("SELECT id, watch, coin, entry, entry_t, exit_t, net_usd FROM evidence_trades WHERE coin=? AND entry_t IS NOT NULL AND entry_t <= ? "
             "AND (exit_t IS NULL OR exit_t >= ?) AND watch NOT LIKE 'RANDOM%' AND watch != 'JARVIS_RANDOM'" + (" AND watch='H07-T30'" if tier == "T30" else ""))
        for tid, w, c, entry, et, xt, net in j.db.execute(q, (coin, b, frm)).fetchall():
            from jarvis.service import watch_engine

            if xt is not None and net is not None:
                pnl, kind = net, "realised"
            else:
                px = _mark_price(j, coin, ex, cache)
                pnl, kind = (watch_engine.net(coin, entry, px, w), "marked") if px and entry else (None, None)
            out[f"ev:{tid}"] = _hold("Jarvis" if w == "JARVIS" else w, _sid_of_watch(w), str(tid), et, xt if net is not None else None, pnl, kind)
    except sqlite3.Error:
        pass
    if tier == "LIVE10" and ex is not None:
        from src.intelligence import explorer_engine as xe

        sid = _sid_of_book("explorer")
        try:
            for tid, js, net, xt in ex.store.book.execute("SELECT id, json, net, exit_t FROM trades WHERE coin=? AND shadow=''", (coin,)).fetchall():
                x = json.loads(js)
                et = x.get("entry_t")
                if et is None or et > b or not (et >= a or xt is None or xt >= low_t):
                    continue
                out[f"ex:{tid}"] = _hold(f"Explorer {x.get('setup')}", sid, str(tid), et, xt, net, "realised" if net is not None else None)
        except Exception:  # noqa: BLE001
            pass
        try:
            for e in ex.st.get("engines", {}).values():
                for t in e.trades:
                    if t.coin != coin or t.shadow is not None or t.actual.done or not t.entry_t or t.entry_t > b or f"ex:{t.id}" in out:
                        continue
                    px = _mark_price(j, coin, ex, cache)
                    out[f"ex:{t.id}"] = _hold(f"Explorer {t.setup}", sid, str(t.id), t.entry_t, None,
                                              xe.NOTIONAL * (px / t.entry - 1) if px else None, "marked" if px else None)
        except Exception:  # noqa: BLE001
            pass
    try:
        traded = (json.loads(r.get("saw") or "{}").get("traded") or [])
    except (TypeError, ValueError):
        traded = []
    if tier == "T30" and any("trend book" in x for x in traded):
        p = Path(j.dir) / "portfolio_book_t30.sqlite"
        sp = _t3_spell(p, coin, day_t, _mark_price(j, coin, ex, cache)) if p.exists() else None
        sid = _sid_of_book("t3_t30")
        out[(sp or {}).get("id") or f"t3:{coin}"] = (_hold("30-coin trend book (T3-B)", sid, sp["id"], sp["entry_t"], sp["exit_t"], sp["pnl"], sp["kind"]) if sp
                                                    else _hold("30-coin trend book (T3-B)", sid, f"T3_T30:{coin}", None, None, None, None))
    # what made the row CAUGHT but holds no position we can price (a Hunter take, an Explorer order that never filled): named, no P&L
    for x in traded:
        if x.startswith("Hunter") and not any(h["sid"] == _sid_of_book("hunter") for h in out.values()):
            out["hunter"] = _hold("Hunter", _sid_of_book("hunter"), "hunter", None, None, None, None)
        elif x.startswith("Explorer") and not any(h["book"].startswith("Explorer") for h in out.values()):
            out["ex:order"] = _hold(x, _sid_of_book("explorer"), "explorer-order", None, None, None, None)
    return list(out.values())


def score_row(j, r: dict, ex=None, cache: dict | None = None) -> dict:
    """The four catch columns for one row (all None for a move that was not CAUGHT)."""
    if r.get("label") != "CAUGHT":
        return {c: None for c, _ in SCORE_COLS}
    hs = holdings(j, r, ex, cache)
    ok = [h for h in hs if h["allowed"] and h["pnl_usd"] is not None]
    return {"caught_books": json.dumps(hs), "caught_allowed": int(any(h["allowed"] for h in hs)),
            "caught_pnl_usd": round(sum(h["pnl_usd"] for h in ok), 2) if ok else None, "caught_scored_t": int(j.now())}


def score_catches(j, days: int = REPEAT_DAYS, remark_open: bool = True, since: str | None = None) -> dict:
    """Score every CAUGHT row of the last N days (all tiers) not scored yet, and mark open holdings again. Writes only the four catch
    columns of missed_moves, by name."""
    _table(j)
    since = since or _day_str(int(j.now()) - days * DAY)
    q = ("SELECT id, day, coin, low_t, tier, label, saw FROM missed_moves WHERE label='CAUGHT' AND day >= ? AND (caught_scored_t IS NULL"
         + (" OR caught_books LIKE '%\"status\": \"OPEN\"%')" if remark_open else ")"))
    rows = [dict(zip(("id", "day", "coin", "low_t", "tier", "label", "saw"), x)) for x in j.db.execute(q, (since,)).fetchall()]
    if not rows:
        return {"scored": 0}
    try:
        ex = j._explorer()
    except Exception:  # noqa: BLE001
        ex = None
    cache: dict = {}
    for r in rows:
        r["tier"] = r["tier"] or "LIVE10"
        sc = score_row(j, r, ex, cache)
        j.db.execute(f"UPDATE missed_moves SET {', '.join(c + '=?' for c, _ in SCORE_COLS)} WHERE id=?", (*(sc[c] for c, _ in SCORE_COLS), r["id"]))
    j.db.commit()
    return {"scored": len(rows)}


def pnl_visible(j) -> bool:
    """Catch P&L totals and averages are shown from PNL_SHOWN_FROM (UTC) on, never before (review #38's one look)."""
    return _day_str(int(j.now())) >= PNL_SHOWN_FROM


def _catch_split(rs: list[dict]) -> dict:
    c = [r for r in rs if r["label"] == "CAUGHT"]
    return {"CAUGHT_TRADE_OK": sum(1 for r in c if r.get("trade_ok") is True), "CAUGHT_MONITOR_ONLY": sum(1 for r in c if r.get("trade_ok") is False),
            "CAUGHT_UNSCORED": sum(1 for r in c if r.get("trade_ok") is None)}


def _catch_money(rs: list[dict]) -> dict:
    """P&L of the distinct catching trades (each counted once, however many moves it is in), allowed books and monitor-only apart.
    Only called once pnl_visible() is true."""
    by: dict = {True: {}, False: {}}
    for r in rs:
        for h in r.get("_books") or []:
            if h.get("pnl_usd") is not None:
                by[bool(h["allowed"])][f"{h['sid']}:{h['id']}"] = h
    out = {}
    for k, name in ((True, "allowed_to_trade"), (False, "monitor_only")):
        hs = list(by[k].values())
        tot = sum(h["pnl_usd"] for h in hs)
        out[name] = {"trades": len(hs), "pnl_usd": round(tot, 2), "avg_usd": round(tot / len(hs), 2) if hs else None,
                     "realised_usd": round(sum(h["pnl_usd"] for h in hs if h["pnl"] == "realised"), 2),
                     "marked_usd": round(sum(h["pnl_usd"] for h in hs if h["pnl"] == "marked"), 2)}
    return out


# ---------------------------------------------------------------------------
# the nights the live and 30-coin reviews were skipped (Oct 9 on): run them again, once, after the fix is deployed
# ---------------------------------------------------------------------------
def skipped_days(j, since: str = SKIP_SINCE, until: str | None = None) -> list[str]:
    """Closed UTC days from `since` to `until` (default: yesterday) whose live review never ran (no missed:<day> record)."""
    _table(j)
    now = int(j.now())
    t = int(datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    last = int(datetime.strptime(until, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()) if until else now - now % DAY - DAY
    out = []
    while t <= min(last, now - now % DAY - DAY):
        d = _day_str(t)
        if not j.db.execute("SELECT 1 FROM engine_state WHERE k=?", (f"missed:{d}",)).fetchone():
            out.append(d)
        t += DAY
    return out


def backfill(j, since: str = SKIP_SINCE, until: str | None = None, log_request=None) -> dict:
    """Re-run each skipped day's review (force=True), then score its catches. Writes missed_moves and engine_state of the live database:
    run it once, by hand, after the fix is deployed."""
    out = {}
    for d in skipped_days(j, since, until):
        t = int(datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
        r = run(j, t, log_request=log_request, force=True)
        out[d] = {"moves": len(r.get("moves") or []), "labels": [f"{m['tier']} {m['coin']} {m['label']}" for m in r.get("moves") or []]}
    out["_scored"] = score_catches(j, since=since)
    return out


def preview_backfill(agent_dir: str | Path, since: str = SKIP_SINCE, until: str | None = None) -> dict:
    """Dry run of backfill(): jarvis.sqlite is opened read-only (?mode=ro) and copied into memory, the review runs on the copy, and the
    rows it WOULD write are returned. Nothing on disk is written: every other file is opened read-only too, no request is filed.
    P&L is shown only for days before review #38's window (or once pnl_visible)."""
    import pickle
    import types

    from jarvis.service import tier30

    base = Path(agent_dir).expanduser()
    src = sqlite3.connect(f"file:{base / 'jarvis.sqlite'}?mode=ro", uri=True, timeout=30)
    mem = sqlite3.connect(":memory:", check_same_thread=False)
    src.backup(mem)
    src.close()
    ex = None
    if (base / "explorer_state.pkl").exists() and (base / "explorer_book.sqlite").exists():
        ex = types.SimpleNamespace(store=types.SimpleNamespace(book=sqlite3.connect(f"file:{base / 'explorer_book.sqlite'}?mode=ro", uri=True)),
                                   st=pickle.loads((base / "explorer_state.pkl").read_bytes()))
    j = types.SimpleNamespace(dir=base, db=mem, now=time.time, prices=lambda: {}, _explorer=lambda: ex)
    con0 = tier30._con
    tier30._con = lambda jj: sqlite3.connect(f"file:{Path(jj.dir) / 'tier30_bars.sqlite'}?mode=ro", uri=True, timeout=30)
    try:
        days = skipped_days(j, since, until)
        before = {r[0] for r in mem.execute("SELECT id FROM missed_moves")}
        res = backfill(j, since, until, log_request=lambda text: {"num": None})
        show = pnl_visible(j)
        cols = ("id", "day", "tier", "coin", "move_pct", "label", "miss_class", "caught_allowed", "caught_pnl_usd", "caught_books")
        rows = [dict(zip(cols, x)) for x in mem.execute(f"SELECT {', '.join(cols)} FROM missed_moves WHERE day IN ({','.join('?' * len(days))}) "
                                                        "ORDER BY day, tier, move_atr DESC", days)] if days else []
        new = [r for r in rows if r["id"] not in before]
        for r in new:
            r["_books"] = json.loads(r.pop("caught_books") or "[]")
            if not (show or r["day"] < REVIEW38_FROM):
                r.pop("caught_pnl_usd")
                for h in r["_books"]:
                    h.pop("pnl_usd", None)
        caught = [r for r in new if r["label"] == "CAUGHT"]
        ok = [r for r in caught if r["caught_allowed"] == 1]
        summary = {"days": days, "rows_would_write": len(new), "by_tier": {t: sum(1 for r in new if r["tier"] == t) for t in ("LIVE10", "T30")},
                   "labels": {k: sum(1 for r in new if r["label"] == k) for k in ("CAUGHT", "SEEN", "MISSED")},
                   "caught_by_book_allowed_to_trade": len(ok), "caught_only_by_monitor_only": len(caught) - len(ok)}
        old = [dict(zip(("id", "day", "tier", "coin", "caught_allowed", "caught_books"), x)) for x in mem.execute(
            "SELECT id, day, coalesce(tier, 'LIVE10'), coin, caught_allowed, caught_books FROM missed_moves WHERE label='CAUGHT' AND day >= ? "
            "ORDER BY day", (since,)) if x[0] not in {r["id"] for r in new}]
        for r in old:
            r["_books"] = json.loads(r.pop("caught_books") or "[]")
        summary["existing_catches_scored"] = {"rows": len(old), "by_tier": {t: sum(1 for r in old if r["tier"] == t) for t in ("UNIV", "LIVE10", "T30")},
                                              "caught_by_book_allowed_to_trade": sum(1 for r in old if r["caught_allowed"] == 1),
                                              "caught_only_by_monitor_only": sum(1 for r in old if r["caught_allowed"] == 0)}
        if show or all(d < REVIEW38_FROM for d in days + [r["day"] for r in old]):
            summary["money"] = _catch_money(new)
            summary["existing_catches_scored"]["money"] = _catch_money(old)
        return {"summary": summary, "rows": new, "existing": old, "run": res}
    finally:
        tier30._con = con0
        mem.close()


def patterns(j, days: int = REPEAT_DAYS, tier: str = "LIVE10") -> list[dict]:
    """The kinds of moves we keep missing (MISSED or only SEEN) in the last N days, most frequent first."""
    _table(j)
    since = _day_str(int(j.now()) - days * DAY)
    out = []
    for pat, n, days_n, avg, coins in j.db.execute("SELECT pattern, COUNT(*), COUNT(DISTINCT day), AVG(move_pct), GROUP_CONCAT(DISTINCT coin) FROM missed_moves "
                                                   "WHERE day >= ? AND label != 'CAUGHT' AND coalesce(tier, 'LIVE10') = ? AND coalesce(miss_class, 'DETECTION') IN ('DETECTION', 'KNOWLEDGE') "
                                                   "GROUP BY pattern ORDER BY 3 DESC",
                                                   (since, tier)):
        kind, zone, reg = pat.split("|")
        # "times" counts independent market days, not rows: coins missing together on one day are one event
        # (the GOAL_EVENTS rule; audit 2026-10-14 found request #38 filed on 10 rows that were 3 days).
        out.append({"pattern": pat, "times": days_n, "rows": n, "avg_move_pct": round(avg, 1), "coins": coins,
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
                f"Moves we keep missing: {p['said']} (on {p['times']} separate days in {REPEAT_DAYS} days, {p['rows']} coins in all, about +{p['avg_move_pct']}% each; {p['coins']}). "
                "Idea: a paper rule for this start, tested against the times the same start led nowhere (picked after the fact, so not proof).")
        r = (log_request or (lambda t: requests_log.add(j, "idea", t, "missed moves", by="ananta-auto")))(text)
        j.db.execute("INSERT OR REPLACE INTO engine_state (k, v) VALUES (?,?)", (key, str(r.get("num") if isinstance(r, dict) else "")))
        out.append({"pattern": p["pattern"], "request": r.get("num") if isinstance(r, dict) else None})
    j.db.commit()
    return out


def recent(j, days: int = 7) -> dict:
    """For the app, Ask and the evening review. A catch is split by who caught it: a book allowed to trade, or only a monitor-only watch.
    Before PNL_SHOWN_FROM this returns counts only, never a P&L (review #38); from that day, each move's catch P&L and the totals of the
    distinct catching trades (each trade once)."""
    _table(j)
    since = _day_str(int(j.now()) - days * DAY)
    backfill_classes(j)
    show = pnl_visible(j)
    rows = []
    for x in j.db.execute("SELECT day, coin, move_pct, move_atr, label, why, kind, at_zone, regime, low_t, coalesce(tier, 'LIVE10'), miss_class, "
                          "caught_allowed, caught_pnl_usd, caught_books FROM missed_moves WHERE day >= ? ORDER BY day DESC, move_atr DESC", (since,)):
        r = dict(zip(("day", "coin", "move_pct", "move_atr", "label", "why", "kind", "at_zone", "regime", "low_t", "tier", "miss_class"), x[:12]))
        r["trade_ok"] = None if x[12] is None else bool(x[12])
        if show:
            r["catch_pnl_usd"] = x[13]
            r["_books"] = json.loads(x[14] or "[]")
        rows.append(r)
    live = [r for r in rows if r["tier"] == "LIVE10"]
    t30 = [r for r in rows if r["tier"] == "T30"]
    univ = [r for r in rows if r["tier"] == "UNIV"]

    def counts(rs: list[dict]) -> dict:
        return {**{k: sum(1 for r in rs if r["label"] == k) for k in ("CAUGHT", "SEEN", "MISSED")}, **_catch_split(rs)}

    for r in rows:
        r["class_why"] = MISS_CLASSES.get(r["miss_class"] or "", "")
    classes = {k: sum(1 for r in rows if r["miss_class"] == k) for k in MISS_CLASSES}
    catches = {"all_tiers": _catch_split(rows),
               "meaning": "CAUGHT_TRADE_OK: a book allowed to trade was in the move; CAUGHT_MONITOR_ONLY: only watches that monitor were "
                          "(won't take again, random, parked or retired); CAUGHT_UNSCORED: not scored yet."}
    if show:
        catches["money"] = _catch_money(rows)
    else:
        catches["money"] = f"not shown before {PNL_SHOWN_FROM}: pre-registered review #38 looks once, after the 14 Dec close"
    for r in rows:
        r.pop("_books", None)
    return {"days": days, "counts": counts(live), "classes": classes, "class_meaning": MISS_CLASSES, "moves": live, "patterns": patterns(j),
            "catches": catches,
            "tier30": {"counts": counts(t30), "moves": t30, "patterns": patterns(j, tier="T30")},
            "universe": {"counts": counts(univ), "moves": univ[:25], "patterns": patterns(j, tier="UNIV"),
                         "meaning": "each day's biggest up-days across every tier A and B coin (at least 5% and one daily range), from the universe feed"},
            "how_to_read": "Each day's biggest rises (at least one daily range and 3%), and whether we were in them (caught: by a book allowed "
                           "to trade, or only by a watch that monitors), noticed them without trading (seen) or never looked (missed). "
                           "Patterns are picked after the fact: ideas to test, not proof."}
