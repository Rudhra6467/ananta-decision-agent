"""The stance and the morning scan (agent fixes A2 and A3; Madhav, Oct 14: "let's start with this fixing steps you suggested").

A2  the stance: a trader's notebook the brain writes once a day, right after the daily close (00:00 UTC): its view of the market,
    what changed since yesterday and why ("view changed from X to Y because Z"), and one line on each open position's thesis.
    Every market answer reads it first (briefs.market_brief), so two answers on the same day start from the same written view.
A3  the morning scan: in the same call the brain picks at most 5 coins of tier A and writes, BEFORE the move, what would make it
    buy: the trigger (a daily close above or below a price, or a touch of it), the invalidation, the tested exit plan, the size and
    how long the expectation waits (1-5 days). Code checks each one; watch() then follows them every 15 minutes:
      OPEN -> TRIGGERED    the trigger happened: the fill is recorded, a random tier-A twin is drawn at the same moment, and the
                           brain is woken ("expectation:<id>"); it still decides with every rule and red flag (A5 lets it go first)
      OPEN -> INVALIDATED  a daily close under the invalidation came first
      OPEN -> EXPIRED      the waiting time ran out
    settle() scores every triggered expectation like a pass is scored (the move a day and five days later, and the same move over
    the market median), and, once its exit plan has run, net of costs against the twin traded with the same plan.

Paper and research only: nothing here trades. Budget: one model call a day inside the brain's own $1.00 day (logged in
ask_messages, thread 'brain', so the pacer counts it); with less than MIN_LEFT of that dollar left it writes the facts only.
"""
from __future__ import annotations

import collections
import hashlib
import json
import os
import time
import uuid
from typing import Any, Callable

DAY = 86400
MAX_EXP = 5
TYPES = ("close_above", "close_below", "touch_above", "touch_below")
PLANS = ("DIP", "ZONE", "TREND")
BAND = 0.10                  # a trigger within 10% of tonight's price
STOP_MAX = 0.15              # the invalidation under the trigger and at most 15% away (the brain's own red flag)
HORIZON = (1, 5)             # days an expectation waits for its trigger
SIZE = (25.0, 100.0)
MIN_LEFT = 0.08              # $ of the brain's day that must be left before the stance's model call is made
MAX_TOKENS = 3000
STATUSES = ("INTACT", "WEAKER", "BROKEN")

SYSTEM = """You are Ananta's decision brain writing tonight's stance: a short trader's notebook for one paper book (crypto, long
only, spot). The daily candle has just closed. Write what you think and what you are looking for BEFORE the market moves. Every
expectation is scored later against what really happened and against a random coin traded with the same plan, so be specific
and honest. Paper only.

Rules:
- Use the facts given (numbers from our own stores) and the knowledge list (what the repair shop measured, with status).
  Measured edges outrank ideas; FAILED items are never the reason for anything.
- The exposure dial is the market state (Bitcoin above BOTH its 50-day and 200-day averages = OPEN, review #25). With the dial
  CLOSED the code buys nothing except the one measured cell (H07 on tier A), so expectations are then scored but not acted on.
- view: two or three sentences: the market as you read it tonight, what you expect over the next few days, and what would change
  your mind.
- changed: compare with yesterday's stance (given): "view changed from X to Y because Z", or "unchanged: <why>". A change needs a
  reason in tonight's facts; never flip without one.
- positions: one line per open position: is its written thesis INTACT, WEAKER or BROKEN by tonight's facts, and why. This is
  commentary only: each trade exits by its own tested plan, never by this line.
- expectations: at most 5 coins from candidates, only where you can say in advance what would make it a buy. Each one:
  coin; plan DIP | ZONE | TREND (the tested exit plans: DIP out after 10 days with no stop; ZONE and TREND out after 20 days);
  trigger {"type": close_above | close_below | touch_above | touch_below, "price": number} that is NOT already met tonight and
  is within 10% of the price; invalidation: a price under the trigger and at most 15% under it (a daily close below it cancels the
  expectation; after a fill it is the stop, or for DIP the point where the idea is wrong); horizon_days 1-5 (how long it waits
  for the trigger); size_pct 25-100; why: one sentence citing the numbers; knowledge_used: ids from the knowledge list.
  An empty list is a fine answer: then say why in no_expectation_reason. Round-trip costs are 0.5-1% (cost_rt_pct): a trigger
  whose likely move is a few tenths of a percent cannot pay.

Reply with ONE JSON object only:
{"view": "...", "changed": "...",
 "positions": [{"coin": "...", "trade_id": "...", "status": "INTACT" | "WEAKER" | "BROKEN", "why": "..."}],
 "expectations": [{"coin": "...", "plan": "DIP", "trigger": {"type": "touch_below", "price": 0.0}, "invalidation": 0.0,
                   "horizon_days": 3, "size_pct": 50, "why": "...", "knowledge_used": ["H07"]}],
 "no_expectation_reason": ""}"""

SAY = ("Ananta's own written view (the brain writes it after each daily close). Start a market answer from it; if you now differ, "
       "say what changed since it was written. Source 'facts only' = no written view today: say so; never invent one.")


