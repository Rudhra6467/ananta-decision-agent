"""Every rule on every coin (engine plan U3-U6; Universe Rule v2, docs/UNIVERSE_RULE_V2.md).

Watches (pre-registered 2026-10-09, before any universe trade): the daily rules with the SAME code the history tests use
(H07, M1a, M2a, M2a-G, M3a, M3b) and the random baselines (10, 20 and 30 days), once per tier, as their own books:
watch id = <rule>-U<tier>, e.g. H07-UA, M1a-UB, RANDOM_20D-UC. A random baseline picks only among its own tier's coins, so
every rule is compared with chance in the same kind of coin. Plus ZONE_TOUCH-U<tier>: the live price comes down into a support
zone of a kind history supports while the market is allowed (the eye's rule, on every coin), stop half a daily range under
the zone, else 20 days. Costs per Universe Rule v2 (registry.cost). The 10-coin and 30-coin books are untouched (D7).

  run_daily(j)          after each daily close: new signals, fills at the next open, exits, for every tier; wakes the brain
                        for tier A and B signals; arms tomorrow's zones; the missed-move check; the nightly rebuild
  tick(j, px)           every 10 seconds on the feed's prices: zone touches, live stops of universe trades and of the brain's
                        trades on coins outside the 10
  rebuild(j, days)      reconstruction: the rules re-run on the stored candles, compared with the ledger (data, code, timing)
  scoreboard(j)         each rule x tier x market regime against its random baseline, in independent market days
  missed(j, day_t)      the day's biggest up-days across tier A and B coins: caught, seen or missed
  status(j)             for the app, Ask and the Evidence page
Paper only: nothing here reaches Hands or an exchange.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

DAY = 86400
TIERS = ("A", "B", "C")
RULES = ("H07", "M1a", "M2a", "M2a-G", "M3a", "M3b")
RANDOMS = ("RANDOM_10D", "RANDOM_20D", "RANDOM_30D")
BASELINE_OF = {"H07": "RANDOM_10D", "ZONE_TOUCH": "RANDOM_20D", "M1a": "RANDOM_30D", "M2a": "RANDOM_30D", "M2a-G": "RANDOM_30D",
               "M3a": "RANDOM_30D", "M3b": "RANDOM_30D"}
ZONE_GAP = 20 * DAY
MIN_EVENTS = 10
STATE: dict[str, Any] = {"armed": {}, "armed_t": 0, "prev": {}, "last_daily": None, "last_tick": None, "errors": {}}


def wid(rule: str, tier: str) -> str:
    return f"{rule}-U{tier}"


def split(watch: str) -> tuple[str, str] | None:
    """'H07-UA' -> ('H07', 'A'); None for any other watch."""
    if len(watch) > 3 and watch[-3:-1] == "-U" and watch[-1] in TIERS:
        return watch[:-3], watch[-1]
    return None


VERSIONS_FILE = "knowledge/universe_versions.json"
VERSION_KEYS = {"days", "rsi_exit", "market_gate"}           # what a new version may change in a rule the engine already has


def versions() -> list[dict]:
    """Engine plan U6.3: rule versions the repair shop passed, each written down (with the day) before it trades. A version runs
    beside its parent on every tier as its own book, '<rule>.<version>-U<tier>', until it has 10 market days."""
    from jarvis.service.core import docs_dir

    try:
        p = docs_dir(Path(__file__).resolve().parents[2]) / VERSIONS_FILE
        return json.loads(p.read_text()).get("versions", []) if p.exists() else []
    except Exception:  # noqa: BLE001
        return []


def register() -> None:
    """Declare the universe watches in the watch engine (same rules, their own ids), plus any registered versions."""
    from jarvis.service import watch_engine as W

    vers = [v for v in versions() if v.get("rule") in RULES and v.get("version") and set(v.get("changes") or {}) <= VERSION_KEYS]
    for tier in TIERS:
        for r in RULES + RANDOMS:
            spec = dict(W.DAILY[r])
            spec["tier"] = "U" + tier
            W.DAILY[wid(r, tier)] = spec
        for v in vers:
            spec = dict(W.DAILY[v["rule"]]) | dict(v["changes"])
            spec.update(tier="U" + tier, parent=wid(v["rule"], tier), since=v.get("since"))
            W.DAILY[wid(f"{v['rule']}.{v['version']}", tier)] = spec
        W.EYE[wid("ZONE_TOUCH", tier)] = {"days": 20}
    RULES_ALL[:] = list(RULES) + [f"{v['rule']}.{v['version']}" for v in vers]
    for v in vers:
        BASELINE_OF[f"{v['rule']}.{v['version']}"] = BASELINE_OF.get(v["rule"], "RANDOM_30D")


RULES_ALL: list[str] = list(RULES)
register()


def _daily(j, coin: str) -> list[tuple]:
    from jarvis.service import feed

    return feed.daily(j, coin)


def _regime(j) -> str | None:
    from jarvis.service import watch_engine
    from src.research import reads as R

    btc = _daily(j, "BTC")
    return watch_engine.regime_at(R.Series(btc), int(j.now())) if len(btc) >= 60 else None


# ---------------------------------------------------------------------------
# daily rules on every coin
# ---------------------------------------------------------------------------
def run_rules(j) -> dict:
    from jarvis.service import registry, watch_engine

    out: dict = {}
    for tier in TIERS:
        coins = registry.members(j, tier)
        if "BTC" not in coins:
            coins = coins + ["BTC"] if tier == "A" else coins
        names = [wid(r, tier) for r in RULES_ALL + list(RANDOMS)]
        r = watch_engine.run(j, watches=names, coins=coins, daily_fn=lambda jj, c: _daily(jj, c), live_trades=False)
        r["managed_live"] = manage_live_rows(j, tier, coins)
        out[tier] = {k: len(v) if isinstance(v, list) else v for k, v in r.items()}
        out[tier]["opened_list"] = r.get("opened", [])
    return out


def manage_live_rows(j, tier: str, coins: list[str]) -> int:
    """Daily time exits and daily-low stop checks of this tier's zone touches, and of the brain's trades on coins outside the 10."""
    from jarvis.service import registry, watch_engine
    from src.research import reads as R

    labs = set(registry.lab10())
    n = 0
    for c in coins:
        rows = j.db.execute(f"SELECT {', '.join(watch_engine.COLS)} FROM evidence_trades WHERE coin=? AND status='OPEN' AND "
                            "(watch=? OR (watch IN ('JARVIS','JARVIS_RANDOM') AND ?))", (c, wid("ZONE_TOUCH", tier), c not in labs)).fetchall()
        if not rows:
            continue
        D = _daily(j, c)
        if len(D) < 30:
            continue
        S = R.Series(D)
        n += len(watch_engine._manage(j, c, D, S, R.rsi(S.c, 10), rows))
    j.db.commit()
    return n


def wake_brain(j, opened: list[dict]) -> int:
    """New signals of tier A and B coins are moments for the brain (it ranks them; random baselines never wake it)."""
    from jarvis.service import brain

    n = 0
    for o in opened:
        sp = split(o["watch"])
        if not sp or sp[0].startswith("RANDOM") or sp[1] not in ("A", "B"):
            continue
        brain.wake(j, o["coin"], f"setup:{o['watch']}", {"day": o.get("day"), "tier": sp[1]})
        n += 1
    return n


# ---------------------------------------------------------------------------
# zones for every coin (armed once a day) and the live look
# ---------------------------------------------------------------------------
def arm(j) -> dict:
    """Support zones near the price for every coin with enough history (the same live_zones code as the 10)."""
    from jarvis.service import registry, zones_watch
    from src.research import reads as R
    from src.research import zones as Z

    st = zones_watch._status(j)
    armed: dict = {"zones": {}, "atr": {}, "tier": {}, "regime": _regime(j), "t": int(time.time())}
    for c in registry.members(j):
        D = _daily(j, c)
        if len(D) < 260:
            continue
        try:
            z = Z.live_zones(D)
        except Exception:  # noqa: BLE001
            continue
        sup = []
        for r in z["zones"]:
            if r.get("side") in ("support", "here"):
                sup.append({"bot": r["bot"], "top": r["top"], "kinds": r.get("kinds"), "history": zones_watch._verdict(r["groups"], st)})
        armed["zones"][c] = sup
        armed["atr"][c] = R.Series(D).atr[-1]
        armed["tier"][c] = registry.tier_of(j, c)
    STATE.update(armed=armed, armed_t=time.time())
    try:
        (Path(j.dir) / "universe_zones.json").write_text(json.dumps(armed))
    except Exception:  # noqa: BLE001
        pass
    return {"coins": len(armed["zones"]), "zones": sum(len(v) for v in armed["zones"].values()), "regime": armed["regime"]}


def _armed(j) -> dict:
    if not STATE.get("armed"):
        p = Path(j.dir) / "universe_zones.json"
        if p.exists():
            STATE["armed"] = json.loads(p.read_text())
    return STATE.get("armed") or {}


def tick(j, px: dict[str, float]) -> dict:
    from jarvis.service import brain, registry, watch_engine

    now = int(j.now())
    armed = _armed(j)
    prev = STATE.get("prev") or {}
    labs = set(registry.lab10())
    opened, closed = [], []
    for c, zones in (armed.get("zones") or {}).items():
        p, p0 = px.get(c), prev.get(c)
        tier = (armed.get("tier") or {}).get(c)
        if p is None or p0 is None or tier not in TIERS:
            continue
        for z in zones:
            top, bot = z.get("top"), z.get("bot")
            if top is None or bot is None or not (p0 > top >= p):
                continue
            if tier in ("A", "B") and c not in labs:          # the eye already wakes the brain for the 10
                brain.wake(j, c, "zone_entry", {"zone": [bot, top], "kinds": z.get("kinds"), "history": z.get("history"), "tier": tier})
            if z.get("history") != "SUPPORTED" or armed.get("regime") != "ALLOWED":
                continue
            w = wid("ZONE_TOUCH", tier)
            same = any(abs((json.loads(dj or "{}").get("zone") or [0])[0] - bot) <= 1e-9 * max(1.0, abs(bot)) for (dj,) in
                       j.db.execute("SELECT detail FROM evidence_trades WHERE watch=? AND coin=? AND signal_t >= ?", (w, c, now - ZONE_GAP)))
            if same:
                continue
            atr = (armed.get("atr") or {}).get(c) or 0.0
            stop = round(bot - 0.5 * atr, 12) if atr else None
            t = watch_engine.open_eye_trade(j, w, c, p, stop, f"entered a {'+'.join(z.get('kinds') or []).lower() or 'support'} zone, market allowed",
                                            {"zone": [bot, top], "kinds": z.get("kinds"), "atr": atr, "tier": tier}, armed.get("regime"))
            if t:
                opened.append({"watch": w, "coin": c})
    # live stops of universe zone touches outside the 10 (the eye checks the 10 on its own prices)
    for t in watch_engine.open_with_stops(j):
        if not split(t["watch"]) or t["coin"] in labs:
            continue
        p = px.get(t["coin"])
        if p is not None and p <= t["stop"]:
            r = watch_engine.close_at(j, t["id"], p, "stop (live price)")
            if r:
                closed.append(r)
    try:
        closed += brain.manage_live(j, {c: p for c, p in px.items() if c not in labs})
    except Exception as exc:  # noqa: BLE001
        STATE["errors"]["brain_live"] = str(exc)[:160]
    STATE.update(prev=dict(px), last_tick=now)
    return {"opened": opened, "closed": closed}


# ---------------------------------------------------------------------------
# reconstruction: the rules re-run on the stored candles, compared with the ledger
# ---------------------------------------------------------------------------
def rebuild(j, days: int = 3) -> dict:
    """Every daily rule on every coin over the last N closed days, from the feed's stored candles, against the ledger.
    A rebuilt signal missing from the ledger is fine when the rule was busy (a trade already open, or the same episode);
    a ledger signal the rebuild does not find is a mismatch (data changed, code changed, or a timing slip)."""
    from jarvis.service import registry, watch_engine
    from src.research import reads as R

    btc = _daily(j, "BTC")
    if len(btc) < 60:
        return {"note": "not enough candles"}
    B = R.Series(btc)
    now = int(j.now())
    since = int(now // DAY * DAY) - days * DAY
    started = int(j.db.execute("SELECT COALESCE(MIN(signal_t), 0) FROM evidence_trades WHERE watch LIKE '%-U_'").fetchone()[0] or 0)
    since = max(since, started)
    rebuilt, explained = set(), 0
    for tier in TIERS:
        for c in registry.members(j, tier):
            D = btc if c == "BTC" else _daily(j, c)
            if len(D) < 60:
                continue
            S = B if c == "BTC" else R.Series(D)
            r10 = R.rsi(S.c, 10)
            for i in range(len(D)):
                if D[i][0] < since:
                    continue
                for rule in RULES_ALL:
                    spec = watch_engine.DAILY[wid(rule, tier)]
                    if spec["kind"] == "h07" and len(D) < 210:
                        continue
                    ok, _, _ = watch_engine._fires(spec, S, B, i, r10)
                    if ok:
                        rebuilt.add((wid(rule, tier), c, D[i][0]))
    live = {(w, c, t) for w, c, t in j.db.execute("SELECT watch, coin, signal_t FROM evidence_trades WHERE source='daily' AND signal_t >= ? "
                                                  "AND watch LIKE '%-U_' AND watch NOT LIKE 'RANDOM%'", (since,))}
    only_live = sorted(live - rebuilt)
    only_rebuilt = []
    for w, c, t in sorted(rebuilt - live):
        busy = j.db.execute("SELECT 1 FROM evidence_trades WHERE watch=? AND coin=? AND signal_t < ? AND (exit_t IS NULL OR exit_t >= ?)",
                            (w, c, t, t)).fetchone()
        ep = watch_engine.DAILY.get(w, {}).get("kind") == "read" and j.db.execute(
            "SELECT 1 FROM evidence_trades WHERE watch=? AND coin=? AND signal_t < ? AND signal_t >= ?", (w, c, t, t - watch_engine.EPISODE_DAYS * DAY)).fetchone()
        tier_now = registry.tier_of(j, c)
        if busy or ep:
            explained += 1
        elif t < started or w[-1] != (tier_now or "C"):
            explained += 1                                  # before the universe books started, or the coin changed tier
        else:
            only_rebuilt.append((w, c, t))
    res = {"t": now, "days": days, "since_day": time.strftime("%Y-%m-%d", time.gmtime(since)), "rebuilt_signals": len(rebuilt),
           "ledger_signals": len(live), "explained_by_rules": explained, "only_in_ledger": [list(x) for x in only_live[:20]],
           "only_in_rebuild": [list(x) for x in only_rebuilt[:20]], "match": not only_live and not only_rebuilt,
           "note": "Daily rules only; zone touches happen on live prices and are checked by their own stops."}
    j.db.execute("CREATE TABLE IF NOT EXISTS universe_rebuilds (t INTEGER PRIMARY KEY, json TEXT)")
    j.db.execute("INSERT OR REPLACE INTO universe_rebuilds VALUES (?,?)", (now, json.dumps(res)))
    j.db.commit()
    return res


def rebuilds(j, n: int = 30) -> list[dict]:
    try:
        return [json.loads(r[0]) for r in j.db.execute("SELECT json FROM universe_rebuilds ORDER BY t DESC LIMIT ?", (n,))]
    except Exception:  # noqa: BLE001
        return []


# ---------------------------------------------------------------------------
# the day's biggest moves across tier A and B
# ---------------------------------------------------------------------------
def missed(j, day_t: int | None = None) -> list[dict]:
    from jarvis.service import missed as M
    from jarvis.service import registry
    from src.research import reads as R

    M._table(j)
    day_t = day_t if day_t is not None else int(j.now() // DAY * DAY) - DAY
    day = time.strftime("%Y-%m-%d", time.gmtime(day_t))
    cands = []
    for c in registry.members(j, "AB"):
        D = _daily(j, c)
        k = next((i for i, b in enumerate(D) if b[0] == day_t), None)
        if k is None or k < 30:
            continue
        atr = R.Series(D[:k]).atr[-1]
        prev, bar = D[k - 1], D[k]
        pct = 100 * (bar[4] / prev[4] - 1)
        if atr and pct >= 5 and (bar[4] - prev[4]) >= atr:
            cands.append(((bar[4] - prev[4]) / atr, pct, c, D[:k], bar, atr))
    reg = _regime(j)
    out = []
    for katr, pct, c, D, bar, atr in sorted(cands, reverse=True)[:M.MAX_MOVES]:
        held = [w for (w,) in j.db.execute("SELECT DISTINCT watch FROM evidence_trades WHERE coin=? AND entry_t IS NOT NULL AND entry_t <= ? "
                                           "AND (exit_t IS NULL OR exit_t >= ?) AND watch NOT LIKE 'RANDOM%' AND watch != 'JARVIS_RANDOM'",
                                           (c, day_t + DAY, day_t))]
        seen = [r[0] for r in j.db.execute("SELECT DISTINCT trigger FROM brain_queue WHERE coin=? AND t >= ? AND t < ?", (c, day_t - DAY, day_t + DAY))]
        lo5, hi5 = min(x[3] for x in D[-5:]), max(x[2] for x in D[-5:])
        kind = "breakout" if bar[2] > hi5 else "rebound" if bar[3] <= lo5 + atr else "swing"
        label = "CAUGHT" if held else "SEEN" if seen else "MISSED"
        tier = registry.tier_of(j, c)
        row = {"id": f"{day}:UNIV:{c}", "day": day, "coin": c, "low_t": day_t, "high_t": day_t + DAY, "low": bar[3], "high": bar[2],
               "move_pct": round(pct, 2), "move_atr": round(katr, 2), "label": label, "saw": json.dumps({"traded": held, "saw": seen}),
               "kind": kind, "at_zone": None, "regime": reg, "pattern": f"{kind}|no zone|{reg or '?'}",
               "why": (f"tier {tier}: in it with " + ", ".join(held)) if held else (f"tier {tier}: the brain was woken ({', '.join(seen)[:80]}) and passed or did not reach it" if seen
                                                                                   else f"tier {tier}: no rule of ours fired on it"),
               "tier": "UNIV", "miss_class": "DECISION" if label == "SEEN" else None if label == "CAUGHT" else "DETECTION"}
        M._insert(j, row)
        out.append(row)
    j.db.commit()
    return out


# ---------------------------------------------------------------------------
# the scoreboard: rule x tier x regime against its random baseline, in market days
# ---------------------------------------------------------------------------
def _stats(rows: list[tuple]) -> dict:
    n = len(rows)
    if not n:
        return {"closed": 0, "events": 0, "avg_usd": None, "wins": 0}
    return {"closed": n, "events": len({time.strftime("%Y-%m-%d", time.gmtime(x[1])) for x in rows if x[1]}),
            "avg_usd": round(sum(x[0] for x in rows) / n, 2), "wins": sum(1 for x in rows if x[0] > 0)}


def scoreboard(j) -> dict:
    rows = j.db.execute("SELECT watch, net_usd, exit_t, regime, status FROM evidence_trades WHERE watch LIKE '%-U_'").fetchall()
    by: dict = {}
    for w, net, xt, reg, st in rows:
        sp = split(w)
        if not sp:
            continue
        rule, tier = sp
        b = by.setdefault((rule, tier), {"closed": [], "open": 0, "regimes": {}})
        if st == "CLOSED":
            b["closed"].append((net or 0.0, xt))
            b["regimes"].setdefault(reg or "?", []).append((net or 0.0, xt))
        elif st in ("OPEN", "WAITING"):
            b["open"] += 1
    out = []
    for (rule, tier), b in sorted(by.items()):
        s = _stats(b["closed"])
        base = BASELINE_OF.get(rule)
        bs = _stats(by.get((base, tier), {}).get("closed", [])) if base else None
        regs = {r: _stats(v) for r, v in b["regimes"].items()}
        vs = round(s["avg_usd"] - bs["avg_usd"], 2) if base and s["avg_usd"] is not None and bs and bs["avg_usd"] is not None else None
        both = all(regs.get(r, {}).get("events", 0) >= 1 for r in ("ALLOWED", "RISK_OFF"))
        verdict = ("baseline" if rule.startswith("RANDOM") else "watched only (tier C)" if tier == "C" else
                   f"too early: {s['events']} of {MIN_EVENTS} market days" if s["events"] < MIN_EVENTS else
                   "ahead of random" if vs is not None and vs > 0 and both else "not ahead of random" if vs is not None else "no baseline yet")
        out.append({"watch": wid(rule, tier), "rule": rule, "tier": tier, **s, "open": b["open"], "baseline": wid(base, tier) if base else None,
                    "vs_random_usd": vs, "regimes": regs, "verdict": verdict})
    return {"watches": out, "min_events": MIN_EVENTS, "would_be_account": would_be(j),
            "rule": "A rule is promoted per tier only when it beats its random baseline of the same tier after costs over 10 independent "
                    "market days in both market regimes, with Madhav's sign-off (Universe Rule v2, section 8)."}


# ---------------------------------------------------------------------------
# the promotion ladder (engine plan U6.4, Universe Rule v2 section 8)
# ---------------------------------------------------------------------------
LADDER = ("SHADOW", "EVIDENCE", "PROMOTED", "LIVE_CANDIDATE")
LADDER_WORDS = {"SHADOW": "watched and scored only", "EVIDENCE": "collecting forward evidence", "PROMOTED": "beat random; the brain ranks it higher",
                "LIVE_CANDIDATE": "may be proposed for real money, with your approval each time"}


def _ladder_table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS universe_ladder (watch TEXT PRIMARY KEY, step TEXT, by TEXT, t INTEGER, note TEXT)")


def ladder(j) -> dict:
    """Every rule x tier with its step, and whether the evidence allows the next one. Nothing moves without Madhav's sign-off."""
    _ladder_table(j)
    saved = {w: (s, by, t, note) for w, s, by, t, note in j.db.execute("SELECT watch, step, by, t, note FROM universe_ladder")}
    rows = []
    sb = scoreboard(j)
    acct = sb.get("would_be_account") or {}
    for w in sb["watches"]:
        if w["rule"].startswith("RANDOM"):
            continue
        step = saved.get(w["watch"], (None,))[0] or ("SHADOW" if w["tier"] == "C" else "EVIDENCE")
        ok, why = False, ""
        ahead = w["verdict"] == "ahead of random"
        positive = (w.get("avg_usd") or 0) > 0                  # engine fix 4: beating random while losing money is not an edge
        if w["tier"] == "C":
            why = "tier C is never judged"
        elif step == "EVIDENCE":
            ok = ahead and positive
            why = ("ahead of random over 10 market days in both regimes, and making money after costs" if ok else
                   w["verdict"] if not ahead else "ahead of random but losing money after costs")
        elif step == "PROMOTED":
            ok = ahead and positive and bool(acct.get("beats_hurdle")) and bool(acct.get("positive_expectancy"))
            why = ("still ahead, and the account makes positive R and beats the benchmark: may become a live candidate (your call)" if ok else
                   f"no longer ahead: {w['verdict']}" if not ahead else "losing money after costs" if not positive else
                   f"the account has not beaten the benchmark yet ({acct.get('return_pct')}% vs {acct.get('hurdle_pct')}%, avg R {acct.get('avg_R')})")
        rows.append({"watch": w["watch"], "rule": w["rule"], "tier": w["tier"], "step": step, "meaning": LADDER_WORDS[step],
                     "next_allowed": ok, "why": why, "signed_by": (saved.get(w["watch"]) or (None, None))[1]})
    return {"rows": rows, "steps": LADDER, "rule": "One step at a time, each with Madhav's sign-off; a step down is always allowed."}


