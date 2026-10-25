"""The trader's discipline (Madhav, 2026-10-24 01:13 Toronto: "Yes to all" to the ten items of the brutal 7-day review,
claude/review-2026-10-24-crypto-7-days-brutal.md). The numbers live in docs/knowledge/discipline_v1.json and move only with a new
history entry there.

  protect(entry, stop0, high, stop)   item 3: the protect rule for any paper trade that has a stop (+1.5 R: stop to the entry;
                                      +2.5 R: trail 1 R under the high). Returns (new stop, rule words or None).
  dial_state(closes)                  item 4: CLOSED / FRAGILE / CONFIRMED from Bitcoin's daily closes (50- and 200-day averages)
  core_targets(state, value)          item 4: the core's target value per coin, the cash target and the tranche size
  selection_floor(tier, px, top, stop) item 7: the brain's floor, as flags (empty = allowed)
  wait_for_arrived(j)                 item 6: yesterday's PASS wait_for conditions that came true on today's close
  officer_checks(j)                   item 8: the officer's checks with a state each (OK / FAIL / UNKNOWN)
  plan_line(j)                        item 5: one plan sentence for the night, and the layer conflicts behind it (the stance wins)

Paper only: nothing here reads the broker or writes an order. The $500 book applies core_targets itself (ndax_book.step).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

DAY = 86400
_CACHE: dict = {"m": None, "v": {}}
STATES = ("CLOSED", "FRAGILE", "CONFIRMED")
STATE_WORDS = {"CLOSED": "the dial is closed (Bitcoin under its 50- or 200-day average)",
               "FRAGILE": "the dial is open but fragile (Bitcoin less than 3% above its 50-day average)",
               "CONFIRMED": "the dial is open and confirmed (Bitcoin 3% or more above its 50-day average)"}


def _path() -> Path:
    from jarvis.service.core import docs_dir

    return docs_dir(".") / "knowledge" / "discipline_v1.json"


def rules() -> dict:
    p = _path()
    try:
        m = p.stat().st_mtime
    except OSError:
        return {}
    if _CACHE["m"] != m:
        _CACHE.update(m=m, v=json.loads(p.read_text()))
    return _CACHE["v"]


def version() -> str:
    return str(rules().get("version") or "discipline-v1")


# ------------------------------------------------------------------------------------------------------------ item 3: protect

def protect(entry: float, stop0: float | None, high: float | None, stop: float | None) -> tuple[float | None, str | None]:
    """The protect rule. R is the first risk unit (entry - first stop); a trade with no stop under its entry is left alone.
    (new stop, the rule applied) or (the old stop, None) when nothing changes. A stop only ever moves up."""
    p = rules().get("protect") or {}
    be, tf, tb = float(p.get("breakeven_r", 1.5)), float(p.get("trail_from_r", 2.5)), float(p.get("trail_by_r", 1.0))
    try:
        entry, stop0 = float(entry), float(stop0) if stop0 else 0.0
    except (TypeError, ValueError):
        return stop, None
    if not stop0 or stop0 >= entry or high is None:
        return stop, None
    r = entry - stop0
    gain = (float(high) - entry) / r
    if gain >= tf:
        cand, words = float(high) - tb * r, f"protect: trails {tb:g} R under the high from +{tf:g} R"
    elif gain >= be:
        cand, words = entry, f"protect: stop to the entry at +{be:g} R"
    else:
        return stop, None
    if stop is None or cand > float(stop):
        return round(cand, 12), words
    return stop, None


def protect_books(watch: str, source: str | None) -> bool:
    """Which rows the protect rule touches: every paper trade with a stop except the $500 account's own positions (item 4 has
    its rules) and the random baselines without stops (they have none, so protect() leaves them alone anyway)."""
    return watch != "BOOK500"


# ------------------------------------------------------------------------------------------------------------ item 4: the core

def _sma(x: list[float], n: int) -> float | None:
    return sum(x[-n:]) / n if len(x) >= n else None


def _ema(x: list[float], n: int) -> float | None:
    if len(x) < n:
        return None
    k, e = 2 / (n + 1), sum(x[:n]) / n
    for v in x[n:]:
        e = v * k + e * (1 - k)
    return e


def dial_state(closes: list[float]) -> str | None:
    """CLOSED / FRAGILE / CONFIRMED from Bitcoin's daily closes (the dial's own averages: EMA 50 and SMA 200, review #25, as
    book500.dial_open and watch_engine.regime_at read them); None without 200 closes."""
    if len(closes) < 200:
        return None
    return dial_state_from(closes[-1], _ema(closes, 50), _sma(closes, 200))


def dial_state_from(close: float, ema50: float | None, sma200: float | None) -> str | None:
    if ema50 is None or sma200 is None:
        return None
    if not (close > ema50 and close > sma200):
        return "CLOSED"
    frac = float((rules().get("core") or {}).get("fragile_pct_over_50d", 0.03))
    return "CONFIRMED" if close / ema50 - 1 >= frac else "FRAGILE"


def core_targets(state: str | None, value: float, weights: dict[str, float], tranches_done: int = 0,
                 held: dict[str, float] | None = None) -> dict:
    """The core's plan for one session, read from the cash target Madhav approved (CLOSED 70%, FRAGILE 40%, CONFIRMED 15%).
    weights = the full core weights (BTC 0.40, ETH 0.20); held = the core's value now per coin (CAD).
      cap     the most the core may hold: min(full weights, 1 - cash target) of the book, split by the weights. Above cap + the trim
              band the core is trimmed back to cap (one trim a session); never below it (24 Oct fix: a fragile dial is not a sell signal,
              the coin's own close under its 50-day average is).
      next    what the core may hold after tonight's buys: FRAGILE holds what it has (no adds), or a first fill of at most first_fill_max
              if it holds nothing; CONFIRMED adds the next third, the first at most first_fill_max; CLOSED nothing.
    Returns {"state", "target" (= cap), "next", "cash_target", "tranche_frac", "words", "trim_band"}."""
    cr = rules().get("core") or {}
    n = int(cr.get("tranches", 3))
    cash = float((cr.get("cash_target") or {}).get(state or "CLOSED", 0.7))
    held = held or {}
    full = sum(weights.values()) or 1.0
    room = 0.0 if state not in ("FRAGILE", "CONFIRMED") else min(full, 1.0 - cash)
    cap = {c: round(value * room * w / full, 2) for c, w in weights.items()}
    first_max = float(cr.get("first_fill_max", 0.20))
    first = {c: round(value * min(first_max, room) * w / full, 2) for c, w in weights.items()}
    has_core = sum(held.values()) > 0.01 * value
    if state == "CONFIRMED":
        if not has_core or tranches_done == 0:
            nxt, frac = first, min(first_max, room) / full
        else:
            frac = min(1.0, (min(tranches_done, n) + 1) / n)
            nxt = {c: min(cap[c], round(value * w * frac, 2)) for c, w in weights.items()}
    elif state == "FRAGILE":
        nxt = {c: min(cap[c], round(held.get(c, 0.0), 2)) for c in weights} if has_core else first
        frac = (sum(nxt.values()) / value / full) if value else 0.0
    else:
        nxt, frac = {c: 0.0 for c in weights}, 0.0
    words = {"CLOSED": "no core: cash",
             "FRAGILE": ("hold the core as it is, no adds until the dial is confirmed" if has_core
                         else f"a first buy of at most {100 * first_max:.0f}% of the book, no more until the dial is confirmed"),
             "CONFIRMED": (f"the first third, at most {100 * first_max:.0f}% of the book" if not has_core or tranches_done == 0 else
                           f"third {min(tranches_done + 1, n)} of {n} after a daily close above the 20-day average")}.get(state or "CLOSED", "no core")
    return {"state": state, "target": cap, "next": nxt, "cash_target": cash, "tranche_frac": round(frac, 4), "words": words,
            "trim_band": float(cr.get("trim_band", 0.05))}


# ------------------------------------------------------------------------------------------------------------ item 7: the floor

def selection_floor(tier: str | None, price: float | None, zone_top: float | None, stop: float | None) -> list[str]:
    """Flags that turn a brain TAKE into a PASS (item 7). Empty = allowed."""
    f = rules().get("selection_floor") or {}
    out = []
    if tier is not None and tier not in (f.get("tiers") or ["A", "B"]):
        out.append(f"selection floor: tier {tier} is outside the brain's book (tier A and B only)")
    try:
        if price and zone_top and price >= float(zone_top) * (1 - float(f.get("zone_top_gap", 0.02))):
            out.append(f"selection floor: the entry is within {100 * float(f.get('zone_top_gap', 0.02)):.0f}% of the top of its zone")
        if price and stop and (float(price) - float(stop)) / float(price) > float(f.get("stop_max", 0.08)):
            out.append(f"selection floor: the stop is more than {100 * float(f.get('stop_max', 0.08)):.0f}% away")
    except (TypeError, ValueError):
        pass
    return out


# ------------------------------------------------------------------------------------------------------------ item 6: wait_for

def _wait_for(plan: Any) -> dict | None:
    try:
        p = json.loads(plan) if isinstance(plan, str) else (plan or {})
    except ValueError:
        return None
    w = p.get("wait_for") if isinstance(p, dict) else None
    return w if isinstance(w, dict) and w else None


def wait_for_arrived(j, days: int = 2) -> list[dict]:
    """Yesterday's (and the day before's) PASS decisions whose wait_for came true on the last daily close: price_above / price_below
    against the coin's close, dial against tonight's dial state. Each row is written once (engine_state wait:<decision id>)."""
    from jarvis.service import feed

    out = []
    try:
        j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")
        rows = j.db.execute("SELECT id, t, coin, plan, thesis FROM brain_decisions WHERE action='PASS' AND t >= ? AND plan LIKE '%wait_for%' ORDER BY t",
                            (int(j.now()) - days * DAY,)).fetchall()
    except Exception:  # noqa: BLE001
        return out
    closes = feed.last_closes(j) if rows else {}
    state = None
    if rows:
        btc = feed.daily(j, "BTC")
        state = dial_state([b[4] for b in btc])
    for did, t, coin, plan, thesis in rows:
        w = _wait_for(plan)
        if not w or j.db.execute("SELECT 1 FROM engine_state WHERE k=?", (f"wait:{did}",)).fetchone():
            continue
        c = closes.get(coin)
        hit = []
        try:
            if w.get("price_above") is not None and c is not None and c >= float(w["price_above"]):
                hit.append(f"closed at {c:,.6g}, above {float(w['price_above']):,.6g}")
            if w.get("price_below") is not None and c is not None and c <= float(w["price_below"]):
                hit.append(f"closed at {c:,.6g}, under {float(w['price_below']):,.6g}")
        except (TypeError, ValueError):
            pass
        if w.get("dial") and state and str(w["dial"]).upper() == state:
            hit.append(f"the dial is {state}")
        if hit:
            out.append({"decision": did, "coin": coin, "waited_for": w.get("words") or w, "arrived": "; ".join(hit), "passed_at": t})
            j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", (f"wait:{did}", json.dumps({"t": int(j.now()), "hit": hit})))
    if out:
        j.db.commit()
    return out


# ------------------------------------------------------------------------------------------------------------ item 8: officer checks

def officer_checks(j) -> list[dict]:
    """Four checks a night, from code. Each {id, state: OK|FAIL|UNKNOWN, words}."""
    from jarvis.service import ndax_book

    oc = rules().get("officer_checks") or {}
    out = []
    try:
        s = ndax_book._get(j, "state") or {}
        value = float(s.get("value") or 0) or 1.0
        cash = float(s.get("cash") or 0)
        plan = s.get("core_plan") or {}
        cash_target = float(plan.get("cash_target", 0.4))
        idle = cash / value - cash_target
        since = s.get("cash_over_target_since")
        days_over = (int(j.now()) - int(since)) / DAY if since else 0
        if idle > 0.10 and days_over > float(oc.get("idle_days", 5)):
            out.append({"id": "idle_cash", "state": "FAIL", "words": f"cash is {100 * cash / value:.0f}% of the book against a {100 * cash_target:.0f}% target, "
                                                                     f"for {days_over:.0f} days"})
        else:
            out.append({"id": "idle_cash", "state": "OK", "words": f"cash {100 * cash / value:.0f}% of the book (target {100 * cash_target:.0f}%)"})
        core = {c: p for c, p in (s.get("pos") or {}).items() if p.get("sleeve") == "CORE"}
        noinv = [c for c, p in core.items() if not p.get("inv")]
        out.append({"id": "core_exit", "state": "FAIL" if noinv else "OK",
                    "words": (f"core positions without a written invalidation: {', '.join(noinv)}" if noinv else
                              ("every core position has its invalidation written" if core else "no core position"))})
    except Exception as exc:  # noqa: BLE001
        out.append({"id": "idle_cash", "state": "UNKNOWN", "words": f"the account could not be read ({str(exc)[:60]})"})
    try:  # book bleed: any book (watch family) down more than 2% of its start ($100 x closed trades) over 7 days
        since = int(j.now()) - int(oc.get("book_bleed_days", 7)) * DAY
        rows = j.db.execute("SELECT watch, COUNT(*), SUM(net_usd) FROM evidence_trades WHERE status='CLOSED' AND exit_t >= ? GROUP BY watch", (since,)).fetchall()
        fam: dict[str, list[float]] = {}
        for w, n, net in rows:
            base = w.split("-U")[0] if "-U" in w else w
            fam.setdefault(base, [0, 0.0])
            fam[base][0] += n
            fam[base][1] += float(net or 0)
        from jarvis.service import strategy_status

        bar = float(oc.get("book_bleed_pct", 0.02)) * 100
        over = [(b, n, net) for b, (n, net) in fam.items() if n >= 5 and net < -bar * n and "RANDOM" not in b]   # baselines are yardsticks, not books
        live = [x for x in over if strategy_status.trades(x[0])]
        paused = [x for x in over if not strategy_status.trades(x[0])]
        # Madhav's decisions on a bleeding book stand for 14 days (24 Oct: "keep Jarvis's own book running"): the check reports the
        # decision instead of failing again every night
        decided = {}
        for b, n, net in live:
            r = j.db.execute("SELECT decision, decided_t FROM rx_queue WHERE key=? AND state='DECIDED' AND decided_t > ? ORDER BY decided_t DESC LIMIT 1",
                             (f"bleed:{b}", int(j.now()) - 14 * DAY)).fetchone() if j.db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='rx_queue'").fetchone() else None
            if r:
                decided[b] = (r[0] or "").split(": ", 1)[-1]
        failing = [x for x in live if x[0] not in decided]
        parts = [f"{b}: {n} closed, net ${net:,.0f} in 7 days" + (f" (Madhav decided: {decided[b][:120]})" if b in decided else "") for b, n, net in live]
        words = "; ".join(parts) if live else "no live book is bleeding over 7 days"
        if paused:
            words += ". Paused books still closing their old trades: " + ", ".join(f"{b} ${net:,.0f}" for b, n, net in paused)
        out.append({"id": "book_bleed", "state": "FAIL" if failing else ("DECIDED" if live else "OK"), "words": words,
                    "books": [{"book": b, "n": n, "net_usd": round(net, 2), "decided": decided.get(b)} for b, n, net in live]})
    except Exception as exc:  # noqa: BLE001
        out.append({"id": "book_bleed", "state": "UNKNOWN", "words": str(exc)[:80]})
    try:  # explorer setups whose closed trades are mostly eaten by costs (the reviews' tags)
        rows = j.db.execute("SELECT book, tags FROM trade_reviews WHERE book LIKE '%Explorer%' AND t >= ?", (int(j.now()) - 30 * DAY,)).fetchall()
        n = len(rows)
        ate = sum(1 for _, tg in rows if "COSTS_ATE" in str(tg or ""))
        share = ate / n if n else None
        bad = share is not None and n >= 10 and share > float(oc.get("costs_ate_share", 0.5))
        out.append({"id": "explorer_costs", "state": "FAIL" if bad else ("UNKNOWN" if share is None else "OK"),
                    "words": (f"{ate} of {n} Explorer trades in 30 days were eaten by costs" if share is not None else "no Explorer reviews in 30 days")})
    except Exception as exc:  # noqa: BLE001
        out.append({"id": "explorer_costs", "state": "UNKNOWN", "words": str(exc)[:80]})
    return out


def file_failed_checks(j, checks: list[dict]) -> list[int]:
    """A failed check becomes a repair-board request, once a week per check (requests_log about key)."""
    from jarvis.service import fixflow, requests_log

    nums = []
    week = time.strftime("%Y-W%W", time.gmtime(j.now()))
    for c in checks:
        if c.get("state") != "FAIL":
            continue
        key = f"officer:{c['id']}:{week}"
        try:
            requests_log._table(j)
            if j.db.execute("SELECT 1 FROM owner_requests WHERE about=?", (key,)).fetchone():
                continue
        except Exception:  # noqa: BLE001
            pass
        try:
            r = fixflow.flag(j, f"Officer check {c['id']} failed: {c['words']} (discipline item 8)", market="crypto", screen="officer", use_ai=False)
            try:
                j.db.execute("UPDATE owner_requests SET about=? WHERE num=?", (key, r["num"]))
                j.db.commit()
            except Exception:  # noqa: BLE001
                pass
            nums.append(r["num"])
        except Exception:  # noqa: BLE001
            continue
    return nums


# ------------------------------------------------------------------------------------------------------------ item 5: one plan line

def plan_line(j, day: str | None = None) -> dict:
    """One plan sentence for tonight, from the layers: the stance (dial state and view), the $500 book's core plan, the brain's
    decisions today, the bold book's action today, and the officer's checks. Conflicts are listed; the stance wins them.
    Saved once per UTC day (engine_state plan:<day>)."""
    from jarvis.service import feed, ndax_book

    now = int(j.now())
    day = day or time.strftime("%Y-%m-%d", time.gmtime(now))
    day0 = now - now % DAY
    btc = feed.daily(j, "BTC")
    state = dial_state([b[4] for b in btc]) if btc else None
    parts: list[str] = []
    conflicts: list[dict] = []
    view = None
    try:
        r = j.db.execute("SELECT view, dial FROM stance WHERE day=? ORDER BY t DESC LIMIT 1", (day,)).fetchone()
        if r and r[0]:
            v = r[0].strip()
            cut = v[:220].rfind(". ")
            view = v[:cut + 1] if cut > 40 else v[:220].rsplit(" ", 1)[0] + "…"   # whole sentences, never a cut word
    except Exception:  # noqa: BLE001
        pass
    parts.append(STATE_WORDS.get(state or "", "the dial could not be read") + ".")
    try:
        from src.research import book500 as B

        s = ndax_book._get(j, "state") or {}
        value = float(s.get("value") or 0)
        cash = float(s.get("cash") or 0)
        plan = s.get("core_plan") or {}
        if value and plan.get("state") != state:          # tonight's step has not run yet: the plan the rule will apply, from the book as it is
            held = {c: p["qty"] * p["last"] for c, p in (s.get("pos") or {}).items() if p.get("sleeve") == "CORE"}
            plan = core_targets(state, value, B.CORE, int((s.get("tranches") or {}).get("done") or (3 if held else 0)), held=held)
        if value:
            parts.append(f"Account: {plan.get('words') or 'core by the dial'}; cash {100 * cash / value:.0f}% (target {100 * float(plan.get('cash_target', 0.4)):.0f}%).")
    except Exception:  # noqa: BLE001
        pass
    try:
        rows = j.db.execute("SELECT action, COUNT(*) FROM brain_decisions WHERE t >= ? GROUP BY action", (day0,)).fetchall()
        d = {a: n for a, n in rows}
        if d:
            parts.append("Brain: " + ", ".join(f"{n} {a.lower()}" for a, n in sorted(d.items())) + ".")
        takes = j.db.execute("SELECT coin FROM brain_decisions WHERE t >= ? AND action='TAKE'", (day0,)).fetchall()
        if takes and state == "CLOSED":
            conflicts.append({"kind": "LAYER_CONFLICT", "between": "brain vs stance", "words": f"the brain bought {', '.join(c for (c,) in takes)} with the dial closed"})
    except Exception:  # noqa: BLE001
        pass
    try:
        r = j.db.execute("SELECT action, coin, stop FROM bold_decisions WHERE day=? ORDER BY t DESC LIMIT 1", (day,)).fetchone()
        if r:
            act, coin, stop = r
            parts.append(f"Bold: {act} {coin or ''}".strip() + ".")
            if act in ("TAKE", "WOULD_ADD") and state != "CONFIRMED":
                conflicts.append({"kind": "LAYER_CONFLICT", "between": "bold vs stance",
                                  "words": f"the bold book wants {coin} while the dial is {state or 'unread'}; the stance wins: no add"})
            if act in ("TAKE", "WOULD_ADD") and not stop:
                conflicts.append({"kind": "LAYER_CONFLICT", "between": "bold vs rule 4", "words": f"a {act} on {coin} with no stop named: dropped"})
    except Exception:  # noqa: BLE001
        pass
    checks = officer_checks(j)
    failed = [c for c in checks if c["state"] == "FAIL"]
    parts.append(("Officer: " + "; ".join(c["words"] for c in failed) + ".") if failed else "Officer: all four checks pass.")
    try:  # the setups board (24 Oct 2026): what the scan of every tier A and B coin found
        from jarvis.service import setups

        b = setups.latest(j)
        if b:
            parts.append("Setups: " + b.get("words", "") + (f" Sent to the brain: {', '.join(b['woke'])}." if b.get("woke") else ""))
            touched = setups.touched_today(j)
            if touched:
                parts.append("Touched their trigger today: " + ", ".join(f"{t['coin']} ({t['family']})" for t in touched[:4]) + ".")
    except Exception:  # noqa: BLE001
        pass
    arrived = wait_for_arrived(j)
    if arrived:
        parts.append("Arrived: " + "; ".join(f"{a['coin']} ({a['arrived']})" for a in arrived[:3]) + ".")
    if view:
        parts.append(f"View: {view}")
    line = " ".join(parts)
    out = {"day": day, "state": state, "line": line, "conflicts": conflicts, "checks": checks, "arrived": arrived, "rules": version()}
    try:
        j.db.execute("CREATE TABLE IF NOT EXISTS engine_state (k TEXT PRIMARY KEY, v TEXT)")
        j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", (f"plan:{day}", json.dumps(out, default=str)))
        j.db.commit()
    except Exception:  # noqa: BLE001
        pass
    return out


def latest_plan(j) -> dict | None:
    try:
        r = j.db.execute("SELECT v FROM engine_state WHERE k LIKE 'plan:%' ORDER BY k DESC LIMIT 1").fetchone()
        return json.loads(r[0]) if r else None
    except Exception:  # noqa: BLE001
        return None
