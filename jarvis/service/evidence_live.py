"""The Evidence page, live: inside the logic repair (Madhav, 2026-10-05: "redesign our evidence page based on these questions ...
it will be like seeing it live what's happening inside the logic repair").

His questions, in his order, each answered with live counts. Every section is best-effort: one failing never hides the rest.

  loop      the repair loop in one strip: looked -> spotted -> decided -> scored -> misses checked -> sent to the repair shop
            -> changed
  clocks    what is watching, how often, and how many looks so far
  limits    every gate that stops a trade: how often it stopped one, and what the stopped trades went on to do
  results   is anything working: average per $100 paper trade after costs against random entries, counted in market events
  rebuild   reconstruction: the nightly rebuild of our own decisions (and the ones Madhav asked for), and the study of other
            traders with what came of it
  misses    each day's biggest moves: caught, seen or missed, and the patterns on their way to the repair shop (5 in 30 days)
  board     the repair board: everything forwarded (tickets, Madhav's requests, reviews, questions waiting for evidence) with
            what was found, what was done, the change and the status
  in_use    what changed because of the evidence
  waiting   what we wait for, how fast it is coming, and when it should be there at this pace

record_rebuild(j) keeps every rebuild result (explorer_reconstruct.json is overwritten each time); the 15-minute jobs call it.
summary(j) is the same in short, for Ask.
"""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

DAY = 86400
GOAL_EVENTS = 10                         # the scoreboard's bar: no verdict before 10 independent market events
BOARD_ORDER = ("WAITING_FOR_YOU", "IN_PROGRESS", "OPEN", "PLANNED", "WAITING_FOR_EVIDENCE", "DONE", "WONT")
BOARD_WORDS = {"WAITING_FOR_YOU": "Waiting for you", "IN_PROGRESS": "In progress", "OPEN": "Open", "PLANNED": "Planned",
               "WAITING_FOR_EVIDENCE": "Waiting for evidence", "DONE": "Done", "WONT": "Closed, no change"}
BOARD_GROUP = {"WAITING_FOR_YOU": "you", "IN_PROGRESS": "us", "OPEN": "us", "PLANNED": "us", "WAITING_FOR_EVIDENCE": "evidence",
               "DONE": "done", "WONT": "done"}
SPEEDUP = {
    "closed_trades": "Trades are plenty; separate market moves are the wait. Everything closing on the same day counts once, so a "
                     "busy day does not help; more days with moves do.",
    "weekly_rebalances": "Set by the calendar: one rebalance a week, by design.",
    "t30_weeks": "Set by the calendar: one check a week, by design.",
    "e5_trades": "E5 trades only on the 10 live coins, so at this pace it takes weeks.",
    "setup_fires": "Your setups are rare by design (a capitulation, a retest after a drop); nothing to speed up without changing the rule.",
    "h07_fires": "Rare by design (a shaken market); the 30-coin tier's H07 watches 29 more coins and is counted apart.",
    "stable_positive_sightings": "Waits for the market to reach a context the atlas marks positive after costs in both periods.",
}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _local(t: float | None) -> str | None:
    from jarvis.service.views import _local as L

    return L(t) if t else None


def _day(t: float | None) -> str | None:
    if not t:
        return None
    try:
        from zoneinfo import ZoneInfo

        return datetime.fromtimestamp(t, ZoneInfo("America/Toronto")).strftime("%b %d").replace(" 0", " ")
    except Exception:  # noqa: BLE001
        return datetime.fromtimestamp(t, timezone.utc).strftime("%b %d")


def _date_t(s: str | None) -> float:
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
    except (TypeError, ValueError):
        return 0.0


def _usd(x: float | None) -> str:
    return "–" if x is None else f"{'+' if x >= 0 else '-'}${abs(x):.2f}"


def _one(j, sql: str, args: tuple = (), default: Any = 0) -> Any:
    try:
        r = j.db.execute(sql, args).fetchone()
        return r[0] if r and r[0] is not None else default
    except Exception:  # noqa: BLE001  the table appears with its first row
        return default


def _try(fn: Callable[[], Any], out: dict, key: str) -> Any:
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001  one section failing never hides the rest
        out.setdefault("errors", {})[key] = f"{type(exc).__name__}: {str(exc)[:160]}"
        return None