def set_step(j, watch: str, step: str, by: str) -> dict:
    """Madhav's sign-off: move one rule x tier one step up (only when the evidence allows it) or any steps down."""
    _ladder_table(j)
    step = (step or "").upper()
    if step not in LADDER:
        raise ValueError(f"step must be one of {', '.join(LADDER)}")
    row = next((r for r in ladder(j)["rows"] if r["watch"] == watch), None)
    if not row:
        raise ValueError(f"{watch} is not a universe rule with a book")
    cur, new = LADDER.index(row["step"]), LADDER.index(step)
    if new == cur + 1 and not row["next_allowed"]:
        raise ValueError(f"not yet: {row['why']}")
    if new > cur + 1:
        raise ValueError("one step at a time")
    j.db.execute("INSERT OR REPLACE INTO universe_ladder VALUES (?,?,?,?,?)", (watch, step, by, int(j.now()), f"from {row['step']}"))
    j.db.commit()
    return {"watch": watch, "from": row["step"], "to": step, "by": by}


def promoted(j) -> set[str]:
    try:
        _ladder_table(j)
        return {w for (w,) in j.db.execute("SELECT watch FROM universe_ladder WHERE step IN ('PROMOTED', 'LIVE_CANDIDATE')")}
    except Exception:  # noqa: BLE001
        return set()


