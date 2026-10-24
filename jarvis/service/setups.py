"""The setups board (Madhav, 24 Oct 2026 10:42: "make sure we are tracking the market completely, looking for good trade setups").

The data side already covers the market (every coin priced every few seconds, daily candles for all of tier A and B); what was missing
was a scan that LOOKS for setups: the brain only heard about zone touches and Explorer hits, which the registry rightly screens out,
so 25 decisions in 7 days were all passes. The board scans every tier A and B coin after each daily close, for every family that is
measured or on trial, and ranks what it finds. Rules, not AI: no model call here.

  build(j)     after the daily close: every coin x family -> FIRED (the rule's condition is met on tonight's close) or CLOSE (one step
               away, with the price that would trigger it), its invalidation (the stop) and the evidence behind the family. The best FIRED
               rows (at most WAKE_MAX a night, inside the selection floor) wake the brain, which decides with every rule and red flag.
  live(j)      every 15 minutes: a CLOSE row whose trigger price the live price has crossed is marked "touched today"; on tier A it wakes the
               brain once (at most LIVE_MAX a day). Nothing is bought here.
  latest(j)    the newest board, for Home, the plan line, the officer and the voice.

Families (each says what its evidence is; none of the shadow ones may buy for the account):
  H07   a close above the 200-day average with RSI(10) under 30: the one measured edge (tier A while the dial is CLOSED, review #26)
  BRK   a close at a 20-session high on 1.5x volume: shadow since 24 Oct (review #21's prior is negative for zone breakouts)
  RBD   a reversal candle off a recent low at a support zone, market allowed: shadow since 24 Oct (the move we keep missing)
  PULL  a pullback to the 20-day average inside an uptrend, momentum cooled (RSI 40-55): never measured as a family; the brain's TREND plan
Paper and research only.
"""
from __future__ import annotations

import json
import time

DAY = 86400
WAKE_MAX = 5
LIVE_MAX = 3
TIERS = ("A", "B")
EVIDENCE = {"H07": "the one measured edge: tier A while the dial is closed (review #26); elsewhere no measured edge",
            "BRK": "on trial (shadow) since 24 Oct; review #21 found zone breakouts on volume failed on every tier",
            "RBD": "on trial (shadow) since 24 Oct; the move we keep missing (3 times in 30 days, about +5% on average)",
            "PULL": "never measured as a family; the brain's TREND plan (a coin in its own uptrend)"}
NAMES = {"H07": "short dip in an uptrend", "BRK": "breakout to a 20-day high on volume", "RBD": "rebound off a recent low at support",
         "PULL": "pullback to the 20-day average in an uptrend"}
WEIGHT = {"H07": 1.0, "BRK": 1.0, "RBD": 1.0, "PULL": 1.0}


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS setups_board (day TEXT PRIMARY KEY, t INTEGER, summary TEXT, rows TEXT)")
    j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")


def _sma(x, n, i):
    return sum(x[i - n + 1:i + 1]) / n if i + 1 >= n else None


