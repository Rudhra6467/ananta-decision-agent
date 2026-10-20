"""The bold book (agent fix A8): a second paper book with a brave written mandate (docs/knowledge/bold_mandate.json).

OFF until Madhav approves. Two locks, both needed: BOLD_BOOK=1 in the service's environment AND "approved" filled in the mandate
file by him. Either one missing and run() returns at once: no model call, no trade, nothing spent.

When on, once per UTC day after the daily close (after the stance, whose facts it reads):
  dial OPEN    the brain must pick its single best tier-A idea and take it ($100 paper, one of the tested exit plans, the
               invalidation written first). A PASS, or a pick the code rejects, is asked once more, then recorded as a mandate MISS.
  dial CLOSED  it may take one or sit; either way the reason is written.
Every trade opens a random tier-A twin (RANDOM_BOLD) at the same moment with the same plan in its own daily ranges. The trades are
the brain's kind (source 'brain'): live stops by brain.manage_live, daily time exits by the watch engine (the 10) and
universe_watch.manage_live_rows (the rest). Its model call is logged as thread 'bold', so it never touches the safe book's budget.
Paper only: nothing here reaches Hands or an exchange.

T3 in the pack (Madhav, 2026-10-20 12:08 Toronto: "4. yes"): the pick input carries each candidate's T3 rating for tonight's close
(`t3` IN or OUT, t3_ratings below: the T3 books' own decision for that close, else portfolio_layer.rate on the coin's daily candles,
as review #37 defines it), with T3's exit worded as what it is: out on a daily close under the 20-day average, not a 20-day hold.
The mandate is unchanged. A pick whose thesis or why cites T3 (review #37's words: the card's id or its aliases, ignoring case) for
a coin T3 rates OUT is saved with flag 'cites_t3_on_out'. It is never blocked: the bold book is a registered experiment, so the
decision stays with the brain; the flag lets review #37's question B be scored. Rows written with this pack carry pack 't3-v1',
which is where review #37's window splits (bold_mandate.json, amendment of 2026-10-20).
"""
from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Callable

WATCH, TWIN = "JARVIS_BOLD", "RANDOM_BOLD"
DAY = 86400
STOP_MAX = 0.15
PACK = "t3-v1"                                         # Madhav, 2026-10-20: "4. yes" (each candidate's T3 rating in the pick input)
T3_BOOKS = ("portfolio_book.sqlite", "portfolio_book_t30.sqlite")   # the 10, then the 30-coin tier (review #37's order)
T3_CITES = ("t3", "trend portfolio", "portfolio layer")  # review #37: the T3 card's id and its aliases (status_cards.json), any case
FLAG_T3_OUT = "cites_t3_on_out"
T3_WORDS = ("T3 tonight: each candidate's `t3` is the trend portfolio's own rating for tonight's daily close. IN: T3 holds the coin "
            "today (its daily close above its 20-day AND its 50-day average, with Bitcoin's close above its own 50-day). OUT: T3 does "
            "not hold it. T3's '20-day exit' is an exit RULE: out on the first daily close under the 20-day average. It is NOT a "
            "20-day hold; the TREND exit plan's 20 days is a separate time exit. T3 backs a coin only on a day it rates it IN.")

SYSTEM = """You are Ananta's decision brain running the BOLD paper book (crypto, long only, spot, paper only) under a written mandate
that differs from the safe book's: on a day the exposure dial is OPEN you MUST pick your single best idea among the candidates and
take it; there is no PASS. On a day the dial is CLOSED you may take one or sit, and you must say why.
- Pick from candidates only (tier A, with tonight's daily candle). Use the facts and the knowledge list; measured edges outrank
  ideas, and FAILED items are never the reason.
- Choose one tested exit plan: DIP (out after 10 days, no stop; still write where the idea is wrong as the stop), ZONE or TREND
  (out after 20 days with the stop). The stop: where the idea is wrong, under the price and at most 15% away. No target.
- Fixed $100. You are scored against a random tier-A coin traded with the same plan at the same moment, against doing nothing,
  and against the market median over the same days.
Reply with ONE JSON object only:
{"action": "TAKE" | "SIT", "coin": "...", "exit_plan": "DIP" | "ZONE" | "TREND", "stop": price,
 "thesis": "one or two sentences: why this is the best idea today", "why_not_others": "one sentence", "knowledge_used": ["ids"]}"""


def _path():
    from jarvis.service.core import docs_dir

    return docs_dir(".") / "knowledge" / "bold_mandate.json"