# ---------------------------------------------------------------------------
# tables and small helpers (tests replace the data helpers)
# ---------------------------------------------------------------------------
def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS stance (day TEXT PRIMARY KEY, t INTEGER, dial REAL, view TEXT, changed TEXT, facts_diff TEXT, "
                 "positions TEXT, facts TEXT, source TEXT, model TEXT, cost_usd REAL, note TEXT)")
    j.db.execute("CREATE TABLE IF NOT EXISTS expectations (id TEXT PRIMARY KEY, day TEXT, t INTEGER, coin TEXT, plan TEXT, trigger_type TEXT, "
                 "trigger_price REAL, invalidation REAL, horizon_days INTEGER, size_pct REAL, why TEXT, knowledge TEXT, price_at_plan REAL, "
                 "dial REAL, status TEXT, status_t INTEGER, fill REAL, fill_t INTEGER, twin_coin TEXT, twin_fill REAL, woke INTEGER, "
                 "after_1d_pct REAL, after_5d_pct REAL, after_1d_ex REAL, after_5d_ex REAL, twin_5d_pct REAL, cost_rt_pct REAL, "
                 "plan_pct REAL, twin_plan_pct REAL, wait_pct REAL, note TEXT)")
    j.db.execute("CREATE INDEX IF NOT EXISTS expectations_status ON expectations (status)")


def _now(j) -> int:
    return int(j.now())


def _day(t: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(t))


def _pct(a, b, n: int = 2) -> float | None:
    return round(100 * (a / b - 1), n) if a and b else None


def _sub(a, b) -> float | None:
    return round(a - b, 1) if a is not None and b is not None else None


def _closed_daily(j, coin: str) -> list[tuple]:
    """The coin's daily candles that have closed (the brain's own source: the Explorer's for the 10, the universe feed's for the rest)."""
    from jarvis.service import brain

    now = _now(j)
    return [b for b in brain._coin_daily(j, coin) if b[0] + DAY <= now]


def _live(j, coin: str) -> float | None:
    from jarvis.service import brain

    return brain._live_px(j, coin)