# ---------------------------------------------------------------------------
# forwarding to the repair shop by rule (engine plan U6.1)
# ---------------------------------------------------------------------------
def forward(j, rb: dict | None = None, log_request: Callable | None = None) -> list[dict]:
    """Findings that go to the repair board on their own, each once: a rebuild mismatch (data, code or timing), the ranking
    throwing away moves that ran, and feed trouble. Missed-move repeats are forwarded by the missed-move loop (tier UNIV)."""
    from jarvis.service import brain, feed, requests_log

    add = log_request or (lambda kind, text, about: requests_log.add(j, kind, text, about, by="ananta-auto"))
    day = time.strftime("%Y-%m-%d", time.gmtime(j.now()))
    out = []

    def once(key: str, kind: str, text: str, about: str):
        k = f"universe:forward:{key}"
        if j.db.execute("SELECT 1 FROM engine_state WHERE k=?", (k,)).fetchone():
            return
        r = add(kind, text, about)
        j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", (k, str(r.get("num") if isinstance(r, dict) else "")))
        j.db.commit()
        out.append({"key": key, "request": r.get("num") if isinstance(r, dict) else None})

    if rb and not rb.get("match", True):
        once(f"rebuild:{day}", "bug", f"Universe rebuild on {day} did not match the ledger: {len(rb.get('only_in_ledger') or [])} signals only in "
             f"the ledger, {len(rb.get('only_in_rebuild') or [])} only in the rebuild (first: {(rb.get('only_in_ledger') or rb.get('only_in_rebuild'))[:3]}). "
             "Check whether the candles changed, the code changed, or a run was late.", "universe rebuild")
    try:
        a = brain.ranking_audit(j)
        u, p = a["not_reviewed"], a["passed"]
        if u["n"] >= 20 and p["n"] >= 10 and u["ran_5pct"] / u["n"] > p["ran_5pct"] / p["n"] + 0.10:
            week = time.strftime("%G-W%V", time.gmtime(j.now()))
            once(f"ranking:{week}", "idea", f"The brain's ranking may be throwing away good moments: {u['ran_5pct']} of {u['n']} wakes it never "
                 f"reviewed ran 5% or more within 5 days, against {p['ran_5pct']} of {p['n']} it looked at and passed. Review the ranking points.",
                 "brain ranking")
    except Exception:  # noqa: BLE001
        pass
    last = (feed.STATE.get("last") or {}).get("m5") or {}
    if last.get("coins") and last.get("on_time", 0) < 0.95 * last["coins"]:
        once(f"feed:{day}", "data", f"The universe feed was late on {day}: {last.get('on_time')} of {last.get('coins')} coins had their last "
             f"5-minute candle on time (errors: {list((feed.STATE.get('errors') or {}).keys())}).", "universe feed")
    return out