def _rows_for(c: str, tier: str, D: list[tuple], btc_c: dict, zones: list[dict] | None, dial: str | None, regime_ok: bool) -> list[dict]:
    """Every family's state on one coin's last closed day."""
    from jarvis.service import discipline
    from src.research import reads as R

    if len(D) < 60:
        return []
    S = R.Series(D)
    i = len(D) - 1
    c0, o0, h0, l0 = S.c[i], S.o[i], S.h[i], S.l[i]
    atr = S.atr[i] or 0.0
    if not atr or not c0:
        return []
    ema50, sma200, sma20 = S.ema50[i], S.sma200[i], _sma(S.c, 20, i)
    r10 = R.rsi(S.c, 10)[i]
    r14 = S.rsi[i]
    vols = [v for v in S.v[i - 20:i] if v]
    vol_x = (S.v[i] / (sum(vols) / len(vols))) if vols and S.v[i] else None
    up = bool(ema50 and sma200 and c0 > ema50 and c0 > sma200)
    b20 = btc_c.get(D[i - 20][0]) if i >= 20 else None
    bnow = btc_c.get(D[i][0])
    rs20 = (c0 / S.c[i - 20] - 1) - (bnow / b20 - 1) if (i >= 20 and b20 and bnow) else None
    leader = bool(rs20 is not None and rs20 >= 0.05 and ema50 and c0 > ema50)
    trend = ("uptrend (above its 50- and 200-day)" if up else "above its 50-day only" if ema50 and c0 > ema50 else
             "under its 50-day" if ema50 else "young coin")
    base = {"coin": c, "tier": tier, "price": c0, "rs20": round(rs20, 4) if rs20 is not None else None, "leader": leader, "trend": trend,
            "vol_x": round(vol_x, 2) if vol_x else None, "atr_pct": round(atr / c0, 4)}
    out = []

    def add(fam, state, trigger, trigger_px, stop, why):
        flags: list[str] = []
        stop_pct = (c0 - stop) / c0 if stop else None
        floor = discipline.selection_floor(tier, c0, None, stop) if stop else []
        s = WEIGHT[fam] + (1.0 if tier == "A" else 0.5) + (1.0 if leader else 0.0) + (1.0 if up else 0.0)
        if fam == "H07" and tier == "A" and dial == "CLOSED":
            s += 3.0                                              # the measured cell
        elif fam != "H07":
            s += {"CONFIRMED": 1.0, "FRAGILE": 0.5}.get(dial or "", 0.0)
        if state == "FIRED":
            s += 2.0
        if floor:
            s -= 3.0
        # what the brain's first passes on the board taught (24 Oct, INIT/VTHO/ICP/WLFI): a stretched breakout and a rebound under its own
        # 50-day or lagging Bitcoin are ordinary days, so they rank lower; they still show, and their books still measure them
        if fam == "BRK" and ((r14 or 0) > 70 or (ema50 and c0 > 1.3 * ema50)):
            s -= 1.5
            flags.append("stretched: RSI over 70 or 30% above its 50-day")
        if fam == "RBD":
            if ema50 and c0 < ema50:
                s -= 1.0
                flags.append("under its own 50-day")
            if rs20 is not None and rs20 < 0:
                s -= 0.5
                flags.append("weaker than Bitcoin over 20 days")
        out.append({**base, "family": fam, "name": NAMES[fam], "state": state, "trigger": trigger, "trigger_px": trigger_px,
                    "stop": round(stop, 10) if stop else None, "stop_pct": round(stop_pct, 4) if stop_pct is not None else None,
                    "why": why, "evidence": EVIDENCE[fam], "floor": floor, "flags": flags, "score": round(s, 2)})

    # H07: above the 200-day, RSI(10) under 30 (CLOSE under 36); no stop by design (review #27), invalidation 2 daily ranges under
    if sma200 and c0 > sma200 and r10 is not None:
        if r10 < 30:
            add("H07", "FIRED", "tonight's close", None, None, f"RSI(10) {r10:.0f}, above its 200-day average")
        elif r10 < 36:
            add("H07", "CLOSE", "RSI(10) under 30 on a close above the 200-day", None, None, f"RSI(10) {r10:.0f}, close to 30")
    # BRK: a close above every close of the last 20 sessions on 1.5x volume (CLOSE: within 3% of that high)
    if i >= 21:
        hi20 = max(S.c[i - 20:i])
        if c0 > hi20 and vol_x and vol_x >= 1.5:
            add("BRK", "FIRED", "tonight's close", None, c0 * 0.92, f"closed at a 20-session high on {vol_x:.1f}x volume")
        elif hi20 >= c0 >= hi20 * 0.97:
            add("BRK", "CLOSE", f"a daily close above {hi20:,.6g} on 1.5x volume", hi20, hi20 * 0.92,
                f"{100 * (hi20 / c0 - 1):.1f}% under its 20-session closing high")
    # RBD: the day's low is the 5-day low, at a support zone (mapped from the closes before tonight, as the evidence book does), then a
    # reversal candle; market allowed. The zone map is only built for a coin at its 5-day low (the expensive part).
    if i >= 260 and l0 <= min(S.l[i - 4:i + 1]) + 0.25 * atr:
        if zones is None:
            from src.research import zones as Z

            try:
                zones = Z.live_zones(D[:-1])["zones"]
            except Exception:  # noqa: BLE001
                zones = []
        at = next((z for z in zones if z["bot"] - 0.5 * atr <= l0 <= z["top"] + 0.5 * atr), None)
        if at:
            stop = l0 - 0.5 * atr
            zw = "+".join(at.get("kinds") or []).lower() or "support"
            if regime_ok and c0 > o0 and c0 >= l0 + 0.6 * (h0 - l0):
                add("RBD", "FIRED", "tonight's close", None, stop, f"a reversal candle off its 5-day low at a {zw} zone")
            elif regime_ok and rs20 is not None and rs20 >= 0:      # only coins holding up against Bitcoin: a falling knife is not "close"
                add("RBD", "CLOSE", f"a green daily close in the top 40% of the day, holding above {stop:,.6g}", None, stop,
                    f"at its 5-day low inside a {zw} zone, no reversal candle yet")
    # PULL: uptrend, the 20-day above the 50-day, the close within 1 daily range of the 20-day, RSI(14) 40-55
    if up and sma20 and ema50 and sma20 > ema50 and r14 is not None and abs(c0 - sma20) <= atr and 40 <= r14 <= 55:
        stop = max(ema50 - 0.5 * atr, c0 - 1.5 * atr) if c0 - ema50 < 3 * atr else c0 - 1.5 * atr
        trig = h0
        if c0 > S.h[i - 1]:
            add("PULL", "FIRED", "tonight's close", None, stop, f"back above yesterday's high after a pullback to the 20-day (RSI {r14:.0f})")
        else:
            add("PULL", "CLOSE", f"a daily close above {trig:,.6g} (today's high)", trig, stop, f"pulled back to its 20-day average, RSI {r14:.0f}")
    return out