def _bars5(j, coin: str, since: int) -> list[tuple]:
    """Closed 5-minute candles from `since` on (the feed keeps 14 days)."""
    from jarvis.service import feed

    now = _now(j)
    n = min(2000, max(12, (now - since) // 300 + 2))
    return [b for b in feed.bars(j, coin, "5m", int(n)) if b[0] >= since and b[0] + 300 <= now]


def _cost1(coin: str) -> float:
    """Paper cost per side, exactly as the brain's own book pays it."""
    from jarvis.service import brain, watch_engine
    from src.research import reads as R

    return R.cost(coin) if brain._is_lab(coin) else watch_engine._cost(coin, brain.WATCH)


def _dial(j) -> dict:
    """The exposure dial, refreshed if its cache still holds the day before the last close."""
    from jarvis.service import exposure

    try:
        s = exposure.state(j) or {}
        y = _day(_now(j) - _now(j) % DAY - DAY)
        if s.get("as_of_day") and s["as_of_day"] != y:
            exposure._CACHE.update(t=0, v=None)
            s = exposure.state(j) or {}
        return s
    except Exception:  # noqa: BLE001
        return {}


def _dw(d) -> str:
    return "unknown" if d is None else ("OPEN" if d > 0 else "CLOSED")


def candidates(j) -> list[str]:
    """Tier A by liquidity, then any of the 10 live coins not in it (the brain ranks the 10 like tier A)."""
    from jarvis.service import registry
    from src.research import reads as R

    try:
        a = registry.members(j, "A")
    except Exception:  # noqa: BLE001
        a = []
    return a + [c for c in R.COINS if c not in a]


# ---------------------------------------------------------------------------
# the facts (numbers only, from our own stores)
# ---------------------------------------------------------------------------
def coin_facts(j, coin: str) -> dict | None:
    """One candidate's numbers on its last closed daily candle; None without 210 days or without yesterday's candle."""
    from src.research import reads as R

    D = _closed_daily(j, coin)
    now = _now(j)
    if len(D) < 210 or D[-1][0] < now - now % DAY - DAY:
        return None
    S = R.Series(D)
    i = len(D) - 1
    c, s200 = S.c[i], S.sma200[i]
    r10 = R.rsi(S.c, 10)[i]
    return {"coin": coin, "close": c, "live": _live(j, coin), "day_pct": _pct(c, S.c[i - 1]), "week_pct": _pct(c, S.c[i - 7]),
            "rsi10": round(r10) if r10 is not None else None, "vs_50d_pct": _pct(c, S.ema50[i]), "vs_200d_pct": _pct(c, s200),
            "atr_pct": round(100 * S.atr[i] / c, 2) if S.atr[i] else None,
            "from_20d_high_pct": _pct(c, max(S.h[-20:])), "from_20d_low_pct": _pct(c, min(S.l[-20:])),
            "h07_now": bool(r10 is not None and r10 < 30 and s200 and c > s200), "cost_rt_pct": round(200 * _cost1(coin), 2)}


def positions(j) -> list[dict]:
    """The brain's open trades in its account (the no-room evidence trades sit outside it), each with its written thesis."""
    from jarvis.service import brain

    brain._table(j)
    now, out = _now(j), []
    for tid, coin, entry, et, stop, dj in j.db.execute(
            "SELECT id, coin, entry, entry_t, stop, detail FROM evidence_trades WHERE watch=? AND status='OPEN' "
            "AND COALESCE(detail,'') NOT LIKE ? ORDER BY entry_t", (brain.WATCH, brain.NOROOM)).fetchall():
        d = json.loads(dj or "{}")
        plan = None
        if d.get("decision"):
            r = j.db.execute("SELECT plan FROM brain_decisions WHERE id=?", (d["decision"],)).fetchone()
            plan = json.loads(r[0] or "{}").get("exit_plan") if r else None
        px = _live(j, coin)
        out.append({"trade_id": tid, "coin": coin, "entry": entry, "now": px, "pnl_pct": _pct(px, entry),
                    "days_held": round((now - (et or now)) / DAY, 1), "exit_plan": plan, "days_max": d.get("days"),
                    "stop": stop or None, "invalidation": d.get("invalidation"), "thesis": (d.get("thesis") or "")[:220]})
    return out


def facts(j) -> dict:
    """Tonight's facts: the dial, Bitcoin, tier-A breadth, every candidate's numbers and the open positions."""
    now = _now(j)
    dl = _dial(j)
    cands, stale = [], []
    for c in candidates(j):
        try:
            f = coin_facts(j, c)
        except Exception:  # noqa: BLE001
            f = None
        (cands.append(f) if f else stale.append(c))
    btc = next((f for f in cands if f["coin"] == "BTC"), None)
    n = len(cands)
    return {"as_of_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime(now)), "candle_closed_utc": _day(now - now % DAY - DAY),
            "dial": {"dial": dl.get("dial"), "words": dl.get("dial_words"), "why": dl.get("why"), "rule": dl.get("rule")},
            "btc": btc,
            "breadth_tier_a": {"above_200d": sum(1 for f in cands if (f["vs_200d_pct"] or -1) > 0),
                               "above_50d": sum(1 for f in cands if (f["vs_50d_pct"] or -1) > 0),
                               "up_last_day": sum(1 for f in cands if (f["day_pct"] or 0) > 0), "of": n},
            "candidates": cands, "no_fresh_candle": stale, "open_positions": positions(j)}


def diff_facts(prev: dict | None, f: dict) -> list[str]:
    """What moved in the facts since the last stance (code, not the model): the dial, Bitcoin's averages, breadth, positions."""
    if not prev:
        return ["first stance: nothing to compare with"]
    out = []
    a, b = (prev.get("dial") or {}).get("dial"), (f.get("dial") or {}).get("dial")
    if a != b:
        out.append(f"the exposure dial changed from {_dw(a)} to {_dw(b)}")
    pb, fb = prev.get("btc") or {}, f.get("btc") or {}
    for k, name in (("vs_50d_pct", "50-day"), ("vs_200d_pct", "200-day")):
        x, y = pb.get(k), fb.get(k)
        if x is not None and y is not None and (x > 0) != (y > 0):
            out.append(f"Bitcoin closed {'above' if y > 0 else 'below'} its {name} average ({x:+.1f}% -> {y:+.1f}%)")
    pa, fa = (prev.get("breadth_tier_a") or {}).get("above_200d"), (f.get("breadth_tier_a") or {}).get("above_200d")
    if pa is not None and fa is not None and pa != fa:
        out.append(f"tier-A coins above their 200-day average: {pa} -> {fa} of {(f.get('breadth_tier_a') or {}).get('of')}")
    po = {p["coin"] for p in prev.get("open_positions") or []}
    fo = {p["coin"] for p in f.get("open_positions") or []}
    if fo - po:
        out.append("new positions: " + ", ".join(sorted(fo - po)))
    if po - fo:
        out.append("closed positions: " + ", ".join(sorted(po - fo)))
    return out or ["no change in the dial, Bitcoin's averages, tier-A breadth or the open positions"]


def _row(j, before: str | None = None) -> dict | None:
    _table(j)
    q = ("SELECT day, t, dial, view, changed, facts_diff, positions, facts, source, model, cost_usd, note FROM stance"
         + (" WHERE day < ?" if before else "") + " ORDER BY day DESC LIMIT 1")
    r = j.db.execute(q, (before,) if before else ()).fetchone()
    if not r:
        return None
    return dict(zip(("day", "t", "dial", "view", "changed", "facts_diff", "positions", "facts", "source", "model", "cost_usd", "note"), r))


def latest(j) -> dict | None:
    """The newest stance with its expectations (for the app and Ask)."""
    r = _row(j)
    if not r:
        return None
    r.pop("facts", None)
    r["facts_diff"] = json.loads(r["facts_diff"] or "[]")
    r["positions"] = json.loads(r["positions"] or "[]")
    r["expectations"] = expectations(j, r["day"])
    return r


def expectations(j, day: str | None = None, status: str | None = None) -> list[dict]:
    _table(j)
    cols = ("id", "day", "t", "coin", "plan", "trigger_type", "trigger_price", "invalidation", "horizon_days", "size_pct", "why", "status",
            "status_t", "fill", "fill_t", "twin_coin", "woke", "after_1d_pct", "after_5d_pct", "after_5d_ex", "cost_rt_pct", "plan_pct",
            "twin_plan_pct", "wait_pct", "note")
    q, args = f"SELECT {', '.join(cols)} FROM expectations WHERE 1=1", []
    if day:
        q, args = q + " AND day=?", args + [day]
    if status:
        q, args = q + " AND status=?", args + [status]
    return [dict(zip(cols, r)) for r in j.db.execute(q + " ORDER BY t, coin", args).fetchall()]


# ---------------------------------------------------------------------------
# writing the stance (once a day, after the daily close)
# ---------------------------------------------------------------------------
def due(j) -> bool:
    """Today's stance (UTC day) not written yet, and yesterday's daily candle is in."""
    _table(j)
    now = _now(j)
    if j.db.execute("SELECT 1 FROM stance WHERE day=?", (_day(now),)).fetchone():
        return False
    D = _closed_daily(j, "BTC")
    return bool(D) and D[-1][0] >= now - now % DAY - DAY


def _may_call(j) -> tuple[bool, str]:
    """The model call only inside the brain's own day of AI money; otherwise the facts alone, and why."""
    from jarvis.service import brain

    if os.getenv("BRAIN_ENABLED", "1") != "1":
        return False, "the brain is switched off (BRAIN_ENABLED): facts only"
    if os.getenv("STANCE_AI", "1") != "1":
        return False, "the stance's model call is switched off (STANCE_AI=0): facts only"
    spent = brain.spent_today(j)
    if brain.DAILY_USD - spent < MIN_LEFT:
        return False, f"the brain's AI dollar for today is used (${spent:.2f} of ${brain.DAILY_USD:.2f}): facts only, nothing new spent"
    try:
        from jarvis.service.ask import Ask

        a = Ask(j)
        if a.setting("ask_enabled") != "1":
            return False, "Ask Ananta (the AI) is switched off: facts only"
        if a.spend().get("left_usd", 1) < brain.MIN_BUDGET:
            return False, "today's AI budget is used up: facts only"
    except Exception:  # noqa: BLE001
        pass
    return True, ""


def _call(system: str, user: str, post=None) -> tuple[str, dict]:
    """One call to the brain's model; no prompt cache (a once-a-day call would pay for the cache write and never read it)."""
    from jarvis.service import ask, brain

    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("no Claude key")
    post = post or ask._post
    r = post("https://api.anthropic.com/v1/messages", {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
             {"model": brain.MODEL, "max_tokens": MAX_TOKENS, "system": system, "messages": [{"role": "user", "content": user}]})
    u = r.get("usage") or {}
    text = "".join(c.get("text", "") for c in r.get("content") or [] if c.get("type") == "text")
    return text, {"in": u.get("input_tokens", 0), "out": u.get("output_tokens", 0), "model": brain.MODEL,
                  "cache_read": u.get("cache_read_input_tokens", 0) or 0, "cache_write": u.get("cache_creation_input_tokens", 0) or 0}


def _log(j, usage: dict, cost: float, ms: int) -> None:
    """Into ask_messages as a 'brain' call, so the day's budget and the brain's pacer both see it."""
    try:
        j.db.execute("INSERT INTO ask_messages (id, thread, t, role, text, reply, provider, model, ms, tokens_in, tokens_out, tools, error, cost_usd, "
                     "mode, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (uuid.uuid4().hex, "brain", _now(j), "assistant", "brain stance and morning scan", "", "sonnet", usage.get("model"), ms,
                      usage.get("in", 0) + usage.get("cache_read", 0) + usage.get("cache_write", 0), usage.get("out", 0), "", None, cost,
                      "worker", "stance (fix A2/A3)"))
        j.db.commit()
    except Exception:  # noqa: BLE001  a test database may not have the table
        pass


def _parse(text: str) -> dict:
    from jarvis.service import brain

    blk = brain._json_block(text)
    if not blk:
        raise ValueError("no JSON in the reply" + (" (it was cut off)" if "{" in (text or "") else ""))
    d = json.loads(blk)
    if not isinstance(d, dict) or not str(d.get("view") or "").strip():
        raise ValueError("the reply has no view")
    return d


def validate(raw: Any, f: dict) -> tuple[list[dict], list[str]]:
    """Code checks every expectation; a bad one is dropped with the reason, never repaired."""
    cands = {c["coin"]: c for c in f.get("candidates") or []}
    out, rejected, seen = [], [], set()
    for e in (raw if isinstance(raw, list) else [])[:2 * MAX_EXP]:
        try:
            if not isinstance(e, dict):
                raise ValueError("not an object")
            coin = str(e.get("coin") or "").upper()
            c = cands.get(coin)
            if not c:
                raise ValueError(f"{coin or '?'}: not a tier-A candidate with tonight's candle")
            if coin in seen:
                raise ValueError(f"{coin}: one expectation per coin")
            if len(out) >= MAX_EXP:
                raise ValueError(f"{coin}: at most {MAX_EXP} expectations")
            plan = str(e.get("plan") or "").upper()
            if plan not in PLANS:
                raise ValueError(f"{coin}: plan must be DIP, ZONE or TREND")
            tr = e.get("trigger") if isinstance(e.get("trigger"), dict) else {}
            typ = str(tr.get("type") or "").lower()
            if typ not in TYPES:
                raise ValueError(f"{coin}: trigger type must be one of {', '.join(TYPES)}")
            px = float(tr.get("price"))
            ref = c.get("live") or c["close"]
            if not px > 0 or abs(px / ref - 1) > BAND:
                raise ValueError(f"{coin}: trigger {px:g} is more than {BAND:.0%} from the price {ref:g}")
            met = {"close_above": c["close"] >= px, "close_below": c["close"] <= px, "touch_above": ref >= px, "touch_below": ref <= px}[typ]
            if met:
                raise ValueError(f"{coin}: the trigger is already met tonight (written after the move, not before it)")
            inv = float(e.get("invalidation"))
            if not (px * (1 - STOP_MAX) <= inv < px):
                raise ValueError(f"{coin}: the invalidation must be under the trigger and at most {STOP_MAX:.0%} under it")
            hz = int(e.get("horizon_days"))
            if not HORIZON[0] <= hz <= HORIZON[1]:
                raise ValueError(f"{coin}: horizon_days must be {HORIZON[0]}-{HORIZON[1]}")
            size = max(SIZE[0], min(SIZE[1], float(e.get("size_pct") or 50)))
        except (TypeError, ValueError, KeyError) as exc:
            rejected.append(str(exc)[:160])
            continue
        seen.add(coin)
        out.append({"coin": coin, "plan": plan, "trigger_type": typ, "trigger_price": px, "invalidation": inv, "horizon_days": hz,
                    "size_pct": size, "why": str(e.get("why") or "")[:300], "price_at_plan": ref,
                    "knowledge": [k for k in (e.get("knowledge_used") or []) if isinstance(k, str)][:6]})
    return out, rejected


def _positions_reply(raw: Any, f: dict) -> list[dict]:
    held = {p["coin"] for p in f.get("open_positions") or []}
    out = []
    for p in raw if isinstance(raw, list) else []:
        if isinstance(p, dict) and str(p.get("coin") or "").upper() in held and str(p.get("status") or "").upper() in STATUSES:
            out.append({"coin": str(p["coin"]).upper(), "trade_id": str(p.get("trade_id") or "")[:20],
                        "status": str(p["status"]).upper(), "why": str(p.get("why") or "")[:200]})
    return out[:25]


def _prompt(j, f: dict, prev: dict | None) -> str:
    from jarvis.service import brain

    know = [{"id": k, "status": s, "what": w} for k, s, w in brain.KNOWLEDGE]
    y = None
    if prev:
        y = {"day": prev["day"], "view": prev.get("view"), "changed": prev.get("changed"), "source": prev.get("source"),
             "expectations": [{k: e[k] for k in ("coin", "plan", "trigger_type", "trigger_price", "invalidation", "status", "fill", "after_1d_pct")}
                              for e in expectations(j, prev["day"])]}
    return ("Tonight's facts (JSON, from our own stores):\n" + json.dumps(f, default=str, separators=(",", ":"))
            + "\n\nYesterday's stance: " + json.dumps(y, default=str, separators=(",", ":"))
            + "\n\nYour morning-scan record so far: " + json.dumps(record(j), default=str, separators=(",", ":"))
            + "\n\nThe knowledge list (what the repair shop measured, with status):\n" + json.dumps(know, separators=(",", ":")))


def plan(j, call: Callable | None = None, force: bool = False) -> dict | None:
    """Once a day after the daily close: the facts, the brain's stance and expectations (when its day's money allows), saved."""
    from jarvis.service import brain

    _table(j)
    if not force and not due(j):
        return None
    now = _now(j)
    day = _day(now)
    f = facts(j)
    prev = _row(j, before=day)
    try:
        prev_facts = json.loads(prev["facts"]) if prev and prev.get("facts") else None
    except ValueError:
        prev_facts = None
    res: dict[str, Any] = {"day": day, "t": now, "dial": (f.get("dial") or {}).get("dial"), "view": None, "changed": None,
                           "facts_diff": diff_facts(prev_facts, f), "positions": [], "expectations": [], "rejected": [],
                           "source": "facts only", "model": None, "cost_usd": 0.0}
    ok, why = _may_call(j)
    if ok and not f["candidates"]:
        ok, why = False, "no tier-A coin has yesterday's daily candle yet: facts only"
    if ok:
        t0 = time.time()
        try:
            text, usage = (call or (lambda u: _call(SYSTEM, u)))(_prompt(j, f, prev))
        except Exception as exc:  # noqa: BLE001
            text, usage, why = None, {}, f"the model call failed ({str(exc)[:120]}): facts only"
        if text is not None:
            cost = brain._price(usage)
            _log(j, usage, cost, int(1000 * (time.time() - t0)))
            res.update(cost_usd=cost, model=usage.get("model"))
            try:
                d = _parse(text)
            except (ValueError, json.JSONDecodeError) as exc:
                d, why = None, f"unreadable reply ({str(exc)[:100]}): facts only"
            if d:
                exps, rejected = validate(d.get("expectations"), f)
                res.update(view=str(d.get("view"))[:900], changed=str(d.get("changed") or "")[:400], source="brain",
                           positions=_positions_reply(d.get("positions"), f), expectations=exps, rejected=rejected)
                if not exps:
                    why = "no expectation tonight: " + str(d.get("no_expectation_reason") or "no reason given")[:300]
                elif rejected:
                    why = "dropped by the code: " + "; ".join(rejected)[:300]
    res["note"] = why
    j.db.execute("INSERT OR REPLACE INTO stance (day, t, dial, view, changed, facts_diff, positions, facts, source, model, cost_usd, note) "
                 "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                 (day, now, res["dial"], res["view"], res["changed"], json.dumps(res["facts_diff"]), json.dumps(res["positions"]),
                  json.dumps(f, default=str, separators=(",", ":")), res["source"], res["model"], res["cost_usd"], why or None))
    for e in res["expectations"]:
        e["id"] = uuid.uuid4().hex[:12]
        j.db.execute("INSERT INTO expectations (id, day, t, coin, plan, trigger_type, trigger_price, invalidation, horizon_days, size_pct, why, "
                     "knowledge, price_at_plan, dial, status, status_t) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (e["id"], day, now, e["coin"], e["plan"], e["trigger_type"], e["trigger_price"], e["invalidation"], e["horizon_days"],
                      e["size_pct"], e["why"], json.dumps(e["knowledge"]), e["price_at_plan"], res["dial"], "OPEN", now))
    j.db.commit()
    if prev and prev.get("dial") is not None and prev["dial"] <= 0 and (res["dial"] or 0) > 0:
        try:                                            # A5: the dial opening is a moment for the brain (review #25)
            brain.wake(j, "BTC", "dial_open", {"from": "CLOSED", "to": "OPEN", "why": (f.get("dial") or {}).get("why")})
            res["woke"] = "dial_open"
        except Exception:  # noqa: BLE001
            pass
    return res


