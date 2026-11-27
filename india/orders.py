"""The order module (design part 1 and part 3; flag 239). Used only from the live day; built switched off on the live-path branch.

This is the ONE file that may build requests for Kite's order and GTT endpoints. Everything else keeps using india/kite.py, which stays
GET plus the margin calculator, and which this file does not change. Nothing running imports this file.

What it can do (each through send(), the one gate):
  - a LIMIT buy for the paper line's chosen contract: 1 lot, NRML, valid for 1 minute (TTL), cancelled by us too if unfilled after 60 s
  - the exit: a LIMIT sell now, or an after-market order (AMO, LIMIT) for the next open, so Zerodha sends it at 09:15 IST without the Mac
  - one GTT per position (the broker-side backstop under an index-level stop), and its deletion
What it refuses (each is a test): a MARKET order, more than 1 lot, a contract the paper decision did not choose, a premium over the cap,
a second overnight position, an entry the margin calculator does not cover, an entry whose exit cannot be placed, and any send while
switches.LIVE_ORDERS is off or the kill switch is on. It never chases: an unfilled entry is cancelled and logged "not filled live".
Every send writes one line first (what, why, which paper decision) and one line after (Kite's answer) to live/orders.jsonl in the live
folder (switches.live_dir()), apart from the paper records.
Zerodha facts this relies on (india/live/README.md, read from Zerodha's own pages on 27 Nov 2026): F&O AMOs are taken 15:45-09:11 IST
and sent to the exchange at 09:15; no AMO can be placed, changed or cancelled 01:00-05:30 IST; GTTs work on F&O contracts, trigger on
the contract's own last price, take LIMIT orders only, and expire with the contract.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import time

from india.live import rules, switches
from india.live.rules import Plan

BASE = "https://api.kite.trade"
EXCHANGE = "NFO"
PRODUCT = "NRML"
TICK = 0.05
BAND_TICKS = 2
BAND_PCT = 0.005
FILL_WAIT_S = 60
ENTRY_PATH = "/orders/regular"
AMO_PATH = "/orders/amo"
GTT_PATH = "/gtt/triggers"
AMO_FNO_FROM = dt.time(15, 45)
AMO_FNO_UNTIL = dt.time(9, 11)
AMO_SHUT = (dt.time(1, 0), dt.time(5, 30))
TIME_EXITS = {"T1130": dt.time(11, 30), "T1515": dt.time(15, 15)}
BACKSTOP_WIDEN = 1.25


class Refused(ValueError):
    """A request this module will not build or send, whatever the switches say."""


def _tick_up(x: float) -> float:
    return round(math.ceil(round(x / TICK, 6)) * TICK, 2)


def _tick_down(x: float) -> float:
    return round(max(1, math.floor(round(x / TICK, 6))) * TICK, 2)


def limit_price(side: str, ref: float) -> float:
    """The paper decision's price plus the band (2 ticks and 0.5%, the realistic-fill rule's slippage), on the price step."""
    if ref <= 0:
        raise Refused("no reference price")
    if side == "BUY":
        return _tick_up(ref * (1 + BAND_PCT) + BAND_TICKS * TICK)
    return _tick_down(ref * (1 - BAND_PCT) - BAND_TICKS * TICK)


def _order(plan: Plan, side: str, price: float) -> dict:
    return {"exchange": EXCHANGE, "tradingsymbol": plan.tradingsymbol, "transaction_type": side, "order_type": "LIMIT",
            "quantity": int(plan.lot) * rules.LOTS, "product": PRODUCT, "price": price}


def entry_request(plan: Plan) -> dict:
    data = {**_order(plan, "BUY", limit_price("BUY", plan.price)), "validity": "TTL", "validity_ttl": 1, "tag": "ananta-live"}
    return {"what": "entry", "method": "POST", "path": ENTRY_PATH, "data": data}


def exit_request(plan: Plan, ref_price: float, next_open: bool = False) -> dict:
    data = {**_order(plan, "SELL", limit_price("SELL", ref_price)), "validity": "DAY", "tag": "ananta-live"}
    return {"what": "exit_amo" if next_open else "exit", "method": "POST", "path": AMO_PATH if next_open else ENTRY_PATH, "data": data}


def gtt_request(plan: Plan, trigger: float, last_price: float) -> dict:
    """One single-leg GTT: when the option's own last price falls to `trigger`, a LIMIT sell of the 1 lot (a band under the trigger)."""
    trig = _tick_down(trigger)
    if not 0 < trig < last_price:
        raise Refused(f"a sell backstop must sit under the last price (trigger {trig}, last {last_price})")
    order = _order(plan, "SELL", limit_price("SELL", trig))
    cond = {"exchange": EXCHANGE, "tradingsymbol": plan.tradingsymbol, "trigger_values": [trig], "last_price": last_price}
    return {"what": "gtt", "method": "POST", "path": GTT_PATH, "data": {"type": "single", "condition": json.dumps(cond), "orders": json.dumps([order])},
            "order": order}