def _s(n: int | None, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


# ---------------------------------------------------------------------------
# the rebuild log (kept from 2026-10-05; the nights before were seeded from the Explorer's alert log)
# ---------------------------------------------------------------------------
def _rebuild_table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS rebuild_log (t INTEGER PRIMARY KEY, source TEXT, match INTEGER, logged INTEGER, "
                 "rebuilt INTEGER, only_live INTEGER, only_rebuilt INTEGER, detail TEXT)")


def record_rebuild(j) -> dict | None:
    """One row per new rebuild file: nightly (at the daily close) or asked for through Ananta (a research job)."""
    _rebuild_table(j)
    p = Path(j.dir) / "explorer_reconstruct.json"
    if not p.exists():
        return None
    t = int(p.stat().st_mtime)
    if j.db.execute("SELECT 1 FROM rebuild_log WHERE t=?", (t,)).fetchone():
        return None
    try:
        r = json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    asked = _one(j, "SELECT COUNT(*) FROM jobs WHERE kind='reconstruction' AND abs(coalesce(done_t, t) - ?) <= 120", (t,))
    src = "asked" if asked else "nightly"
    j.db.execute("INSERT INTO rebuild_log VALUES (?,?,?,?,?,?,?,?)",
                 (t, src, int(bool(r.get("match"))), r.get("logged_real_events"), r.get("rebuilt_real_events"),
                  len(r.get("only_in_live") or []), len(r.get("only_in_rebuilt") or []), json.dumps(r, default=str)[:4000]))
    j.db.commit()
    return {"t": t, "source": src, "match": bool(r.get("match"))}


# ---------------------------------------------------------------------------
# the page
# ---------------------------------------------------------------------------
def build(j) -> dict:
    from jarvis.service import views

    now = j.now()
    out: dict[str, Any] = {"as_of": _local(now)}
    ex = _try(lambda: j._explorer(), out, "explorer")
    L = _try(lambda: views._ledger(j), out, "ledger") or {}
    P = (_try(lambda: views.evidence_pipeline(j), out, "pipeline") if ex else None) or {}
    rows = (_try(lambda: views._outcomes(ex), out, "outcomes") if ex else None) or []
    out["days"] = P.get("days")
    out["rules"] = P.get("rules")
    out["since"] = _day(ex.st.get("trade_from_t")) if ex else None
    for key, fn in (("health", lambda: _health(j)),
                    ("clocks", lambda: _clocks(j, P, ex)),
                    ("limits", lambda: _limits(j, P, rows, L, ex)),
                    ("results", lambda: _results(j, P, rows)),
                    ("rebuild", lambda: _rebuild(j, L)),
                    ("misses", lambda: _misses(j)),
                    ("board", lambda: _board(j, L, P)),
                    ("in_use", lambda: _in_use(L, P)),
                    ("waiting", lambda: _waiting(j, P, ex)),
                    ("daily_review", lambda: _daily_review())):
        out[key] = _try(fn, out, key)
    out["loop"] = _try(lambda: _loop(j, out, P, rows), out, "loop")
    out["gate"] = _try(lambda: _gate(j, out), out, "gate")
    out["headline"] = _try(lambda: _headline(out), out, "headline")
    return out


def _daily_review() -> dict | None:
    """The morning review (step 0.6 of the build plan): a scheduled run works the repair board and writes one page per day to
    docs/repair_shop/daily/YYYY-MM-DD.md. The Evidence page shows the newest one."""
    d = Path(__file__).resolve().parents[2] / "docs" / "repair_shop" / "daily"
    files = sorted(d.glob("????-??-??.md")) if d.exists() else []
    if not files:
        return None
    text = files[-1].read_text()
    return {"day": files[-1].stem, "text": text[:6000], "count": len(files)}


def _health(j) -> dict:
    from jarvis.service import health

    h = health.status(j)
    parts = h["parts"]
    return {"ok": sum(1 for p in parts.values() if p["ok"]), "of": len(parts), "down": h["down"], "summary": h["summary"],
            "checked_s_ago": h["last_check_s_ago"],
            "outages_3d": [{"name": o["name"], "minutes": o["minutes"], "from": _local(o["down_t"]), "still_down": not o["up_t"]}
                           for o in h["outages_3d"][:6]]}


def _wake_moves(j) -> dict[str, list[float]]:
    """What each brain wake's coin did in the next 24 hours (1-hour closes), by the wake's fate (status check, Oct 8: the 6-hour
    cooldown had dropped 398 wakes and nobody knew what they would have done)."""
    ex = j._explorer()
    if not ex:
        return {}
    closes: dict[str, dict[int, float]] = {}
    for c, eng in ex.st["engines"].items():
        closes[c] = {int(b[0]) // 3600: b[4] for b in eng.tf["1h"].bars}
    out: dict[str, list[float]] = {}
    for t, coin, state in j.db.execute("SELECT t, coin, state FROM brain_queue"):
        h = closes.get(coin) or {}
        a, b = h.get(int(t) // 3600), h.get(int(t) // 3600 + 24)
        if a and b:
            k = "DONE" if state == "DONE" else state.split(":", 1)[-1].strip()
            out.setdefault(k, []).append(100 * (b / a - 1))
    return out


def _t30_days(j) -> dict:
    """30-coin missed-move review: days run, days with no qualifying up-move, days that failed (from Oct 8 on each day leaves a trace)."""
    st = {k[11:]: json.loads(v) for k, v in j.db.execute("SELECT k, v FROM engine_state WHERE k LIKE 'missed_t30:%'")}
    return {"reviewed": len(st), "empty": sum(1 for v in st.values() if v.get("moves") == 0),
            "failed": sorted(k for k, v in st.items() if v.get("error")),
            "note": "A day counts only when a coin closed at least 5% up and more than its normal daily range; Oct 6 to 8 every tier coin fell."}


def _move_summary(xs: list[float]) -> dict | None:
    if len(xs) < 3:
        return None
    return {"n": len(xs), "avg_pct": round(sum(xs) / len(xs), 2), "up_pct": round(100 * sum(1 for x in xs if x > 0) / len(xs))}


def _clocks(j, P: dict, ex) -> list[dict]:
    from jarvis.service import eye, health, views

    days = P.get("days") or 0
    seen = sum(s["seen"] for s in P.get("seen") or [])
    D = P.get("decided") or {}
    hb = views._jsonl(Path(j.dir) / "watch_heartbeat.jsonl", 5000)
    hs = views._hourly_strategies(j)
    hun, sq = hs.get("hunter", {}), hs.get("squeeze", {})
    t30_days = t30_hold = 0
    p30 = Path(j.dir) / "portfolio_book_t30.sqlite"
    if p30.exists():
        con = sqlite3.connect(f"file:{p30}?mode=ro", uri=True, timeout=10)
        try:
            t30_days = con.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
            last = con.execute("SELECT json FROM decisions ORDER BY day_t DESC LIMIT 1").fetchone()
            if last:
                t30_hold = sum(1 for r in (json.loads(last[0]).get("ratings") or {}).values() if r.get("hold"))
        finally:
            con.close()
    t3_days = _try(lambda: j._layer().con.execute("SELECT COUNT(*) FROM decisions").fetchone()[0], {}, "t3") or 0
    wakes = _one(j, "SELECT COUNT(*) FROM brain_queue")
    decided = _one(j, "SELECT COUNT(*) FROM brain_decisions WHERE action != 'ERROR'")
    dropped = _one(j, "SELECT COUNT(*) FROM brain_queue WHERE state LIKE 'DROPPED%'")
    daily_sig = _one(j, "SELECT COUNT(*) FROM evidence_trades WHERE source='daily' AND watch NOT LIKE 'RANDOM%' AND watch != 'H07-T30'")
    daily_rnd = _one(j, "SELECT COUNT(*) FROM evidence_trades WHERE source='daily' AND watch LIKE 'RANDOM%'")
    h07_30 = _one(j, "SELECT COUNT(*) FROM evidence_trades WHERE watch='H07-T30'")
    zone_touch = _one(j, "SELECT COUNT(*) FROM evidence_trades WHERE watch='ZONE_TOUCH'")
    missed_days = _one(j, "SELECT COUNT(*) FROM engine_state WHERE k LIKE 'missed:____-__-__'")
    _rebuild_table(j)
    nights = _one(j, "SELECT COUNT(*) FROM rebuild_log WHERE source LIKE 'nightly%'")
    ticks = eye.STATE.get("ticks") if eye.STATE.get("running") else None
    uni: list[dict] = []
    try:                                                   # engine plan U2-U5: the whole universe, beside the 10
        from jarvis.service import registry, universe_explorer, universe_watch

        cnt = registry.load(j).get("counts") or {}
        u_sig = _one(j, "SELECT COUNT(*) FROM evidence_trades WHERE watch LIKE '%-U_' AND watch NOT LIKE 'RANDOM%' AND watch NOT LIKE 'ZONE_TOUCH%'")
        u_rnd = _one(j, "SELECT COUNT(*) FROM evidence_trades WHERE watch LIKE 'RANDOM%-U_'")
        u_zt = _one(j, "SELECT COUNT(*) FROM evidence_trades WHERE watch LIKE 'ZONE_TOUCH-U_'")
        u_rb = len(universe_watch.rebuilds(j, 1000))
        unrev = _one(j, "SELECT COUNT(*) FROM brain_unreviewed") if j.db.execute(
            "SELECT 1 FROM sqlite_master WHERE name='brain_unreviewed'").fetchone() else 0
        ux = (universe_explorer.STATE.get("last") or {})
        scope = f"{cnt.get('listed', 0)} coins"
        uni = [
            {"cadence": "10 s / 5 min", "name": "Universe feed", "scope": scope, "n": cnt.get("listed"), "unit": "coins",
             "detail": f"Every coin's price every 10 seconds and its 5-minute candles every 5 minutes (Binance public data); tier A {cnt.get('A', 0)}, "
                       f"B {cnt.get('B', 0)}, C {cnt.get('C', 0)} (C is watched, never judged)."},
            {"cadence": "10 s", "name": "Zone touch, every coin", "scope": scope, "n": u_zt, "unit": "paper trades",
             "detail": "The eye's zone-touch rule on every coin's live price, per tier, with its own stop and 20-day exit."},
            {"cadence": "daily", "name": "Daily rules, every coin", "scope": scope, "n": u_sig + u_rnd, "unit": "paper trades",
             "detail": f"The short dip trade and your setups on every coin after each daily close: {_s(u_sig, 'signal')}; random baselines "
                       f"per tier took {u_rnd}."},
            {"cadence": "15 min", "name": "Explorer setups, every coin (shadows)", "scope": scope, "n": ux.get("coins"), "unit": "coins checked",
             "detail": "The 15-minute setups on every coin as shadow trades, scored by tier against the engine's random entries; they never "
                       "wake the brain outside the 10 (they lost after costs in history)."},
            {"cadence": "nightly", "name": "Universe rebuild", "scope": "every daily rule on every coin", "n": u_rb, "unit": "nights",
             "detail": "Re-runs every daily rule on the stored candles and checks the ledger has exactly those signals."},
            {"cadence": "on wake", "name": "Brain's ranking", "scope": scope, "n": unrev, "unit": "wakes not reviewed",
             "detail": "Every wake is ranked first; the AI decides the best ones within the day's budget, and the rest are scored later "
                       "to check the ranking."},
        ]
    except Exception:  # noqa: BLE001
        uni = []
    return uni + [
        {"cadence": "10 s", "name": "The eye", "scope": "10 coins", "n": ticks, "unit": "looks since the last restart",
         "detail": f"Your stops and alerts, a sudden Bitcoin drop, price entering a support zone ({_s(zone_touch, 'zone-touch trade')}); "
                   "it also manages Jarvis's open trades."},
        {"cadence": f"{round(health.EVERY / 60)} min", "name": "Health watchdog", "scope": "every part", "n": None, "unit": "",
         "detail": f"Checks every {round(health.EVERY / 60)} minutes that each part is alive and working (the Explorer's last real scan, "
                   "Hands' login, the tunnel, the hourly watch); a part down twice in a row phones you."},
        {"cadence": "15 min", "name": "Explorer", "scope": "10 coins", "n": int(days * 96 * 10), "unit": "coin checks",
         "detail": f"{seen} setups seen, {D.get('real_orders', 0)} real paper orders, "
                   f"{sum(b['n'] for b in D.get('blocked') or [])} stopped and tracked, {D.get('random_baseline', 0)} random entries."},
        {"cadence": "1 h", "name": "Hourly watch (Hunter, Squeeze)", "scope": "10 coins", "n": sum(1 for h in hb if h.get("ok")), "unit": "looks",
         "detail": f"Last 24 hours: Hunter checked {hun.get('looks', 0)} times and fired {hun.get('setups', 0)}; "
                   f"Squeeze checked {sq.get('looks', 0)} times and fired {sq.get('setups', 0)}."},
        {"cadence": "daily", "name": "Daily watches", "scope": "10 coins", "n": daily_sig + daily_rnd, "unit": "paper trades",
         "detail": f"At each daily close (8 PM Toronto): your setups and the short dip trade gave {_s(daily_sig, 'signal')}; "
                   f"the random baselines took {daily_rnd}."},
        {"cadence": "daily", "name": "30-coin paper tier", "scope": "29 coins", "n": t30_days, "unit": "daily decisions",
         "detail": f"The trend book holds {t30_hold} of 29 coins; the dip trade (H07-T30) has given {_s(h07_30, 'signal')}."},
        {"cadence": "daily", "name": "Trend portfolio (T3-B)", "scope": "10 coins", "n": t3_days, "unit": "daily ratings",
         "detail": "Rates every coin each day; re-sizes a coin only when it drifts outside 0.5x-1.5x of its share."},
        {"cadence": "daily", "name": "Missed-move review", "scope": "10 + 29 coins", "n": missed_days, "unit": "days reviewed",
         "detail": "Half an hour after the daily close: the day's biggest moves, and whether we caught, saw or missed them."},
        {"cadence": "nightly", "name": "Nightly rebuild", "scope": "every Explorer decision", "n": nights, "unit": "nights",
         "detail": "Replays the Explorer from raw candles and checks every real decision comes out the same."},
        {"cadence": "on wake", "name": "Jarvis's brain", "scope": "10 coins", "n": wakes, "unit": "wakes",
         "detail": f"Woken by the Explorer, Hunter, your setups, zone entries and coins needing attention: decided {decided}, "
                   f"dropped {dropped} (see the limits)."},
    ]


def _limit_verdict(stopped: int, after: dict, base: dict) -> str:
    if not stopped:
        return "Never reached so far."
    if not after.get("closed"):
        return "Nothing it stopped has finished yet."
    a, r, x = after.get("avg_usd"), (base.get("real") or {}).get("avg_usd"), (base.get("random") or {}).get("avg_usd")
    bits = [f"What it stopped averaged {_usd(a)} per $100 trade"]
    if r is not None:
        bits.append(f"{'worse than' if a < r else 'better than'} the trades taken ({_usd(r)})")
    if x is not None:
        bits.append(f"{'worse than' if a < x else 'better than'} random entries ({_usd(x)})")
    ev = after.get("events") or 0
    tail = f"Only {_s(ev, 'market event')}, so too early to call." if ev < GOAL_EVENTS else f"{ev} market events: enough to read."
    lean = (" So far it is not hiding winners." if (r is not None and a < r) and (x is None or a < x) else
            " So far the stopped trades did better: worth watching." if r is not None and a > r else "")
    return ", ".join(bits) + "." + lean + " " + tail


def _limits(j, P: dict, rows: list[dict], L: dict, ex) -> list[dict]:
    from jarvis.service import brain
    from jarvis.service.views import _summ

    try:
        from src.intelligence import explorer_live as xl

        mo, md = xl.MAX_OPEN, xl.MAX_DAY
    except Exception:  # noqa: BLE001
        mo, md = 20, 60
    stack = 1
    if ex:
        eng0 = next(iter(ex.st["engines"].values()))
        rules = eng0.rules_at(int(j.now())) if hasattr(eng0, "rules_at") else None
        stack = getattr(rules, "stack", 1) if rules else 1
    D = P.get("decided") or {}
    stopped = {b["code"]: b["n"] for b in D.get("blocked") or []}
    base = {"real": _summ([r for r in rows if not r["shadow"]]), "random": _summ([r for r in rows if r["shadow"] == "RANDOM"])}
    tickets = {t["id"]: t for t in L.get("tickets", [])}
    out = []
    for code, rule, setting, why in (
            ("REJECTED_SLOT", "One trade per coin per kind",
             f"up to {stack} at once per coin and trade kind, at least 2 four-hour ranges apart" if stack > 1 else "one at a time per coin and trade kind",
             "keeps one move from filling the book with copies of the same trade"),
            ("NO_TYPE", "Room to a target", "a setup trades only when one trade kind has room to its target",
             "a quality check, not a cap: no room means the costs eat the trade"),
            ("CAP", "Account limit", f"{mo} open at once, {md} new a day", "the $2,000 paper account at $100 a trade"),
            ("REJECTED_DUP", "One setup per coin per scan", "if two setups fire on one coin in the same scan, the first is taken",
             "two setups on one candle are one decision")):
        after = _summ([r for r in rows if r["shadow"] == code])
        n = stopped.get(code, 0)
        out.append({"id": code, "where": "Explorer", "rule": rule, "setting": setting, "why": why, "stopped": n, "after": after,
                    "verdict": _limit_verdict(n, after, base), "tracked": True})
    drops: dict[str, int] = {}
    try:
        for state, n in j.db.execute("SELECT state, COUNT(*) FROM brain_queue WHERE state LIKE 'DROPPED:%' GROUP BY 1"):
            k = state.split(":", 1)[1].strip()
            drops[k] = drops.get(k, 0) + n
    except Exception:  # noqa: BLE001  no wakes yet
        pass
    tk4 = tickets.get("TK4")
    brain_rules = [
        ("HOLDING", "already holding", "Trades per coin", f"at most {brain.MAX_PER_COIN} open on one coin; a wake on a coin at that limit is dropped"),
        ("OPEN_MAX", "trades already open", "Open trades", f"at most {brain.MAX_OPEN} open"),
        ("DAY_MAX", "decisions are used", "Decisions a day", f"{brain.DAILY_MAX} a day"),
        ("COOLDOWN", "last 6 hours", "One decision per coin per 6 hours", "a coin decided less than 6 hours ago waits"),
        ("STALE", "stale", "Fresh wakes only", f"a wake older than {brain.STALE_S // 60} minutes is dropped"),
        ("BUDGET", "budget", "AI budget", "the daily Claude budget"),
        ("OFF", "switched off", "Switched off", "the brain or Ask is off"),
    ]
    used = set()
    moves = _try(lambda: _wake_moves(j), {}, "wake_moves") or {}
    for key, needle, rule, setting in brain_rules:
        n = sum(v for k, v in drops.items() if needle in k)
        used |= {k for k in drops if needle in k}
        if not n and key not in ("HOLDING", "OPEN_MAX", "DAY_MAX"):
            continue
        mv = _move_summary([x for k, xs in moves.items() if needle in k for x in xs])
        base_mv = _move_summary(moves.get("DONE") or [])
        out.append({"id": f"BRAIN_{key}", "where": "Jarvis's brain", "rule": rule, "setting": setting, "stopped": n, "after": None,
                    "tracked": bool(mv), "moves_24h": mv, "decided_moves_24h": base_mv,
                    "verdict": ("Never reached so far." if not n else
                                (f"After the wakes it dropped, the coin moved {mv['avg_pct']:+.2f}% on average in the next 24 hours "
                                 f"({mv['n']} wakes, {mv['up_pct']}% up); after the wakes it decided on, {base_mv['avg_pct']:+.2f}%. "
                                 "A rough check, not a trade result: there was no plan to score.") if mv and base_mv else
                                "Dropped wakes are not followed, so what they would have done is unknown."),
                    "proposal": ({"id": "TK4", "status": tk4.get("status"), "change": tk4.get("change")}
                                 if tk4 and key in ("HOLDING", "OPEN_MAX", "DAY_MAX") and n else None)})
    for k, n in drops.items():
        if k not in used:
            out.append({"id": "BRAIN_OTHER", "where": "Jarvis's brain", "rule": k, "setting": "", "stopped": n, "after": None,
                        "tracked": False, "verdict": "Dropped wakes are not followed."})
    out.append({"id": "SIZE", "where": "Every book", "rule": "Trade size", "setting": "$100 per paper trade; $2,000 per trend book",
                "stopped": None, "after": None, "tracked": False,
                "verdict": "Size changes the dollars, not the evidence: a bigger paper size makes the same number of trades. "
                           "Evidence grows with more trades from separate market moves."})
    return out


def _results(j, P: dict, rows: list[dict]) -> dict:
    from jarvis.service import brain, views

    groups = (("real", "Explorer: real paper trades", lambda r: not r["shadow"]),
              ("would_be", "Explorer: stopped by a limit (tracked)", lambda r: r["shadow"] in ("REJECTED_SLOT", "CAP", "REJECTED_DUP")),
              ("no_type", "Explorer: no room to a target (tracked)", lambda r: r["shadow"] == "NO_TYPE"),
              ("random", "Random entries: the bar to beat", lambda r: r["shadow"] == "RANDOM"))
    items = [{"key": k, "label": label, **views._summ([r for r in rows if f(r)])} for k, label, f in groups]
    items[0]["open"] = (P.get("results") or {}).get("open_real")
    rep = _try(lambda: brain.report(j), {}, "brain") or {}
    if rep:
        items.append({"key": "jarvis", "label": "Jarvis's own trades", "closed": rep.get("closed", 0), "wins": None,
                      "avg_usd": rep.get("avg_usd_per_100"), "net_usd": None, "events": rep.get("events", 0), "open": len(rep.get("open") or []),
                      "twins_avg_usd": rep.get("random_twin_avg_usd"), "vs_twins_usd": rep.get("vs_random_usd")})
    rnd = next(x for x in items if x["key"] == "random")
    real = items[0]
    events = views._events_count(rows)
    books = []
    t3 = next((x for x in (P.get("in_use") or {}).get("repairs") or [] if x.get("id") == "T3"), None)
    tr = (t3 or {}).get("tracking") or {}
    if tr:
        books.append({"key": "t3", "label": "Trend portfolio, 10 coins", "pct": tr.get("main_return_pct"), "vs_label": "buy and hold",
                      "vs_pct": tr.get("buy_hold_return_pct"), "days": tr.get("days"), "trades": tr.get("trades")})

    def t30():
        from jarvis.service import tier30

        s = tier30.status(j)
        m = s["t3"]["books"]["MAIN"]
        bh = tier30.buy_hold(j)
        books.append({"key": "t30", "label": "Trend book, 30-coin tier", "pct": m.get("return_pct"),
                      "vs_label": "buy and hold" if bh.get("pct") is not None else None, "vs_pct": bh.get("pct"),
                      "days": round((j.now() - bh["since_t"]) / DAY, 1) if bh.get("since_t") else None, "trades": m.get("trades"),
                      "stale_coins": bh.get("stale") or []})
        h = s["h07"]
        books.append({"key": "h07_t30", "label": "Dip trade (H07), 30-coin tier", "closed": h.get("closed"), "net_usd": h.get("net_usd"),
                      "open": h.get("open")})

    _try(t30, {}, "t30")
    if events < GOAL_EVENTS:
        verdict = (f"Too early: {_s(events, 'market event')} so far, and no verdict before {GOAL_EVENTS}. "
                   f"So far real trades average {_usd(real['avg_usd'])} per $100 against {_usd(rnd['avg_usd'])} for random entries.")
    else:
        verdict = ("Real trades are ahead of random entries." if (real["avg_usd"] or 0) > (rnd["avg_usd"] or 0) else
                   "Real trades are not ahead of random entries.")
    return {"items": items, "random_avg_usd": rnd["avg_usd"], "events": events, "goal_events": GOAL_EVENTS, "books": books,
            "by_setup": (P.get("results") or {}).get("by_setup") or [], "verdict": verdict,
            "read": "Each bar is the average result of a $100 paper trade after costs. A group is only useful if it beats the random "
                    "entries, and only after 10 separate market moves: trades closing on the same day are one piece of evidence."}


def _chain(L: dict) -> list[dict]:
    R = {r["id"]: r for r in L.get("reviews", [])}
    M = {m["id"]: m for m in L.get("modes", [])}
    T = {t["id"]: t for t in L.get("tickets", [])}
    out = []
    if "R2" in R:
        out.append({"id": "R2", "step": "Studied other traders' real trades", "what": R["R2"].get("result"), "status": "DONE",
                    "verdict": R["R2"].get("verdict"), "change": R["R2"].get("changed")})
    if "R3" in R:
        out.append({"id": "R3", "step": "Tested their one pattern: buying weakness", "what": R["R3"].get("result"), "status": "DONE",
                    "verdict": R["R3"].get("verdict"), "change": R["R3"].get("changed")})
    if "W1" in M:
        out.append({"id": "W1", "step": "You put the dip setup (E6) on paper anyway, for evidence", "what": M["W1"].get("what"),
                    "status": "IN_USE", "change": M["W1"].get("why")})
    if "TK2" in T:
        out.append({"id": "TK2", "step": "Live paper found a flaw in the dip trades", "what": T["TK2"].get("what"),
                    "status": T["TK2"].get("status"), "change": T["TK2"].get("change")})
    return out


def _rebuild(j, L: dict) -> dict:
    _rebuild_table(j)
    logged = j.db.execute("SELECT t, source, match, logged, rebuilt FROM rebuild_log ORDER BY t").fetchall()
    nightly = [r for r in logged if (r[1] or "").startswith("nightly")]
    asked = []
    try:
        asked = [(t, json.loads(res or "{}")) for t, res in
                 j.db.execute("SELECT coalesce(done_t, t), result FROM jobs WHERE kind='reconstruction' AND status='DONE' ORDER BY t")]
    except Exception:  # noqa: BLE001  no research jobs yet
        pass
    n_mis = sum(1 for r in nightly if not r[2])
    a_mis = sum(1 for _, r in asked if r.get("match") is False)
    p = Path(j.dir) / "explorer_reconstruct.json"
    cur = json.loads(p.read_text()) if p.exists() else {}
    study = next((s for s in L.get("studies", []) if s.get("id") == "R2"), None)
    return {"nightly": {"runs": len(nightly), "first": _day(nightly[0][0]) if nightly else None, "mismatches": n_mis,
                        "every": "every night at the daily close (8 PM Toronto)"},
            "asked": {"runs": len(asked), "mismatches": a_mis, "last": _local(asked[-1][0]) if asked else None,
                      "how": "you ask Ananta: \"run the reconstruction\""},
            "total": len(nightly) + len(asked), "mismatches": n_mis + a_mis,
            "last": {"when": _local(p.stat().st_mtime) if p.exists() else None, "match": cur.get("match"),
                     "checked": cur.get("logged_real_events"), "rebuilt": cur.get("rebuilt_real_events")},
            "how": "The whole Explorer is replayed from the raw candles with a fresh engine; every real decision (order, fill, close) "
                   "must come out the same, at the same time. The account limits are not re-applied.",
            "if_mismatch": "Your phone gets an alert, the day's evidence is not trusted until the difference is explained, and it goes "
                           "on the repair board as a ticket.",
            "others": study, "chain": _chain(L)}


def _misses(j) -> dict:
    from jarvis.service import missed

    r = missed.recent(j, 30)
    flags = {k for (k,) in j.db.execute("SELECT k FROM engine_state WHERE k LIKE 'missed:flag:%'")}
    days = sorted(k for (k,) in j.db.execute("SELECT k FROM engine_state WHERE k LIKE 'missed:____-__-__'"))

    def pats(ps: list[dict], tier: str) -> list[dict]:
        return [{"said": p["said"], "times": p["times"], "of": missed.REPEAT_N, "avg_move_pct": p["avg_move_pct"], "coins": p["coins"],
                 "forwarded": (f"missed:flag:{p['pattern']}" + ("" if tier == "LIVE10" else f":{tier}")) in flags} for p in ps]

    def mv(ms: list[dict]) -> list[dict]:
        return [{"day": m["day"], "coin": m["coin"], "move_pct": m["move_pct"], "label": m["label"], "why": m["why"],
                 "miss_class": m.get("miss_class"), "class_why": m.get("class_why")} for m in ms[:8]]

    return {"days_reviewed": len(days), "since": _day(_date_t(days[0][7:])) if days else None,
            "live": {"counts": r["counts"], "moves": mv(r["moves"]), "patterns": pats(r["patterns"], "LIVE10")},
            "t30": {"counts": r["tier30"]["counts"], "moves": mv(r["tier30"]["moves"]), "patterns": pats(r["tier30"]["patterns"], "T30"),
                    "days": _t30_days(j)},
            "forwarded": len(flags), "classes": r.get("classes"), "class_meaning": r.get("class_meaning"),
            "what_we_do": f"Every miss is filed with what we saw at its start and a class (data, intentional, execution, decision, detection, "
                          f"knowledge): a move the market gate rightly refused is not a mistake. The same kind of detection or knowledge miss {missed.REPEAT_N} times in "
                          f"{missed.REPEAT_DAYS} days becomes a repair-shop request (an idea to test against the times the same start "
                          "led nowhere), and Jarvis's brain sees it as a candidate pattern. Picked after the fact, so never proof."}


def _board(j, L: dict, P: dict) -> dict:
    from jarvis.service import requests_log

    items: list[dict] = []
    for t in L.get("tickets", []):
        items.append({"id": t["id"], "kind": "ticket", "date": t.get("date"), "from": t.get("from"), "what": t.get("what"),
                      "did": t.get("did"), "change": t.get("change"), "status": t.get("status") or "OPEN", "next": t.get("next")})
    for r in requests_log._select(j):
        items.append({"id": f"#{r['num']}", "kind": "request", "date": datetime.fromtimestamp(r["t"], timezone.utc).strftime("%Y-%m-%d") if r.get("t") else None,
                      "from": "you" if r.get("by") == "owner" else "Ananta flagged it itself", "what": r.get("text"), "did": r.get("note") or "",
                      "change": "", "status": r.get("status") or "OPEN", "about": r.get("about")})
    for r in L.get("reviews", []):
        items.append({"id": r["id"], "kind": "review", "date": r.get("date"), "from": r.get("forwarded_because"), "what": r.get("title"),
                      "question": r.get("question"), "did": r.get("result"), "change": r.get("changed"),
                      "status": "DONE" if r.get("status") == "DONE" else "IN_PROGRESS", "verdict": r.get("verdict") or None})
    for q in (P.get("shop") or {}).get("queue") or L.get("queue", []):
        items.append({"id": q["id"], "kind": "question", "date": None, "from": q.get("why"), "what": q.get("title"),
                      "did": f"Waiting for {q.get('waiting_for')}.", "change": "", "status": "WAITING_FOR_EVIDENCE",
                      "have": q.get("have"), "goal": q.get("goal")})
    order = {s: k for k, s in enumerate(BOARD_ORDER)}
    items.sort(key=lambda x: (order.get(x["status"], 9), -_date_t(x["date"])))
    for x in items:
        x["status_words"] = BOARD_WORDS.get(x["status"], x["status"])
        x["group"] = BOARD_GROUP.get(x["status"], "us")
    groups = {g: sum(1 for x in items if x["group"] == g) for g in ("you", "us", "evidence", "done")}
    verdicts: dict[str, int] = {}
    for r in L.get("reviews", []):
        if r.get("status") == "DONE":
            verdicts[r.get("verdict") or "?"] = verdicts.get(r.get("verdict") or "?", 0) + 1
    return {"items": items, "groups": groups, "kinds": {k: sum(1 for x in items if x["kind"] == k) for k in ("ticket", "request", "review", "question")},
            "verdicts": verdicts, "words": BOARD_WORDS,
            "read": "Tickets are problems or chances found in the live system (by the watchdog, the logs, your chats or a check); requests "
                    "are what you or Ananta flagged; reviews are questions tested in the repair shop on data the system never saw; "
                    "questions wait for live evidence."}


def _in_use(L: dict, P: dict) -> dict:
    reps = (P.get("in_use") or {}).get("repairs") or L.get("in_use", [])
    items = []
    for x in reps:
        t = x.get("tracking") or {}
        items.append({"id": x["id"], "what": x.get("what"), "since": x.get("since"), "from": x.get("from"), "expect": x.get("expect"),
                      "watch_out": x.get("watch_out"), "so_far": x.get("verdict_so_far"),
                      "numbers": ({"book_pct": t.get("main_return_pct"), "buy_hold_pct": t.get("buy_hold_return_pct"), "days": t.get("days"),
                                   "trades": t.get("trades")} if t else None)})
    safety = L.get("safety_changes", [])
    return {"items": items, "modes": L.get("modes", []), "safety": safety[::-1], "safety_n": len(safety)}


def _waiting(j, P: dict, ex) -> list[dict]:
    from jarvis.service import brain

    now = j.now()
    start_ex = ex.st.get("trade_from_t") if ex else None
    t3_first = _try(lambda: j._layer().con.execute("SELECT min(day_t) FROM decisions").fetchone()[0], {}, "t3")
    t30_first = None
    p30 = Path(j.dir) / "portfolio_book_t30.sqlite"
    if p30.exists():
        con = sqlite3.connect(f"file:{p30}?mode=ro", uri=True, timeout=10)
        try:
            t30_first = con.execute("SELECT min(day_t) FROM decisions").fetchone()[0]
        finally:
            con.close()
    jarvis_first = _one(j, "SELECT min(t) FROM brain_decisions", default=None)
    reads_first = _one(j, "SELECT min(t) FROM snapshots", default=None) or start_ex
    rep = _try(lambda: brain.report(j), {}, "brain") or {}
    wakes = _one(j, "SELECT COUNT(*) FROM brain_queue")
    decided = _one(j, "SELECT COUNT(*) FROM brain_decisions WHERE action != 'ERROR'")
    out = []
    for q in (P.get("shop") or {}).get("queue") or []:
        m = q.get("metric")
        row = {"id": q["id"], "title": q.get("title"), "waiting_for": q.get("waiting_for"), "why": q.get("why"),
               "have": q.get("have"), "goal": q.get("goal"), "unit": "", "speedup": SPEEDUP.get(m)}
        start = None
        if m == "closed_trades":
            n = q.get("have") or 0
            row.update(have=q.get("events") or 0, goal=GOAL_EVENTS, unit="market events",
                       also=f"{n} trades closed: the {q.get('goal')}-trade part is {'met' if n >= (q.get('goal') or 0) else 'not met yet'}")
            start = start_ex
        elif m in ("weekly_rebalances", "t30_weeks"):
            first = t3_first if m == "weekly_rebalances" else t30_first
            row["unit"] = "weeks"
            if first:
                due = first + (q.get("goal") or 6) * 7 * DAY
                row.update(have=int((now - first) // (7 * DAY)), since=_day(first), eta_date=_day(due),
                           eta_days=max(0, math.ceil((due - now) / DAY)), pace="one a week")
            row["done"] = bool(row["goal"]) and (row["have"] or 0) >= row["goal"]
            out.append(row)
            continue
        elif m == "jarvis_events":
            row.update(have=rep.get("events", 0), unit="market events")
            row["speedup"] = (f"Jarvis decided {decided} of {wakes} wakes; ticket TK4 (decide on every wake, 20 open, 40 a day) is the "
                              "biggest speed-up and waits for you.")
            start = jarvis_first
        elif m == "review_slot":
            row.update(unit="review", have=0, eta_note="waits for a work session, not for the market", done=False)
            out.append(row)
            continue
        elif m == "e5_trades":
            row["unit"], start = "E5 trades", start_ex
        elif m in ("setup_fires", "h07_fires"):
            row["unit"], start = "signals", reads_first
        else:
            row["unit"], start = "sightings", start_ex
        have = row["have"] or 0
        if start and now - start > DAY / 2:
            pace = have / ((now - start) / DAY)
            row.update(since=_day(start), pace_per_day=round(pace, 2))
            if row["goal"] and have < row["goal"]:
                if pace > 0:
                    row["eta_days"] = math.ceil((row["goal"] - have) / pace)
                    row["eta_date"] = _day(now + row["eta_days"] * DAY)
                else:
                    row["eta_note"] = f"none yet in {round((now - start) / DAY)} days"
        row["done"] = bool(row["goal"]) and have >= row["goal"]
        out.append(row)
    return out


def _loop(j, out: dict, P: dict, rows: list[dict]) -> list[dict]:
    from jarvis.service import views

    D = P.get("decided") or {}
    clocks = {c["name"]: c for c in out.get("clocks") or []}
    ex_checks = (clocks.get("Explorer") or {}).get("n") or 0
    hourly = (clocks.get("Hourly watch (Hunter, Squeeze)") or {}).get("n") or 0
    seen = sum(s["seen"] for s in P.get("seen") or [])
    blocked = sum(b["n"] for b in D.get("blocked") or [])
    wakes = _one(j, "SELECT COUNT(*) FROM brain_queue")
    decided = _one(j, "SELECT COUNT(*) FROM brain_decisions WHERE action != 'ERROR'")
    daily_closed = _one(j, "SELECT COUNT(*) FROM evidence_trades WHERE status='CLOSED'")
    events = views._events_count(rows)
    m = out.get("misses") or {}
    mc = {k: (m.get("live") or {}).get("counts", {}).get(k, 0) + (m.get("t30") or {}).get("counts", {}).get(k, 0) for k in ("CAUGHT", "SEEN", "MISSED")}
    b = (out.get("board") or {}).get("kinds") or {}
    u = out.get("in_use") or {}
    return [
        {"key": "looked", "label": "Looked", "n": ex_checks + hourly,
         "sub": f"{ex_checks:,} Explorer coin checks and {hourly} hourly looks; the eye looks every 10 seconds; daily watches at each close"},
        {"key": "spotted", "label": "Spotted", "n": seen, "sub": "setups whose every condition was met"},
        {"key": "decided", "label": "Decided", "n": D.get("real_orders", 0) + blocked + decided,
         "sub": f"{D.get('real_orders', 0)} real Explorer orders ({D.get('filled', 0)} filled); {blocked} stopped (a limit, or no room to "
                f"a target) and tracked anyway; Jarvis decided {decided} of {wakes} wakes; plus {D.get('random_baseline', 0)} random entries as the bar"},
        {"key": "scored", "label": "Scored", "n": len(rows) + daily_closed,
         "sub": f"closed trades scored after costs (real, stopped, random); {_s(events, 'market event')} so far"},
        {"key": "missed", "label": "Misses checked", "n": sum(mc.values()),
         "sub": f"big moves: {mc['CAUGHT']} caught, {mc['SEEN']} seen, {mc['MISSED']} missed"},
        {"key": "forwarded", "label": "Sent to the repair shop", "n": sum(b.values()),
         "sub": f"{_s(b.get('review', 0), 'review')}, {_s(b.get('ticket', 0), 'ticket')}, {_s(b.get('request', 0), 'request')}, "
                f"{b.get('question', 0)} waiting for evidence"},
        {"key": "changed", "label": "Changed", "n": len(u.get("items") or []) + len(u.get("modes") or []) + (u.get("safety_n") or 0),
         "sub": f"{len(u.get('items') or [])} repairs running in paper, {len(u.get('modes') or [])} mode, {u.get('safety_n') or 0} safety changes"},
    ]


PERMISSION_CHECK_FROM = 1791288000      # 2026-10-06 12:00 UTC: Jarvis's decisions are permission-checked from here on
GATE_WORDS = {"PASS": "Pass", "FAIL": "Fail", "PARTLY": "Partly", "PENDING": "In progress", "NOT_MEASURED": "Not measured yet"}


def _gate(j, out: dict) -> dict:
    """The Engine Acceptance Gate (docs/knowledge/acceptance_gate.json): 27 checks; a few are computed live here."""
    from jarvis.service.core import docs_dir

    g = json.loads((docs_dir(j.dir) / "knowledge" / "acceptance_gate.json").read_text())
    checks = [dict(c) for c in g["checks"]]
    by = {c["id"]: c for c in checks}
    _rebuild_table(j)
    nights = [m for (m,) in j.db.execute("SELECT match FROM rebuild_log WHERE source LIKE 'nightly%' ORDER BY t DESC")]
    run = 0
    for m in nights:
        if not m:
            break
        run += 1
    c = by.get("engine_reproducible")
    if c:
        c["status"] = "PASS" if run >= 30 else "FAIL" if nights and not nights[0] else "PENDING"
        c["note"] = f"{run} of 30 nights in a row match" + ("; the last night did NOT match" if nights and not nights[0] else "")
    r = out.get("results") or {}
    c = by.get("strategy_baselines")
    if c and r:
        real = next((x for x in r.get("items", []) if x["key"] == "real"), {})
        ev = r.get("events") or 0
        ahead = (real.get("avg_usd") or -9) > (r.get("random_avg_usd") or 0)
        c["status"] = ("PASS" if ahead else "FAIL") if ev >= GOAL_EVENTS else "PENDING"
        c["note"] = (f"{ev} of {GOAL_EVENTS} market events; real {_usd(real.get('avg_usd'))} vs random {_usd(r.get('random_avg_usd'))} per $100")
    c = by.get("agent_no_failed_rules")
    if c:
        since = max(int(j.now()) - 7 * DAY, PERMISSION_CHECK_FROM)      # only decisions made since the check exists count
        n = _one(j, "SELECT COUNT(*) FROM brain_decisions WHERE t >= ? AND action != 'ERROR'", (since,))
        # Only BUYS count (status check, Oct 8): a pass that mentions a context idea is not a trade on it. A buy that rested only on
        # context-only ideas is turned into a pass by brain.permission_check ("permission:" notes = the check working).
        n = _one(j, "SELECT COUNT(*) FROM brain_decisions WHERE t >= ? AND action = 'TAKE'", (since,))
        cited = _one(j, "SELECT COUNT(*) FROM brain_decisions WHERE t >= ? AND action = 'TAKE' AND note LIKE '%cited context-only%'", (since,))
        blocked = _one(j, "SELECT COUNT(*) FROM brain_decisions WHERE t >= ? AND note LIKE 'permission:%'", (since,))
        c["status"] = "PENDING" if not n else "PASS" if not cited else "FAIL"
        c["note"] = (f"{cited} of {n} buys leaned partly on a context-only idea; {blocked} buys that rested only on one were stopped "
                     "(last 7 days, checked since Oct 6)" if n else "no buys since the check started (Oct 6)")
    for c in checks:
        c["status_words"] = GATE_WORDS.get(c["status"], c["status"])
    passed = sum(1 for c in checks if c["status"] == "PASS")
    areas = []
    for c in checks:
        if c["area"] not in areas:
            areas.append(c["area"])
    return {"passed": passed, "of": len(checks), "checks": checks, "areas": areas, "rule": g["rule"],
            "counts": {k: sum(1 for c in checks if c["status"] == k) for k in GATE_WORDS}}


def _headline(out: dict) -> str:
    r = out.get("results") or {}
    g = (out.get("board") or {}).get("groups") or {}
    loop = {x["key"]: x for x in out.get("loop") or []}
    bits = [f"Day {out.get('days')} of paper."] if out.get("days") is not None else []
    if r:
        bits.append(f"{(loop.get('scored') or {}).get('n', 0)} trades scored from {_s(r.get('events'), 'market event')}; "
                    f"no verdict before {GOAL_EVENTS}.")
        real = next((x for x in r.get("items", []) if x["key"] == "real"), None)
        if real and real.get("avg_usd") is not None and r.get("random_avg_usd") is not None:
            bits.append(f"So far real trades average {_usd(real['avg_usd'])} per $100, random entries {_usd(r['random_avg_usd'])}.")
    gt = out.get("gate") or {}
    if gt:
        bits.append(f"Acceptance gate: {gt['passed']} of {gt['of']} checks pass.")
    if g.get("you"):
        bits.append(f"{_s(g['you'], 'change')} wait{'s' if g['you'] == 1 else ''} for your yes.")
    return " ".join(bits)


def summary(j) -> dict:
    """The same page in short, for Ask: counts and the open work, without the long texts."""
    d = build(j)
    b = d.get("board") or {}
    active = [{k: x.get(k) for k in ("id", "kind", "what", "status_words", "change")} for x in b.get("items", []) if x.get("group") in ("you", "us")]
    lim = [{k: x.get(k) for k in ("where", "rule", "setting", "stopped", "verdict")} for x in d.get("limits") or []]
    rb = d.get("rebuild") or {}
    return {"as_of": d.get("as_of"), "headline": d.get("headline"), "loop": d.get("loop"), "clocks": d.get("clocks"), "limits": lim,
            "results": {k: (d.get("results") or {}).get(k) for k in ("items", "events", "goal_events", "books", "verdict")},
            "reconstruction": {k: rb.get(k) for k in ("nightly", "asked", "total", "mismatches", "last", "how", "if_mismatch", "others", "chain")},
            "misses": d.get("misses"), "board_counts": {"groups": b.get("groups"), "kinds": b.get("kinds"), "review_verdicts": b.get("verdicts")},
            "open_work": active, "waiting": d.get("waiting"),
            "acceptance_gate": {k: (d.get("gate") or {}).get(k) for k in ("passed", "of", "counts", "rule")} | {
                "not_passing": [{x: c.get(x) for x in ("area", "check", "status_words", "pass_mark", "note")} for c in (d.get("gate") or {}).get("checks", [])
                                if c["status"] != "PASS"]},
            "errors": d.get("errors")}
