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
        user = ("Tonight's facts (JSON):\n" + json.dumps(f, default=str, separators=(",", ":")) + "\n\nThe knowledge list:\n"
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
        gwhy = None
        if pick:                                     # the trade guard: the kill switch again, and the pick's price age
            t_seen, lim = seen.get(pick["coin"], (None, None))
            gwhy = tg.blocked(j, WATCH, pick["coin"], price_t=t_seen, max_age_s=lim)
        if pick and gwhy:
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
    j.db.execute("INSERT INTO bold_decisions (id, day, t, dial, action, coin, plan, price, stop, thesis, why, model, cost_usd, trade_id, "
                 "random_id, note) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                 (did, day, now, dial, res["action"], res.get("coin"), res.get("plan"), res.get("price"), res.get("stop"), res.get("thesis"),
                  res.get("why"), res.get("model"), res["cost_usd"], res.get("trade_id"), res.get("random_id"), res.get("note") or None))
    j.db.commit()
    return res
