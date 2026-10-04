"""Market-shift alerts (Madhav's OK, 2026-10-04): the one market rule that history backs, said out loud when it changes.

The market regime is Bitcoin against its 50-day average (V02; review #7: inside a support zone, 68% held with Bitcoin above it
against 50% below). It decides the trend portfolio (cash when Bitcoin is under), the M2a-G read and the zone-touch trade, and
it is the first thing the decision brain weighs. Two alerts:

  live(j, px, armed, push)   the eye's live price crosses the 50-day average (0.3% past it, so a price sitting on the line
                             does not ring every minute): "if the day closes here, the market turns risk-off / allowed".
                             At most one note per direction every 12 hours.
  close(j, push)             after a daily close, if the regime changed from the previous close: what flipped and what it
                             changes; with breadth (how many of our 10 coins are above their own 50-day average).

Both go into the feed (eye_events) and the phone. Paper only; nothing trades from here.
"""
from __future__ import annotations

from typing import Callable

BAND = 0.003
LIVE_COOLDOWN = 12 * 3600
WHAT = {"RISK_OFF": "the trend portfolio moves to cash at its next check, the zone-touch and market-gated setups pause, and Jarvis sizes down",
        "ALLOWED": "the trend portfolio can buy again at its next check, and the zone-touch and market-gated setups are back on"}


def _state(j, k: str) -> str | None:
    from jarvis.service import watch_engine

    watch_engine._table(j)
    r = j.db.execute("SELECT v FROM engine_state WHERE k=?", (k,)).fetchone()
    return r[0] if r else None


def _set(j, k: str, v: str) -> None:
    j.db.execute("INSERT OR REPLACE INTO engine_state VALUES (?,?)", (k, v))
    j.db.commit()


def live(j, px: dict, armed: dict, push: Callable | None = None) -> list[dict]:
    from jarvis.service import eye

    p, ema, reg = px.get("BTC"), armed.get("btc_ema50"), armed.get("regime")
    if not p or not ema or reg not in ("ALLOWED", "RISK_OFF"):
        return []
    now = float(j.now())
    if reg == "ALLOWED" and p < ema * (1 - BAND) and eye._cool_ok("shift:down", LIVE_COOLDOWN, now):
        return [eye._event(j, "MARKET_WARN", "BTC", p, "Bitcoin is under its 50-day average",
                           f"About ${p:,.0f} against the average near ${ema:,.0f}. If the day closes under it, the market turns risk-off: {WHAT['RISK_OFF']}.",
                           push, {"ema50": ema, "regime": reg})]
    if reg == "RISK_OFF" and p > ema * (1 + BAND) and eye._cool_ok("shift:up", LIVE_COOLDOWN, now):
        return [eye._event(j, "MARKET_WARN", "BTC", p, "Bitcoin is back above its 50-day average",
                           f"About ${p:,.0f} against the average near ${ema:,.0f}. If the day closes above it, the market turns allowed: {WHAT['ALLOWED']}.",
                           push, {"ema50": ema, "regime": reg})]
    return []


def breadth(j) -> tuple[int, int]:
    """How many of our coins closed above their own 50-day average on the last daily close."""
    from jarvis.service.reads_watch import _daily
    from src.research import reads as R

    up = n = 0
    for c in R.COINS:
        D = _daily(j, c)
        if len(D) < 60:
            continue
        S = R.Series(D)
        if S.ema50[-1] is not None:
            n += 1
            up += S.c[-1] > S.ema50[-1]
    return up, n


def close(j, push: Callable | None = None) -> dict | None:
    """Once per daily close: did the regime flip?"""
    from jarvis.service import eye, watch_engine
    from jarvis.service.reads_watch import _daily
    from src.research import reads as R

    btc = _daily(j, "BTC")
    if len(btc) < 60:
        return None
    B = R.Series(btc)
    last_t = str(btc[-1][0])
    if _state(j, "shift:last_close") == last_t:
        return None
    reg = watch_engine.regime_at(B, btc[-1][0])
    prev = _state(j, "shift:regime")
    _set(j, "shift:last_close", last_t)
    _set(j, "shift:regime", reg or "")
    if not prev or not reg or prev == reg:
        return {"regime": reg, "changed": False}
    up, n = breadth(j)
    eye._table(j)
    title = "Market turned risk-off: Bitcoin closed under its 50-day" if reg == "RISK_OFF" else "Market allowed again: Bitcoin closed above its 50-day"
    body = (f"Close ${B.c[-1]:,.0f}, average ${B.ema50[-1]:,.0f}. {up} of {n} coins closed above their own 50-day. "
            f"What changes: {WHAT[reg]}.")
    e = eye._event(j, "MARKET_SHIFT", "BTC", B.c[-1], title, body, push, {"from": prev, "to": reg, "breadth": [up, n]})
    if reg == "ALLOWED":                                   # a market opening up again is a moment worth a decision
        try:
            from jarvis.service import brain

            brain.wake(j, "BTC", "market_shift", {"from": prev, "to": reg})
        except Exception:  # noqa: BLE001
            pass
    return {"regime": reg, "changed": True, "event": e["id"]}