# ---------------------------------------------------------------------------
# following the expectations (every 15 minutes) and scoring them
# ---------------------------------------------------------------------------
def _event(j, coin: str, t0: int, typ: str, px: float, inv: float, hz: int, now: int) -> tuple | None:
    """What happened first since the plan was written: ("TRIGGERED", t, fill), ("INVALIDATED", t, price), ("EXPIRED", t, price) or None.
    Close triggers and the invalidation use daily closes; touches use the closed 5-minute candles (a limit or stop at the price,
    filled at the candle's open when it opened beyond it)."""
    end = t0 + hz * DAY
    D = [b for b in _closed_daily(j, coin) if b[0] + DAY > t0]          # candles that closed after the plan was written
    inv_t = inv_px = trig_t = fill = None
    for b in D:
        if b[4] < inv:
            inv_t, inv_px = b[0] + DAY, b[4]
            break
    if typ in ("close_above", "close_below"):
        for b in D:
            if (b[4] >= px) if typ == "close_above" else (b[4] <= px):
                trig_t, fill = b[0] + DAY, b[4]
                break
    else:
        bars = _bars5(j, coin, t0)
        for b in bars:
            if typ == "touch_below" and b[3] <= px:
                trig_t, fill = b[0] + 300, min(px, b[1])
                break
            if typ == "touch_above" and b[2] >= px:
                trig_t, fill = b[0] + 300, max(px, b[1])
                break
        if trig_t is None and not bars:                                  # no 5-minute candles: the live price
            live = _live(j, coin)
            if live is not None and ((live <= px) if typ == "touch_below" else (live >= px)):
                trig_t, fill = now, live
    hits = [h for h in (("TRIGGERED", trig_t, fill), ("INVALIDATED", inv_t, inv_px)) if h[1] is not None and h[1] <= end]
    if hits:
        k, et, p = min(hits, key=lambda h: (h[1], h[0] != "TRIGGERED"))  # the earliest; a tie goes to the trigger
        if k == "TRIGGERED" and p <= inv:
            return ("INVALIDATED", et, p)                                # it came with the price already under the invalidation
        return (k, et, p)
    if now >= end:
        return ("EXPIRED", end, _live(j, coin) or (D[-1][4] if D else None))
    return None