# ---------------------------------------------------------------------------
# the daily round and status
# ---------------------------------------------------------------------------
MAX_OPEN_ACCOUNT, MAX_SAME_DAY, ACCOUNT_USD = 20, 5, 2000.0
RISK_PCT, MAX_RISK_PCT, MAX_POS_PCT, DEFAULT_STOP = 0.5, 6.0, 20.0, 0.08     # engine fix 4: risk per trade, total open risk, one coin, stop if none


def would_be(j) -> dict:
    """What a real $2,000 account would have done with the same signals (engine plan U4.2, engine fixes 1 and 4):
    tier A and B rule signals and zone touches in time order; no new buy on a day the exposure dial was closed unless that rule has
    a measured edge in a closed market (review #26); at most 20 open, one per coin, 5 new a day; each trade risks 0.5% of the
    account (size = risk / distance to its stop, 8% when it has none, at most 20% of the account in one coin) and all open trades
    together at most 6%. Results in R (one R = the amount risked), compared with the benchmark (Bitcoin above its 50-day average)
    over the same days: the hurdle."""
    from jarvis.service import ev, exposure

    rows = j.db.execute("SELECT watch, coin, entry_t, exit_t, net_usd, status, entry, stop FROM evidence_trades "
                        "WHERE watch LIKE '%-U_' AND watch NOT LIKE 'RANDOM%' AND entry_t IS NOT NULL ORDER BY entry_t").fetchall()
    try:
        dial = exposure.dial_by_day(j)
    except Exception:  # noqa: BLE001
        dial = {}
    open_, taken, per_day = [], [], {}
    skipped = {"dial_closed": 0, "full": 0, "same_coin": 0, "same_day": 0, "risk_cap": 0}
    for w, c, et, xt, net, st, entry, stop in rows:
        sp = split(w)
        if not sp or sp[1] == "C":
            continue
        open_ = [o for o in open_ if o[2] is None or o[2] > et]
        day = time.strftime("%Y-%m-%d", time.gmtime(et))
        dist = (entry - stop) / entry if entry and stop and 0 < stop < entry else DEFAULT_STOP
        risk = ACCOUNT_USD * RISK_PCT / 100
        size = min(ACCOUNT_USD * MAX_POS_PCT / 100, risk / dist)
        risk = size * dist
        if dial.get(day) == 0 and ev.value(sp[0].split(".")[0], "CLOSED", sp[1]) <= 0:
            skipped["dial_closed"] += 1
        elif len(open_) >= MAX_OPEN_ACCOUNT:
            skipped["full"] += 1
        elif any(o[0] == c for o in open_):
            skipped["same_coin"] += 1
        elif per_day.get(day, 0) >= MAX_SAME_DAY:
            skipped["same_day"] += 1
        elif sum(o[3] for o in open_) + risk > ACCOUNT_USD * MAX_RISK_PCT / 100:
            skipped["risk_cap"] += 1
        else:
            open_.append((c, et, xt, risk))
            per_day[day] = per_day.get(day, 0) + 1
            frac = (net or 0.0) / 100.0                 # the evidence ledger stakes $100 a trade
            taken.append({"watch": w, "coin": c, "t": et, "status": st, "usd": size * frac, "R": frac / dist})
    closed = [x for x in taken if x["status"] == "CLOSED"]
    pnl = round(sum(x["usd"] for x in closed), 2)
    ret = round(100 * pnl / ACCOUNT_USD, 2)
    avg_r = round(sum(x["R"] for x in closed) / len(closed), 3) if closed else None
    hurdle = None
    if taken:
        try:
            hurdle = exposure.hurdle_since(j, taken[0]["t"])
        except Exception:  # noqa: BLE001
            hurdle = None
    return {"account_usd": ACCOUNT_USD, "taken": len(taken), "closed": len(closed), "open": len(taken) - len(closed), "skipped": skipped,
            "net_usd": pnl, "return_pct": ret, "avg_R": avg_r, "total_R": round(sum(x["R"] for x in closed), 2),
            "hurdle_pct": hurdle, "beats_hurdle": (ret > hurdle) if hurdle is not None and closed else None,
            "positive_expectancy": (avg_r > 0) if avg_r is not None else None,
            "rules": f"no new buys while the exposure dial is closed (except measured edges), at most {MAX_OPEN_ACCOUNT} open, one per coin, "
                     f"{MAX_SAME_DAY} new a day, {RISK_PCT}% of the account risked a trade, {MAX_RISK_PCT:g}% open risk in total, tiers A and B only",
            "how_to_read": "R is the result in units of the amount risked. The account must show positive R AND beat the benchmark "
                           "(Bitcoin above its 50-day average) over the same days before anything is proposed for real money."}