def cancel_request(order_id: str, variety: str = "regular") -> dict:
    if variety not in ("regular", "amo"):
        raise Refused(f"unknown variety {variety!r}")
    return {"what": "cancel", "method": "DELETE", "path": f"/orders/{variety}/{order_id}", "data": {}}


def gtt_delete_request(trigger_id: int) -> dict:
    return {"what": "gtt_delete", "method": "DELETE", "path": f"{GTT_PATH}/{int(trigger_id)}", "data": {}}


def validate(req: dict, plan: Plan) -> None:
    """The refusals that hold whatever the switches say. Raises Refused."""
    p = str(req.get("path") or "")
    if not (p in (ENTRY_PATH, AMO_PATH, GTT_PATH) or p.startswith(("/orders/regular/", "/orders/amo/", GTT_PATH + "/"))):
        raise Refused(f"not an order path this module may use: {p}")
    if req.get("method") not in ("POST", "DELETE"):
        raise Refused(f"method {req.get('method')} is not used by this module")
    if req["method"] == "DELETE":
        return
    o = req.get("order") or req.get("data") or {}
    if o.get("order_type") != "LIMIT":
        raise Refused(f"only LIMIT orders (asked {o.get('order_type')!r}); never a market order on options")
    if int(o.get("quantity") or 0) != int(plan.lot) * rules.LOTS or not plan.lot:
        raise Refused(f"exactly 1 lot ({plan.lot}); asked {o.get('quantity')}")
    if o.get("tradingsymbol") != plan.tradingsymbol or not plan.tradingsymbol or o.get("exchange") != EXCHANGE:
        raise Refused(f"{o.get('tradingsymbol')} is not the contract the paper decision chose ({plan.tradingsymbol})")
    if o.get("product") != PRODUCT:
        raise Refused("NRML only")
    price = float(o.get("price") or 0)
    if price <= 0 or abs(round(price / TICK) * TICK - price) > 1e-6:
        raise Refused(f"price {price} is not on the 0.05 step")
    want = "BUY" if req["what"] == "entry" else "SELL"
    if o.get("transaction_type") != want:
        raise Refused(f"{req['what']} must be a {want}")


# ---------------------------------------------------------------- the ledger and the one gate
def ledger_path():
    return switches.live_dir() / "live" / "orders.jsonl"


def _ledger(line: dict) -> None:
    f = ledger_path()
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a") as fh:
        fh.write(json.dumps({"t": round(time.time(), 3), **line}, sort_keys=True, default=str) + "\n")


def read_ledger() -> list[dict]:
    try:
        return [json.loads(x) for x in ledger_path().read_text().splitlines() if x.strip()]
    except FileNotFoundError:
        return []


def _ref(plan: Plan) -> dict:
    return {"date": plan.date, "index": plan.index, "point": plan.point, "tradingsymbol": plan.tradingsymbol}


def note(plan: Plan, what: str, why: str, **extra) -> None:
    """A line in the ledger for a decision that sent nothing (a skip, not filled live, a dry run)."""
    _ledger({"step": "note", "what": what, "why": why, "decision": _ref(plan), **extra})


def send(kite, req: dict, plan: Plan, why: str) -> dict:
    """The one gate. Validate, write the line before, ask the switches, send, write the line after. Nothing else in the live path
    reaches Kite's order or GTT endpoints."""
    validate(req, plan)
    _ledger({"step": "before", "what": req["what"], "method": req["method"], "path": req["path"], "data": req["data"], "why": why,
             "decision": _ref(plan)})
    try:
        switches.require_send()
    except switches.OrdersOff as e:
        _ledger({"step": "after", "what": req["what"], "ok": False, "sent": False, "answer": f"refused at the gate: {e}", "decision": _ref(plan)})
        raise
    try:
        ans = _http(kite, req)
    except Exception as e:  # noqa: BLE001  logged, counted, raised
        _ledger({"step": "after", "what": req["what"], "ok": False, "sent": True, "answer": f"{type(e).__name__}: {e}"[:300], "decision": _ref(plan)})
        switches.note_failure(f"{req['what']} {plan.tradingsymbol}: {type(e).__name__}")
        raise
    _ledger({"step": "after", "what": req["what"], "ok": True, "sent": True, "answer": ans, "decision": _ref(plan)})
    switches.note_success()
    return ans or {}