def mandate() -> dict:
    try:
        return json.loads(_path().read_text())
    except Exception:  # noqa: BLE001
        return {}


def enabled() -> tuple[bool, str]:
    """Both locks or nothing."""
    if os.getenv("BOLD_BOOK", "0") != "1":
        return False, "off: BOLD_BOOK is not 1 in the service's environment"
    if not mandate().get("approved"):
        return False, "off: the mandate is not approved by Madhav yet (docs/knowledge/bold_mandate.json)"
    return True, ""


def _ai_ok(j) -> tuple[bool, str]:
    """The same switches the brain obeys: BRAIN_ENABLED, Ask switched on, and the day's whole AI budget not used up."""
    if os.getenv("BRAIN_ENABLED", "1") != "1":
        return False, "the brain is switched off (BRAIN_ENABLED)"
    try:
        from jarvis.service import brain
        from jarvis.service.ask import Ask

        a = Ask(j)
        if a.setting("ask_enabled") != "1":
            return False, "Ask Ananta (the AI) is switched off"
        if a.spend().get("left_usd", 1) < brain.MIN_BUDGET:
            return False, "today's AI budget is used up"
    except Exception as exc:  # noqa: BLE001  fail closed (Oct 15): a switch or budget that cannot be read is not a yes
        return False, f"the AI switch or budget could not be read ({str(exc)[:80]})"
    return True, ""


def _table(j) -> None:
    j.db.execute("CREATE TABLE IF NOT EXISTS bold_decisions (id TEXT PRIMARY KEY, day TEXT, t INTEGER, dial REAL, action TEXT, coin TEXT, "
                 "plan TEXT, price REAL, stop REAL, thesis TEXT, why TEXT, model TEXT, cost_usd REAL, trade_id TEXT, random_id TEXT, note TEXT)")
    have = {r[1] for r in j.db.execute("PRAGMA table_info(bold_decisions)").fetchall()}
    for col in ("pack", "t3", "flag", "knowledge_used"):          # Oct 20 ("4. yes"): the pack version, T3's ratings, the flag
        if col not in have:
            j.db.execute(f"ALTER TABLE bold_decisions ADD COLUMN {col} TEXT")


def _close_t(f: dict, now: int) -> int:
    """The close time (day_close_t, as portfolio_layer.daily_view writes it) of the daily candle the facts were built on."""
    import calendar

    day = f.get("candle_closed_utc")
    if day:
        return calendar.timegm(time.strptime(day, "%Y-%m-%d")) + DAY
    return now - now % DAY


def _book_ratings(base, close_t: int) -> dict:
    """coin -> rating from the T3 books' own decision for that close (read-only; a missing book or day gives nothing)."""
    import sqlite3
    from pathlib import Path

    out: dict = {}
    for name in T3_BOOKS:
        f = Path(base) / name
        if not f.exists():
            continue
        try:
            con = sqlite3.connect(f"file:{f}?mode=ro", uri=True)
            try:
                r = con.execute("SELECT json FROM decisions WHERE day_t=?", (close_t,)).fetchone()
            finally:
                con.close()
        except sqlite3.Error:
            continue
        for coin, x in ((json.loads(r[0]) if r else {}).get("ratings") or {}).items():
            out.setdefault(coin.upper(), {"t3": "IN" if x.get("hold") else "OUT", "rating": x.get("rating"),
                                          "why": list(x.get("why") or [])[:2], "source": name})
    return out


def _view(D: list[tuple]):
    from src.intelligence import portfolio_layer as pl
    from src.intelligence.explorer_engine import TfState

    tf = TfState("1d")
    for b in D:
        tf.add(*b[:6])
    return pl.daily_view(tf)


def t3_ratings(j, f: dict, daily: Callable | None = None) -> dict:
    """Each candidate's T3 rating for the close the facts were built on: {coin: {t3: IN|OUT|None, rating, why, source}}.
    The T3 books' own decision for that close when one holds the coin; otherwise portfolio_layer.rate on the coin's closed daily
    candles up to that close, Bitcoin's close against its own 50-day as the market gate (review #37, question B). The momentum rank
    is left out there (it moves STRONG/OK/WEAK only, never IN or OUT). None: not enough candles to rate."""
    from src.intelligence import portfolio_layer as pl

    if daily is None:
        from jarvis.service import stance

        daily = lambda c: stance._closed_daily(j, c)  # noqa: E731
    close_t = _close_t(f, int(j.now()))
    coins = [str(c.get("coin") or "").upper() for c in f.get("candidates") or []]
    books = _book_ratings(j.dir, close_t)
    out: dict = {}
    views: dict = {}

    def view(c):
        if c not in views:
            try:
                views[c] = _view([b for b in daily(c) if b[0] + DAY <= close_t])
            except Exception:  # noqa: BLE001
                views[c] = None
        return views[c]
    for c in coins:
        if c in books:
            out[c] = books[c]
            continue
        v, btc = view(c), view("BTC")
        if not v or not btc:
            out[c] = {"t3": None, "rating": None, "why": ["not enough daily candles to rate"], "source": "computed"}
            continue
        r, on, why = pl.rate(c, v, btc["close"] > btc["ema50"], None)
        out[c] = {"t3": "IN" if on else "OUT", "rating": r, "why": why[:2], "source": "computed"}
    return out