def build(j, wake: bool = True) -> dict:
    """Tonight's board: every tier A and B coin, every family; the best FIRED rows wake the brain."""
    from jarvis.service import brain, discipline, feed, registry, watch_engine
    from src.research import reads as R

    _table(j)
    now = int(j.now())
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    btc = feed.daily(j, "BTC")
    btc_c = {b[0]: b[4] for b in btc}
    dial = discipline.dial_state([b[4] for b in btc]) if btc else None
    regime_ok = bool(btc) and watch_engine.regime_at(R.Series(btc), btc[-1][0]) == "ALLOWED" if len(btc) >= 60 else False
    rows: list[dict] = []
    scanned = 0
    for tier in TIERS:
        for c in registry.members(j, tier):
            D = feed.daily(j, c)
            if not D or now - D[-1][0] > 2 * DAY + 3 * 3600:
                continue
            scanned += 1
            try:
                rows += _rows_for(c, tier, D, btc_c, None, dial, regime_ok)
            except Exception:  # noqa: BLE001  one coin never stops the board
                continue
    rows.sort(key=lambda r: (-r["score"], r["coin"]))
    fired = [r for r in rows if r["state"] == "FIRED"]
    close = [r for r in rows if r["state"] == "CLOSE"]
    woke = []
    if wake:
        try:
            held = {c for (c,) in j.db.execute("SELECT DISTINCT coin FROM evidence_trades WHERE watch='JARVIS' AND status='OPEN'").fetchall()}
        except Exception:  # noqa: BLE001  no book yet
            held = set()
        for r in [r for r in fired if not r["floor"] and r["coin"] not in held][:WAKE_MAX]:   # a coin the brain holds is not news to it
            try:
                if brain.wake(j, r["coin"], f"board:{r['family']}", {"board": {k: r[k] for k in ("family", "name", "why", "stop", "stop_pct", "evidence", "trend", "rs20", "flags")}}):
                    woke.append(f"{r['coin']} {r['family']}")
            except Exception:  # noqa: BLE001
                continue
    leaders = sorted([r for r in rows if r["leader"]], key=lambda r: -(r["rs20"] or 0))
    seen, lead = set(), []
    for r in leaders:
        if r["coin"] not in seen:
            seen.add(r["coin"])
            lead.append({"coin": r["coin"], "tier": r["tier"], "rs20": r["rs20"]})
    summary = {"day": day, "dial": dial, "market_allowed": regime_ok, "scanned": scanned, "fired": len(fired), "close": len(close),
               "by_family": {f: {"fired": sum(1 for r in fired if r["family"] == f), "close": sum(1 for r in close if r["family"] == f)} for f in NAMES},
               "top": [{k: r[k] for k in ("coin", "tier", "family", "state", "score", "why", "trigger", "stop_pct")} for r in rows[:5]],
               "leaders": lead[:8], "woke": woke, "words": words(fired, close, scanned, dial, lead)}
    j.db.execute("INSERT OR REPLACE INTO setups_board VALUES (?,?,?,?)", (day, now, json.dumps(summary, default=str), json.dumps(rows[:200], default=str)))
    j.db.commit()
    return summary