def _http(kite, req: dict) -> dict:
    """The only network call to an order or GTT endpoint. Reached only from send(), after switches.require_send()."""
    switches.require_send()
    r = kite.s.request(req["method"], BASE + req["path"], data=req["data"] or None, timeout=20)
    r.raise_for_status()
    return r.json().get("data") or {}


# ---------------------------------------------------------------- the exits (design part 3)
def amo_window_open(t_ist: dt.time) -> bool:
    """May an F&O after-market order be placed at this India time? 15:45-09:11 IST, never 01:00-05:30 IST (Zerodha's maintenance)."""
    if AMO_SHUT[0] <= t_ist < AMO_SHUT[1]:
        return False
    return t_ist >= AMO_FNO_FROM or t_ist <= AMO_FNO_UNTIL


def backstop_trigger(option_price: float, delta: float, index_entry: float, index_stop: float, widen: float = BACKSTOP_WIDEN) -> float:
    """The option price that matches the index stop (from the option's delta at entry), placed `widen` times further away, so the
    broker's GTT fires only if the Mac has missed the index stop. Never under one price step."""
    move = abs(float(delta)) * abs(float(index_entry) - float(index_stop)) * float(widen)
    return _tick_down(max(TICK, float(option_price) - move))


def index_stop_hit(option_type: str, index_level: float, index_stop: float) -> bool:
    """A bought call (CE) is stopped when the index falls to its stop; a bought put (PE) when it rises to it."""
    return index_level <= index_stop if option_type == "CE" else index_level >= index_stop


def exit_route(plan: Plan) -> tuple[bool, str]:
    """Can this decision's exit be placed? Asked before the entry: the module never enters a trade whose exit it cannot place."""
    x = plan.exit
    if x == rules.OVERNIGHT_EXIT:
        return True, "an AMO at Zerodha from 15:45 IST, sent at the next 09:15 without the Mac"
    if x in rules.INDEX_STOP_EXITS:
        need = ("delta", "index_entry", "index_stop")
        if all(plan.extra.get(k) is not None for k in need):
            return True, "the Mac watches the index each minute; a GTT backstop on the option at Zerodha; else a LIMIT sell at 15:15 IST"
        return False, "an index-level stop with no delta or stop level: its GTT backstop cannot be set"
    if x in TIME_EXITS:
        if plan.extra.get("option_backstop"):
            return True, f"a LIMIT sell at {TIME_EXITS[x]:%H:%M} IST; a GTT backstop until it fills"
        return False, "a time exit with no backstop price: if the Mac misses the time, nothing at Zerodha closes it"
    return False, f"unknown exit {x!r}"


def alert_step(plan: Plan) -> str:
    """The exact step for Madhav when the Mac cannot act on an open position (sent as a HIGH phone alert by the caller)."""
    return f"Open Kite, Positions, exit {plan.tradingsymbol}, 1 lot ({int(plan.lot) * rules.LOTS} units), as a LIMIT sell near the bid."


def _refused(plan: Plan, what: str, why: str) -> dict:
    note(plan, what, why)
    return {"done": False, "why": why}


# ---------------------------------------------------------------- the steps the live day would run (none runs today)
def enter(kite, plan: Plan, held: list[Plan], why: str = "the paper line's decision") -> dict:
    """The live entry for one paper decision: the rules, the margin calculator, the exit route, then the gate."""
    v, reason = rules.verdict(plan, held)
    if v != "trade":
        return _refused(plan, "skip", reason)
    ok, reason = exit_route(plan)
    if not ok:
        return _refused(plan, "skip", f"skip: the exit cannot be placed ({reason})")
    ok, mwhy, need = rules.margin_check(kite, plan, held)
    if not ok:
        return _refused(plan, "skip", f"skip: {mwhy}")
    try:
        ans = send(kite, entry_request(plan), plan, f"{why}; margin Rs {need:,.0f}; exit: {reason}")
    except switches.OrdersOff as e:
        return {"done": False, "why": f"refused at the gate: {e}"}
    return {"done": True, "order_id": ans.get("order_id"), "exit_route": reason}