def cites_t3(*texts) -> bool:
    """Review #37's 'cites T3': the text contains the T3 card's id or one of its aliases, ignoring case."""
    t = " ".join(str(x or "") for x in texts).lower()
    return any(k in t for k in T3_CITES)


def t3_flag(coin: str | None, t3: dict, *texts) -> str | None:
    """'cites_t3_on_out' when the pick cites T3 for a coin T3 rates OUT that day; never a block."""
    if not coin or not cites_t3(*texts):
        return None
    return FLAG_T3_OUT if (t3.get(coin.upper()) or {}).get("t3") == "OUT" else None


def pack_facts(f: dict, t3: dict) -> dict:
    """The facts the bold pick reads: tonight's stance facts with each candidate's T3 rating added (the stance's own copy is untouched)."""
    g = dict(f)
    g["candidates"] = [{**c, "t3": (t3.get(str(c.get("coin") or "").upper()) or {}).get("t3"),
                        "t3_rating": (t3.get(str(c.get("coin") or "").upper()) or {}).get("rating")} for c in f.get("candidates") or []]
    return g


def _day(t: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(t))


def spent_today(j) -> float:
    """The bold book's own model money today (Toronto day, like the brain's), from ask_messages thread 'bold'."""
    from jarvis.service import brain

    try:
        return float(j.db.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM ask_messages WHERE thread='bold' AND t >= ?",
                                  (brain._today0(j),)).fetchone()[0] or 0.0)
    except Exception:  # noqa: BLE001
        return 0.0


def _log(j, usage: dict, cost: float, ms: int) -> None:
    try:
        j.db.execute("INSERT INTO ask_messages (id, thread, t, role, text, reply, provider, model, ms, tokens_in, tokens_out, tools, error, cost_usd, "
                     "mode, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (uuid.uuid4().hex, "bold", int(j.now()), "assistant", "bold book daily pick", "", "sonnet", usage.get("model"), ms,
                      usage.get("in", 0) + usage.get("cache_read", 0) + usage.get("cache_write", 0), usage.get("out", 0), "", None, cost,
                      "worker", "bold book (fix A8)"))
        j.db.commit()
    except Exception:  # noqa: BLE001  a test database may not have the table
        pass


def _parse(text: str) -> dict:
    from jarvis.service import brain

    blk = brain._json_block(text)
    if not blk:
        raise ValueError("no JSON in the reply")
    d = json.loads(blk)
    if not isinstance(d, dict) or d.get("action") not in ("TAKE", "SIT"):
        raise ValueError("action must be TAKE or SIT")
    return d


def check(d: dict, f: dict, live: dict) -> tuple[dict | None, str]:
    """A TAKE the code accepts, or the reason it does not (never repaired)."""
    from jarvis.service import brain

    if d.get("action") != "TAKE":
        return None, "no TAKE"
    cands = {c["coin"] for c in f.get("candidates") or []}
    coin = str(d.get("coin") or "").upper()
    if coin not in cands:
        return None, f"{coin or '?'} is not a tier-A candidate with tonight's candle"
    plan = str(d.get("exit_plan") or "").upper()
    if plan not in brain.EXIT_PLANS:
        return None, "the exit plan must be DIP, ZONE or TREND"
    px = live.get(coin)
    if not px:
        return None, f"no live price for {coin}"
    try:
        stop = float(d.get("stop"))
    except (TypeError, ValueError):
        return None, "no stop"
    if not (px * (1 - STOP_MAX) <= stop < px):
        return None, f"the stop {stop:g} must be under the price {px:g} and at most 15% away"
    return {"coin": coin, "plan": plan, "price": px, "stop": stop, "thesis": str(d.get("thesis") or "")[:400]}, ""