def words(fired: list[dict], close: list[dict], scanned: int, dial: str | None, lead: list[dict]) -> str:
    def name(r):
        return f"{r['coin']} ({NAMES[r['family']]})"
    s = f"Scanned {scanned} coins: {len(fired)} setups fired, {len(close)} one step away."
    ok = [r for r in fired if not r["floor"]]
    if ok:
        s += " Best: " + ", ".join(name(r) for r in ok[:3]) + "."
    elif close:
        s += " Closest: " + ", ".join(name(r) for r in close[:3]) + "."
    if lead:
        s += " Strongest against Bitcoin over 20 days: " + ", ".join(x["coin"] for x in lead[:3]) + "."
    return s


def latest(j) -> dict | None:
    _table(j)
    r = j.db.execute("SELECT summary, rows FROM setups_board ORDER BY day DESC LIMIT 1").fetchone()
    if not r:
        return None
    return {**json.loads(r[0]), "rows": json.loads(r[1])}


def live(j) -> list[dict]:
    """Every 15 minutes: CLOSE rows whose price trigger the live price crossed. Marked once a day; tier A wakes the brain (LIVE_MAX a day)."""
    from jarvis.service import brain, feed

    b = latest(j)
    if not b:
        return []
    day = time.strftime("%Y-%m-%d", time.gmtime(j.now()))
    px = feed.prices(j)
    out, woke_today = [], 0
    try:
        woke_today = j.db.execute("SELECT COUNT(*) FROM engine_state WHERE k LIKE ? AND v LIKE '%\"woke\": true%'", (f"board_live:{day}:%",)).fetchone()[0]
    except Exception:  # noqa: BLE001
        pass
    for r in b["rows"]:
        if r["state"] != "CLOSE" or not r.get("trigger_px") or r["floor"]:
            continue
        p = px.get(r["coin"])
        if p is None or p < r["trigger_px"]:
            continue
        k = f"board_live:{day}:{r['coin']}:{r['family']}"
        if j.db.execute("SELECT 1 FROM engine_state WHERE k=?", (k,)).fetchone():
            continue
        wake = r["tier"] == "A" and woke_today < LIVE_MAX
        if wake:
            try:
                wake = bool(brain.wake(j, r["coin"], f"board_live:{r['family']}", {"board": {"family": r["family"], "why": r["why"] + f"; the live price {p:,.6g} is over the trigger {r['trigger_px']:,.6g} (not a daily close yet)", "stop": r["stop"]}}))
            except Exception:  # noqa: BLE001
                wake = False
            woke_today += int(wake)
        j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", (k, json.dumps({"t": int(j.now()), "px": p, "woke": wake})))
        out.append({"coin": r["coin"], "family": r["family"], "price": p, "trigger_px": r["trigger_px"], "woke": wake})
    if out:
        j.db.commit()
    return out


def touched_today(j) -> list[dict]:
    day = time.strftime("%Y-%m-%d", time.gmtime(j.now()))
    try:
        rows = j.db.execute("SELECT k, v FROM engine_state WHERE k LIKE ?", (f"board_live:{day}:%",)).fetchall()
    except Exception:  # noqa: BLE001
        return []
    out = []
    for k, v in rows:
        _, _, coin, fam = k.split(":", 3)
        out.append({"coin": coin, "family": fam, **json.loads(v)})
    return out