def _twin(j, eid: str, coin: str, typ: str, et: int) -> tuple[str | None, float | None]:
    """A random tier-A coin at the same moment (fixed by the expectation's id), and its price then."""
    pool = sorted(c for c in candidates(j) if c != coin)
    if not pool:
        return None, None
    tw = pool[int(hashlib.sha1(f"{eid}|{et}".encode()).hexdigest(), 16) % len(pool)]
    if typ.startswith("close_"):
        b = next((b for b in _closed_daily(j, tw) if b[0] + DAY == et), None)
        return tw, (b[4] if b else None)
    b = next((b for b in _bars5(j, tw, et - 300) if b[0] + 300 >= et), None)
    return tw, (b[4] if b else _live(j, tw))


def watch(j) -> dict:
    """Every 15 minutes: each OPEN expectation against the market; a trigger wakes the brain (while fresh); then the scoring."""
    from jarvis.service import brain

    _table(j)
    now = _now(j)
    out: dict[str, Any] = {"triggered": [], "invalidated": [], "expired": []}
    for eid, t, coin, plan_, typ, px, inv, hz, size, why, p0 in j.db.execute(
            "SELECT id, t, coin, plan, trigger_type, trigger_price, invalidation, horizon_days, size_pct, why, price_at_plan "
            "FROM expectations WHERE status='OPEN'").fetchall():
        try:
            ev = _event(j, coin, t, typ, px, inv, hz, now)
        except Exception as exc:  # noqa: BLE001
            out.setdefault("errors", []).append(f"{coin}: {str(exc)[:80]}")
            continue
        if not ev:
            continue
        kind, et, price = ev
        if kind == "TRIGGERED":
            tw, tfill = _twin(j, eid, coin, typ, et)
            woke = 0
            if now - et <= brain.STALE_S:
                brain.wake(j, coin, f"expectation:{eid}", {
                    "plan": plan_, "trigger": {"type": typ, "price": px}, "invalidation": inv, "size_pct": size, "why": why, "fill": price,
                    "written_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime(t)),
                    "meaning": "your own plan, written before the move by the morning scan (fix A3); decide it like any moment, with every rule"})
                woke = 1
            j.db.execute("UPDATE expectations SET status='TRIGGERED', status_t=?, fill=?, fill_t=?, twin_coin=?, twin_fill=?, woke=?, note=? WHERE id=?",
                         (now, price, et, tw, tfill, woke, None if woke else "triggered more than 45 minutes before this check: scored, not sent to the brain", eid))
            out["triggered"].append(coin)
        else:
            j.db.execute("UPDATE expectations SET status=?, status_t=?, wait_pct=? WHERE id=?", (kind, et, _pct(price, p0), eid))
            out[kind.lower()].append(coin)
    j.db.commit()
    out["scored"] = settle(j)
    return out