def run_daily(j) -> dict:
    """Called by the feed after the daily candles land (and safe to call any time: every step catches up on its own).
    The rebuild covers the last 3 days each night and everything since the start on Mondays (the weekly full rebuild)."""
    out: dict = {}
    full = time.gmtime(j.now()).tm_wday == 0
    for name, fn in (("rules", lambda: run_rules(j)), ("arm", lambda: arm(j)), ("rebuild", lambda: rebuild(j, 400 if full else 3)),
                     ("missed", lambda: [r["coin"] + " " + r["label"] for r in missed(j)])):
        t0 = time.time()
        try:
            out[name] = fn()
        except Exception as exc:  # noqa: BLE001  one step failing never stops the others
            out[name] = {"error": str(exc)[:200]}
        out[name + "_s"] = round(time.time() - t0, 1)
    try:
        opened = [o for t in TIERS for o in ((out.get("rules") or {}).get(t) or {}).get("opened_list", [])]
        out["brain_woke"] = wake_brain(j, opened)
    except Exception as exc:  # noqa: BLE001
        out["brain_error"] = str(exc)[:200]
    for t in TIERS:
        ((out.get("rules") or {}).get(t) or {}).pop("opened_list", None)
    try:
        out["forwarded"] = forward(j, out.get("rebuild") if isinstance(out.get("rebuild"), dict) else None)
    except Exception as exc:  # noqa: BLE001
        out["forward_error"] = str(exc)[:200]
    try:
        _daily_file(j, out)
    except Exception:  # noqa: BLE001
        pass
    for t in TIERS:
        ((out.get("rules") or {}).get(t) or {}).pop("opened_list", None)
    STATE["last_daily"] = {"t": int(time.time()), **{k: v for k, v in out.items() if k != "missed"}}
    return out