def cancel_if_unfilled(kite, plan: Plan, order_id: str, placed_t: float, filled: bool, now: float | None = None) -> dict:
    """After 60 seconds an unfilled entry is cancelled and logged 'not filled live'. It never chases."""
    now = time.time() if now is None else now
    if filled or now - placed_t < FILL_WAIT_S:
        return {"done": False, "why": "filled" if filled else "still inside the 60 seconds"}
    try:
        send(kite, cancel_request(order_id), plan, "unfilled after 60 s: not filled live, never chased")
    except switches.OrdersOff as e:
        return {"done": False, "why": f"refused at the gate: {e}"}
    note(plan, "not_filled_live", "the entry was not filled within 60 s and was cancelled")
    return {"done": True}


def after_fill(kite, plan: Plan, fill_price: float) -> dict:
    """Right after an entry fills: an index-stop exit gets its GTT backstop at once. If the backstop cannot be placed, the position is
    exited now and Madhav gets the exact step."""
    if plan.exit not in rules.INDEX_STOP_EXITS and not plan.extra.get("option_backstop"):
        return {"done": False, "why": "no backstop for this exit (the next-open AMO is placed from 15:45 IST)"}
    trig = plan.extra.get("option_backstop") or backstop_trigger(fill_price, plan.extra["delta"], plan.extra["index_entry"], plan.extra["index_stop"])
    try:
        ans = send(kite, gtt_request(plan, trig, fill_price), plan, f"GTT backstop at {trig} under the index stop")
    except switches.OrdersOff as e:
        return {"done": False, "why": f"refused at the gate: {e}"}
    except Exception as e:  # noqa: BLE001  the backstop failed: get out, and tell Madhav
        out = exit_now(kite, plan, fill_price, f"the GTT backstop failed ({type(e).__name__})")
        return {"done": False, "why": "the backstop failed; exited now", "exit": out, "alert": alert_step(plan)}
    return {"done": True, "trigger_id": ans.get("trigger_id"), "trigger": trig}


def exit_now(kite, plan: Plan, ref_price: float, why: str) -> dict:
    """A LIMIT sell now (an index stop the Mac saw, a time exit, a failed backstop)."""
    try:
        ans = send(kite, exit_request(plan, ref_price), plan, why)
    except switches.OrdersOff as e:
        return {"done": False, "why": f"refused at the gate: {e}", "alert": alert_step(plan)}
    except Exception as e:  # noqa: BLE001
        return {"done": False, "why": f"the exit failed ({type(e).__name__})", "alert": alert_step(plan)}
    return {"done": True, "order_id": ans.get("order_id")}


def exit_next_open(kite, plan: Plan, ref_price: float, t_ist: dt.time) -> dict:
    """After the close (from 15:45 IST): the next-open exit as an AMO, so Zerodha sends it at 09:15 IST without the Mac."""
    if not amo_window_open(t_ist):
        return {"done": False, "why": f"outside the F&O AMO window at {t_ist:%H:%M} IST", "alert": alert_step(plan)}
    try:
        ans = send(kite, exit_request(plan, ref_price, next_open=True), plan, "the next-open exit, as an AMO")
    except switches.OrdersOff as e:
        return {"done": False, "why": f"refused at the gate: {e}", "alert": alert_step(plan)}
    except Exception as e:  # noqa: BLE001
        return {"done": False, "why": f"the AMO failed ({type(e).__name__})", "alert": alert_step(plan)}
    return {"done": True, "order_id": ans.get("order_id")}


def morning_check(kite, plan: Plan, amo_order_id: str, filled: bool, t_ist: dt.time, new_ref: float | None = None,
                  repriced: bool = False) -> dict:
    """The 09:15 job: the AMO filled, or by 09:20 IST it is re-priced once (cancel, then a LIMIT sell at the new price); then an alert."""
    if filled:
        return {"done": True, "why": "the next-open exit filled"}
    if t_ist < dt.time(9, 20):
        return {"done": False, "why": "waiting until 09:20 IST"}
    if repriced or new_ref is None:
        return {"done": False, "why": "not filled after one re-price", "alert": alert_step(plan)}
    try:
        send(kite, cancel_request(amo_order_id, "amo"), plan, "the AMO did not fill by 09:20 IST: re-priced once")
    except switches.OrdersOff as e:
        return {"done": False, "why": f"refused at the gate: {e}", "alert": alert_step(plan)}
    except Exception as e:  # noqa: BLE001
        return {"done": False, "why": f"the cancel failed ({type(e).__name__})", "alert": alert_step(plan)}
    return exit_now(kite, plan, new_ref, "the re-price of the next-open exit (once)")