def simulate(D: list[tuple], t: int, entry: float, plan_: str, stop: float | None) -> float | None:
    """Gross % of one paper trade entered at t under a tested exit plan on daily candles that open at or after t: DIP out at the
    close of day 10 with no stop; ZONE and TREND out at the close of day 20, or at the stop when a daily low reaches it first (at
    the open when it opened under). None until the plan has run."""
    from jarvis.service import brain

    ep = brain.EXIT_PLANS.get(plan_) or {}
    if not ep.get("days") or not entry:
        return None
    use_stop, end = bool(stop) and not ep.get("no_stop"), t + ep["days"] * DAY
    for b in D:
        if b[0] < t:
            continue
        if use_stop and b[3] <= stop:
            return _pct(min(b[1], stop), entry)
        if b[0] + DAY >= end:
            return _pct(b[4], entry)
    return None


def _twin_stop(D: list[tuple], T: list[tuple], t: int, fill: float, inv: float, tfill: float) -> float | None:
    """The twin's stop the same number of daily ranges under its own price (as the brain's random twin)."""
    from src.research import reads as R

    if not inv or not fill or not tfill:
        return None
    da, ta = [b for b in D if b[0] + DAY <= t], [b for b in T if b[0] + DAY <= t]
    a1 = R.Series(da).atr[-1] if len(da) > 20 else None
    a2 = R.Series(ta).atr[-1] if len(ta) > 20 else None
    if a1 and a2:
        return tfill - (fill - inv) / a1 * a2
    return tfill * inv / fill