def record(j) -> dict:
    """The bold book against its twins: closed trades, average per $100 after costs, and the misses of its mandate."""
    _table(j)
    me = [r[0] or 0.0 for r in j.db.execute("SELECT net_usd FROM evidence_trades WHERE watch=? AND status='CLOSED'", (WATCH,))]
    tw = [r[0] or 0.0 for r in j.db.execute("SELECT net_usd FROM evidence_trades WHERE watch=? AND status='CLOSED'", (TWIN,))]
    acts = dict(j.db.execute("SELECT action, COUNT(*) FROM bold_decisions GROUP BY action").fetchall())
    return {"closed": len(me), "avg_usd_per_100": round(sum(me) / len(me), 2) if me else None,
            "twin_closed": len(tw), "twin_avg_usd_per_100": round(sum(tw) / len(tw), 2) if tw else None,
            "open": j.db.execute("SELECT COUNT(*) FROM evidence_trades WHERE watch=? AND status='OPEN'", (WATCH,)).fetchone()[0],
            "decisions": acts, "enabled": enabled()[0], "why_off": enabled()[1] or None}


def _open_pair(j, did: str, pick: dict) -> tuple[dict, dict | None]:
    """The trade and its random tier-A twin, exactly as the brain opens its own (same plan in the twin's own daily ranges)."""
    from jarvis.service import brain, stance

    ep = brain.EXIT_PLANS[pick["plan"]]
    atr = brain._atr(j, pick["coin"]) or 0.0
    live_stop = 0.0 if ep.get("no_stop") else pick["stop"]
    regime = brain._regime_now(j)
    det = {"bold": did, "thesis": pick["thesis"], "size_pct": 100.0, "exit_plan": pick["plan"], "invalidation": pick["stop"]}
    trade = brain._open(j, WATCH, pick["coin"], pick["price"], live_stop, None, None, ep["days"], atr, det, regime)
    pool = [c for c in stance.candidates(j) if c != pick["coin"] and brain._live_px(j, c)]
    rc = brain._random_coin(j, pick["coin"], int(j.now()), pool)
    rnd = None
    if rc and atr:
        from jarvis.service import trade_guard as tg

        ratr, rp = brain._atr(j, rc), brain._live_px(j, rc)
        if ratr and rp:                                  # the twin opens only on its own fresh price (the trade guard)
            _, t_seen, lim = brain._live_quote(j, rc)
            if tg.blocked(j, TWIN, rc, price_t=t_seen, max_age_s=lim):
                ratr = None
        if ratr and rp:
            k = (pick["price"] - pick["stop"]) / atr
            rnd = brain._open(j, TWIN, rc, rp, (rp - k * ratr) if live_stop else 0.0, None, None, ep["days"], ratr,
                              {"bold": did, "twin_of": trade["id"], "thesis": f"random twin of {pick['coin']}"}, regime)
    return trade, rnd