def _daily_file(j, out: dict) -> None:
    """The night's universe round in plain words, beside the daily review the 7:25 am task writes (engine plan U5.4)."""
    from jarvis.service.core import docs_dir

    day = time.strftime("%Y-%m-%d", time.gmtime(j.now()))
    p = docs_dir(j.dir) / "repair_shop" / "daily" / f"universe_{day}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    sb = [w for w in scoreboard(j)["watches"] if w["closed"] or w["open"]]
    rb = out.get("rebuild") if isinstance(out.get("rebuild"), dict) else {}
    lines = [f"# Universe round, {day}", "", f"Coins: {status(j).get('counts')}", "",
             "## Rules on every coin", ""] + [f"- tier {t}: {(out.get('rules') or {}).get(t)}" for t in TIERS] + [
             "", "## Rebuild", "", f"- {rb.get('rebuilt_signals')} signals rebuilt, {rb.get('ledger_signals')} in the ledger, match: {rb.get('match')}", "",
             "## Biggest up-days (tier A and B)", ""] + [f"- {m}" for m in (out.get("missed") or [])] + [
             "", "## Scoreboard (rule x tier, market days)", "", "| watch | closed | market days | avg $/100 | vs random | open | verdict |", "|---|---|---|---|---|---|---|"] + [
             f"| {w['watch']} | {w['closed']} | {w['events']} | {w['avg_usd']} | {w['vs_random_usd']} | {w['open']} | {w['verdict']} |" for w in sb] + [
             "", f"Forwarded to the repair shop: {out.get('forwarded') or 'nothing'}", ""]
    p.write_text("\n".join(lines))