def settle(j) -> int:
    """Triggered expectations scored like a pass: a day and five days on (and over the market median); then the exit plan, net of
    costs, beside the twin with the same plan. SCORED when both are in."""
    from jarvis.service import brain

    now, n = _now(j), 0
    rows = j.db.execute("SELECT id, coin, plan, fill, fill_t, invalidation, twin_coin, twin_fill, after_5d_pct, plan_pct FROM expectations "
                        "WHERE status='TRIGGERED' AND fill IS NOT NULL AND fill_t <= ?", (now - DAY,)).fetchall()
    bench: dict = {}
    for eid, coin, plan_, fill, ft, inv, tw, tfill, a5_done, plan_done in rows:
        D = _closed_daily(j, coin)
        T = _closed_daily(j, tw) if tw else []
        upd: dict[str, Any] = {}
        if a5_done is None:
            a1 = next((b[4] for b in D if b[0] >= ft), None)                   # as settle_passes: the first close a full day on
            a5 = next((b[4] for b in D if b[0] + DAY >= ft + 5 * DAY), None) if now >= ft + 5 * DAY else None
            if a1 is not None:
                p1, p5 = brain._pct(a1, fill), (brain._pct(a5, fill) if a5 else None)
                day0 = ft - ft % DAY
                m1 = bench.setdefault((day0, 1), brain.market_median_move(j, day0, 1))
                m5 = bench.setdefault((day0, 5), brain.market_median_move(j, day0, 5)) if p5 is not None else None
                upd.update(after_1d_pct=p1, after_5d_pct=p5, after_1d_ex=_sub(p1, m1), after_5d_ex=_sub(p5, m5), cost_rt_pct=round(200 * _cost1(coin), 2))
                if p5 is not None and tfill:
                    t5 = next((b[4] for b in T if b[0] + DAY >= ft + 5 * DAY), None)
                    upd["twin_5d_pct"] = brain._pct(t5, tfill) if t5 else None
        if plan_done is None:
            g = simulate(D, ft, fill, plan_, inv)
            if g is not None:
                upd["plan_pct"] = round(g - 200 * _cost1(coin), 2)
                if tfill:
                    tg = simulate(T, ft, tfill, plan_, _twin_stop(D, T, ft, fill, inv, tfill))
                    upd["twin_plan_pct"] = round(tg - 200 * _cost1(tw), 2) if tg is not None else None
        if not upd:
            continue
        done5 = upd.get("after_5d_pct", a5_done) is not None
        donep = upd.get("plan_pct", plan_done) is not None
        if done5 and donep:
            upd["status"] = "SCORED"
        j.db.execute(f"UPDATE expectations SET {', '.join(k + '=?' for k in upd)} WHERE id=?", (*upd.values(), eid))
        n += 1
    j.db.commit()
    return n