def run(j, call: Callable | None = None) -> dict | None:
    """Once per UTC day, after tonight's stance. Off unless both locks are open. While the trade guard's kill switch is on (or
    cannot be read) it waits without a model call and tries again at the next run; a pick whose price is too old is BLOCKED."""
    from jarvis.service import brain, stance
    from jarvis.service import trade_guard as tg

    ok, why = enabled()
    if not ok:
        return {"off": why}
    _table(j)
    now = int(j.now())
    day = _day(now)
    if j.db.execute("SELECT 1 FROM bold_decisions WHERE day=?", (day,)).fetchone():
        return None
    srow = stance._row(j)
    if not srow or srow["day"] != day:
        return {"waiting": "for tonight's stance"}
    kill_why = tg.blocked(j, WATCH)
    if kill_why:
        return {"blocked": kill_why}
    f = json.loads(srow["facts"] or "{}")
    dial = (f.get("dial") or {}).get("dial")
    must = bool(dial and dial > 0)
    budget = float((mandate().get("parameters") or {}).get("budget_usd_per_day") or 0.05)
    did = uuid.uuid4().hex[:12]
    res: dict[str, Any] = {"id": did, "day": day, "dial": dial, "action": None, "cost_usd": 0.0, "note": ""}
    ai_ok, ai_why = _ai_ok(j)
    if spent_today(j) >= budget or not ai_ok:
        res.update(action="MISS" if must else "SIT", note=ai_why or f"the bold book's ${budget:.2f} for today is used")
    else:
        know = [{"id": k, "status": s, "what": w} for k, s, w in brain.KNOWLEDGE]
        try:
            t3 = t3_ratings(j, f)
        except Exception as exc:  # noqa: BLE001  the pick still runs; the row says T3 could not be read
            t3, res["note"] = {}, f"T3 ratings could not be read ({str(exc)[:80]})"
        res["t3"] = t3
        user = ("Tonight's facts (JSON):\n" + json.dumps(pack_facts(f, t3), default=str, separators=(",", ":")) + "\n\n" + T3_WORDS
                + "\n\nThe knowledge list:\n"
                + json.dumps(know, separators=(",", ":")) + "\n\nYour bold record so far: " + json.dumps(record(j), default=str)
                + ("\n\nThe dial is OPEN: you must take one." if must else "\n\nThe dial is CLOSED: take one or sit, and say why."))
        live = {c["coin"]: brain._live_px(j, c["coin"]) for c in f.get("candidates") or []}
        seen = {c: brain._live_quote(j, c)[1:] for c in live}          # when each price was seen, for the trade guard
        call = call or (lambda u: stance._call(SYSTEM, u))
        pick, d, reason = None, {}, ""
        for attempt in range(2):
            t0 = time.time()
            try:
                text, usage = call(user if attempt == 0 else user + f"\n\nYour last reply was not accepted ({reason}). The mandate: "
                                   "reply with ONE JSON object; on an OPEN day action must be TAKE with a coin from candidates.")
            except Exception as exc:  # noqa: BLE001
                reason = f"the model call failed ({str(exc)[:100]})"
                break
            cost = brain._price(usage)
            _log(j, usage, cost, int(1000 * (time.time() - t0)))
            res["cost_usd"] += cost
            res["model"] = usage.get("model")
            try:
                d = _parse(text)
            except (ValueError, json.JSONDecodeError) as exc:
                reason = f"unreadable reply: {exc}"
                continue
            if d["action"] == "SIT" and not must:
                break
            pick, reason = check(d, f, live)
            if pick:
                break
        held = None
        if pick:                                     # no stacking (Madhav, Oct 16): a coin the book already holds is not bought again
            held = j.db.execute("SELECT id FROM evidence_trades WHERE watch=? AND coin=? AND status='OPEN' LIMIT 1",
                                (WATCH, pick["coin"])).fetchone()
        gwhy = None
        if pick and not held:                        # the trade guard: the kill switch again, and the pick's price age
            t_seen, lim = seen.get(pick["coin"], (None, None))
            gwhy = tg.blocked(j, WATCH, pick["coin"], price_t=t_seen, max_age_s=lim)
        if pick and held:
            res.update(action="WOULD_ADD", coin=pick["coin"], plan=pick["plan"], price=pick["price"], stop=pick["stop"], thesis=pick["thesis"],
                       why=str(d.get("why_not_others") or "")[:300],
                       note=f"no stacking: the book already holds an open {pick['coin']} trade ({held[0]}); the pick is recorded, nothing opened")
        elif pick and gwhy:
            res.update(action="BLOCKED", coin=pick["coin"], plan=pick["plan"], price=pick["price"], stop=pick["stop"], thesis=pick["thesis"],
                       note="trade guard: " + gwhy)
        elif pick:
            trade, rnd = _open_pair(j, did, pick)
            res.update(action="TAKE", coin=pick["coin"], plan=pick["plan"], price=pick["price"], stop=pick["stop"], thesis=pick["thesis"],
                       why=str(d.get("why_not_others") or "")[:300], trade_id=trade["id"], random_id=rnd["id"] if rnd else None)
        elif d.get("action") == "SIT" and not must:
            res.update(action="SIT", why=str(d.get("thesis") or d.get("why_not_others") or "")[:400])
        else:
            res.update(action="MISS" if must else "SIT", note=("mandate miss: " if must else "") + (reason or "no pick")[:300])
        res["knowledge_used"] = d.get("knowledge_used") if isinstance(d.get("knowledge_used"), list) else None
        res["flag"] = t3_flag(res.get("coin"), t3, res.get("thesis"), res.get("why"))
    j.db.execute("INSERT INTO bold_decisions (id, day, t, dial, action, coin, plan, price, stop, thesis, why, model, cost_usd, trade_id, "
                 "random_id, note, pack, t3, flag, knowledge_used) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (did, day, now, dial, res["action"], res.get("coin"), res.get("plan"), res.get("price"), res.get("stop"), res.get("thesis"),
                  res.get("why"), res.get("model"), res["cost_usd"], res.get("trade_id"), res.get("random_id"), res.get("note") or None,
                  PACK if "t3" in res else None, json.dumps(res["t3"]) if "t3" in res else None, res.get("flag"),
                  json.dumps(res["knowledge_used"]) if res.get("knowledge_used") else None))
    j.db.commit()
    return res