def coins(j, tier: str | None = None, q: str | None = None, sort: str = "trading", n: int = 60) -> dict:
    """Every watched coin for the app and Ask: tier, live price, today's change, the nearest support zone, can-buy flags.
    sort: trading (biggest first), up / down (today's change), near (closest above a support zone a history supports)."""
    from jarvis.service import feed, registry

    reg = registry.load(j).get("coins", {})
    px = feed.prices(j)
    armed = _armed(j)
    last = feed.last_closes(j)
    rows = []
    for c in registry.members(j, (tier or "").upper() or None):
        if q and q.upper() not in c:
            continue
        k = reg.get(c) or {}
        p = px.get(c)
        chg = round(100 * (p / last[c] - 1), 2) if p and last.get(c) else None
        near = None
        for z in (armed.get("zones") or {}).get(c) or []:
            if p and z.get("history") == "SUPPORTED" and z["top"] and p >= z["bot"]:
                d = round(100 * (p / z["top"] - 1), 2)
                if near is None or d < near["above_pct"]:
                    near = {"above_pct": max(d, 0.0), "zone": [z["bot"], z["top"]], "kinds": z.get("kinds")}
        rows.append({"coin": c, "name": k.get("name"), "tier": k.get("tier"), "price": p, "change_today_pct": chg, "median_daily_usd_30d": k.get("median_usd_30d"),
                     "ndax": k.get("ndax"), "kraken": k.get("kraken"), "groups": k.get("groups") or [], "near_zone": near})
    if sort == "up":
        rows.sort(key=lambda r: -(r["change_today_pct"] if r["change_today_pct"] is not None else -1e9))
    elif sort == "down":
        rows.sort(key=lambda r: (r["change_today_pct"] if r["change_today_pct"] is not None else 1e9))
    elif sort == "near":
        rows = [r for r in rows if r["near_zone"]]
        rows.sort(key=lambda r: r["near_zone"]["above_pct"])
    return {"count": len(rows), "coins": rows[:max(1, min(int(n or 60), 600))], "counts": registry.load(j).get("counts"),
            "note": "Every coin trading on Binance against USDT, minus stablecoins, wrapped and leveraged tokens (Universe Rule v2). "
                    "Tier A trades over $20M a day, B $1M-$20M, C under $1M (watched, never judged). Paper only."}


def status(j) -> dict:
    from jarvis.service import feed, registry

    reg = registry.load(j)
    armed = _armed(j)
    open_n = j.db.execute("SELECT COUNT(*) FROM evidence_trades WHERE watch LIKE '%-U_' AND status IN ('OPEN','WAITING')").fetchone()[0]
    closed_n = j.db.execute("SELECT COUNT(*) FROM evidence_trades WHERE watch LIKE '%-U_' AND status='CLOSED'").fetchone()[0]
    rb = rebuilds(j, 1)
    return {"counts": reg.get("counts"), "built_at": reg.get("built_at"), "feed": feed.status(j),
            "zones_armed": {"coins": len(armed.get("zones") or {}), "regime": armed.get("regime")},
            "trades": {"open_or_waiting": open_n, "closed": closed_n}, "last_rebuild": rb[0] if rb else None,
            "last_daily": STATE.get("last_daily"), "rule_doc": "docs/UNIVERSE_RULE_V2.md"}