# ---------------------------------------------------------------------------
# what others read: the record, the brief block, the evening line
# ---------------------------------------------------------------------------
def record(j, days: int = 60) -> dict:
    """The morning scan's own record: written, triggered, invalidated, expired; and how the triggered ones did against their twins."""
    _table(j)
    rows = j.db.execute("SELECT status, after_5d_pct, after_5d_ex, cost_rt_pct, twin_coin, twin_5d_pct, plan_pct, twin_plan_pct "
                        "FROM expectations WHERE t >= ?", (_now(j) - days * DAY,)).fetchall()
    by = collections.Counter(r[0] for r in rows)

    def avg(xs):
        xs = [x for x in xs if x is not None]
        return round(sum(xs) / len(xs), 2) if xs else None
    s5 = [r for r in rows if r[1] is not None]
    sp = [r for r in rows if r[6] is not None]
    return {"written": len(rows), "waiting": by["OPEN"], "triggered": by["TRIGGERED"] + by["SCORED"], "invalidated": by["INVALIDATED"],
            "expired": by["EXPIRED"], "scored_5d": len(s5), "avg_5d_net_pct": avg([r[1] - (r[3] or 0) for r in s5]),
            "avg_5d_vs_market_pct": avg([r[2] for r in s5]),
            "avg_twin_5d_net_pct": avg([r[5] - 200 * _cost1(r[4]) for r in s5 if r[5] is not None and r[4]]),
            "plans_done": len(sp), "avg_plan_net_pct": avg([r[6] for r in sp]), "avg_twin_plan_net_pct": avg([r[7] for r in sp]),
            "note": "small numbers mean little until about 10 are scored"}


def brief(j) -> dict | None:
    """The block every market answer reads first (briefs.market_brief): the newest stance, its expectations and the record."""
    r = _row(j)
    if not r:
        return None
    exps = expectations(j, r["day"])
    pos = [p for p in json.loads(r["positions"] or "[]") if p.get("status") in ("WEAKER", "BROKEN")]
    rec = record(j)
    return {"written_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime(r["t"])), "source": r["source"],
            "dial": _dw(r["dial"]), "view": r["view"] or f"(no written view: {r['note'] or 'facts only'})", "changed": r["changed"],
            "facts_changed": json.loads(r["facts_diff"] or "[]")[:4],
            "expectations": [{"coin": e["coin"], "plan": e["plan"], "trigger": f"{e['trigger_type']} {e['trigger_price']:.6g}",
                              "wrong_if_close_under": e["invalidation"], "waits_days": e["horizon_days"], "status": e["status"]} for e in exps],
            "positions_flagged": [{k: p.get(k) for k in ("coin", "status", "why")} for p in pos[:5]],
            "record": {k: rec[k] for k in ("written", "triggered", "scored_5d", "avg_5d_net_pct", "avg_twin_5d_net_pct")},
            "say": SAY}


def evening_line(j, d0: int) -> str:
    """One sentence for the evening review: tonight's stance and what the expectations did since d0 (Toronto midnight)."""
    r = _row(j)
    if not r:
        return ""
    exps = expectations(j, r["day"])
    moved = dict(j.db.execute("SELECT status, COUNT(*) FROM expectations WHERE status != 'OPEN' AND status_t >= ? GROUP BY status", (d0,)).fetchall())
    if r["source"] == "brain":
        first = (r["view"] or "").split(". ")[0].rstrip(".")
        s = f"Tonight's stance: {first}."
        s += (f" Expectations written: {len(exps)} ({', '.join(e['coin'] for e in exps)})." if exps else " No expectation written tonight.")
    else:
        s = f"Tonight's stance: facts only ({r['note'] or 'no model call'})."
    if moved:
        s += " Since midnight: " + ", ".join(f"{v} {k.lower()}" for k, v in sorted(moved.items())) + "."
    return s
