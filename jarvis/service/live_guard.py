"""The live-money guard (plan Batch 6, D12): plain code, outside the AI, that every real NDAX order must pass. NOT WIRED to any
order path yet: wiring it into Hands is a safety change for Madhav's review (docs/LIVE_MONEY_SAFETY.md). Today it checks the $500
paper book, so the rules are exercised every day before any money depends on them.

  check_order(j, side, coin, value_cad, sleeve)   -> {"ok", "why"}: buys pass only when the brakes allow, the sleeve has room, the
                                                     trade is within 10% of the book and the coin trades in CAD on NDAX; sells always pass
  kill_plan(j)                                    -> what the kill switch would do now: cancel every open order, then sell every
                                                     holding at the bid, back to CAD (a dry run: nothing is sent)
  stops_plan(j)                                   -> the resting stop each setup holding should carry on NDAX (6 x ATR under entry)
"""
from __future__ import annotations

from src.research import book500 as B

SLEEVE_CAP = {"CORE": sum(B.CORE.values()), "EDGE": B.EDGE_SLEEVE, "JUDGMENT": B.JUDGMENT_SLEEVE}


def _state(j) -> dict:
    from jarvis.service import ndax_book

    ndax_book._table(j)
    return ndax_book._get(j, "state") or {}


def check_order(j, side: str, coin: str, value_cad: float, sleeve: str = "EDGE", inst: dict | None = None, now: float | None = None) -> dict:
    import time

    side = (side or "").upper()
    if side == "SELL":
        return {"ok": True, "why": "sells are always allowed"}
    if side != "BUY":
        return {"ok": False, "why": "side must be BUY or SELL"}
    s = _state(j)
    if not s:
        return {"ok": False, "why": "the book has not started"}
    from jarvis.service import ndax_book

    b = ndax_book._brakes(s.get("brakes"))
    t = int(now or time.time())
    if b.paused:
        return {"ok": False, "why": "PAUSED after a 15% fall from the peak; only Madhav can resume"}
    if not b.may_buy(t - t % 86400):
        return {"ok": False, "why": f"a brake is on until {B._day(b.block_until)}"}
    if inst is not None and coin not in inst:
        return {"ok": False, "why": f"{coin} does not trade against CAD on NDAX"}
    value = s.get("value") or B.START_CAD
    if sleeve != "CORE" and value_cad > B.MAX_PER_TRADE * value + 0.01:
        return {"ok": False, "why": f"over 10% of the book (${B.MAX_PER_TRADE * value:.2f})"}
    used = sum(p["paid"] for p in s.get("pos", {}).values() if p["sleeve"] == sleeve)
    cap = SLEEVE_CAP.get(sleeve)
    if cap is None:
        return {"ok": False, "why": f"unknown sleeve {sleeve}"}
    if used + value_cad > cap * value + 0.01:
        return {"ok": False, "why": f"the {sleeve} sleeve is full ({used:.2f} of {cap * value:.2f})"}
    if value_cad > s.get("cash", 0):
        return {"ok": False, "why": "not enough cash"}
    return {"ok": True, "why": "within the brakes and limits"}


def kill_plan(j) -> dict:
    s = _state(j)
    pos = s.get("pos") or {}
    steps = ["cancel every open order on NDAX (CancelAllOrders)"]
    total = s.get("cash", 0.0)
    for c, p in sorted(pos.items()):
        steps.append(f"sell {p['qty']:.8f} {c} at the bid (about ${p['qty'] * p['last']:.2f})")
        total += p["qty"] * p["last"] * (1 - B.NDAX_FEE)
    steps.append("confirm every balance except CAD is zero; then disable the API key on the NDAX website")
    return {"dry_run": True, "steps": steps, "cad_after_about": round(total, 2)}


def stops_plan(j) -> list[dict]:
    s = _state(j)
    return [{"coin": c, "qty": p["qty"], "stop": p.get("stop_on_ndax"), "sleeve": p["sleeve"]}
            for c, p in sorted((s.get("pos") or {}).items()) if p["sleeve"] != "CORE"]
