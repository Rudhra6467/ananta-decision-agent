"""Setup checklist: for each Explorer setup, which conditions are met right now and which are missing.

Read-only. Mirrors CoinEngine.setups() condition by condition so Ask Ananta can say
"two of three conditions are met, the 15-minute turn is still missing". A parity test
(tests/test_setup_checklist.py) checks that "all conditions met" == "the engine fired the setup".
"""
from __future__ import annotations

from typing import Any

NAMES = {
    "E1": "Pullback in an uptrend",
    "E2": "Breakout after a quiet period",
    "E3": "Bounce at support",
    "E4": "Momentum continuation",
    "E5": "Squeeze breakout",
    "E6": "Deep dip (15m RSI under 30)",
    "E7": "Dip in a 4h downtrend",
    "E8": "Dip below the daily trend",
}
TRADED = ("E1", "E2", "E3", "E4", "E5")   # E6-E8 are watched only (Rulebook v0: dip setups off)


def _c(text: str, met: bool, value: Any = None) -> dict:
    v = round(value, 4) if isinstance(value, float) else value
    return {"text": text, "met": bool(met), "value": v}


def checklist(eng, st: dict) -> list[dict]:
    m15 = eng.tf["15m"]
    last4 = list(m15.bars)[-4:]
    low4 = min(b[3] for b in last4)
    z = st["zones"]
    touched_ema = low4 <= st["ema20_1h"]
    touched_sup = z["support"] is not None and low4 <= z["support"] + z["w"]
    rsi1h, rsi15 = st["rsi1h"], st["rsi15"]
    out = []

    out.append(("E1", [
        _c("1h trend is up (price above a rising 50-hour average)", st["S1"] == "BULL", st["S1"]),
        _c("Price pulled back to the 20-hour average or a support level in the last hour", touched_ema or touched_sup),
        _c("1h RSI between 35 and 55 (cooled off, not broken)", 35 <= rsi1h <= 55, rsi1h),
        _c("15m price turned back up through its 20-bar average", bool(st["S3"]), st["S3"]),
    ]))

    h1 = eng.tf["1h"]
    broke = []
    if len(h1.bars) >= 2:
        c1, pc1 = h1.bars[-1][4], h1.bars[-2][4]
        broke = [x for x in z["res_levels"] if pc1 <= x + z["w"] < c1]
    out.append(("E2", [
        _c("A 1h candle just closed (checked once an hour)", st["h1_closed_now"]),
        _c("Volume at least 1.5x normal", st["vol1h"] is not None and st["vol1h"] >= 1.5, st["vol1h"]),
        _c("Market was quiet (contracted) in the last 12 hours", st["contracted_12h"]),
        _c("The 1h close broke above a resistance level", bool(broke)),
    ]))

    in_sup = z["in_support"] or touched_sup
    out.append(("E3", [
        _c("Price is at a support level", in_sup),
        _c("15m RSI dipped under 35 in the last 3 bars", st["rsi15_min3"] < 35, st["rsi15_min3"]),
        _c("15m RSI is turning up", st["rsi15_prev"] is not None and rsi15 > st["rsi15_prev"], rsi15),
        _c("15m price turned back up through its 20-bar average", bool(st["S3"]), st["S3"]),
    ]))

    prev15 = m15.bars[-2]
    e20_prev = m15.ema_ago("20", 1)
    out.append(("E4", [
        _c("1h trend is up", st["S1"] == "BULL", st["S1"]),
        _c("Short-term direction is up (above a rising 20-hour average)", st["S2"] == "UP", st["S2"]),
        _c("Strong momentum (in the top 30% of the last ~50 hours)", st["roc_pct"] is not None and st["roc_pct"] >= 0.70, st["roc_pct"]),
        _c("1h RSI between 55 and 70 (strong, not overheated)", 55 <= rsi1h <= 70, rsi1h),
        _c("Previous 15m candle dipped to its 20-bar average and price is back above", prev15[3] <= e20_prev and st["c15"] > st["ema20_15"]),
    ]))

    out.append(("E5", [
        _c("A 1h candle just closed (checked once an hour)", st["h1_closed_now"]),
        _c("Market was squeezed (contracted) on the previous hour", st["contracted_prev"]),
        _c("1h close above the upper Bollinger band", st["bb_upper_1h"] is not None and st["c1h"] > st["bb_upper_1h"]),
        _c("Short-term direction is not down", st["S2"] != "DOWN", st["S2"]),
    ]))

    out.append(("E6", [_c("15m RSI under 30", rsi15 < 30, rsi15)]))
    out.append(("E7", [_c("1h RSI under 40", rsi1h < 40, rsi1h),
                       _c("4h trend is down", st["trend_4h"] == "DOWN", st["trend_4h"])]))
    out.append(("E8", [_c("Daily close below its 50-day average", not st["daily_above_ema50"]),
                       _c("Weak momentum (bottom 30%)", st["roc_pct"] is not None and st["roc_pct"] <= 0.30, st["roc_pct"])]))

    rows = []
    for sid, conds in out:
        met = sum(c["met"] for c in conds)
        rows.append({"setup": sid, "name": NAMES[sid], "traded": sid in TRADED, "met": met, "of": len(conds),
                     "complete": met == len(conds), "missing": [c["text"] for c in conds if not c["met"]], "conditions": conds})
    return rows


def describe_state(st: dict) -> dict:
    """The market picture in plain words (the same numbers the setups use)."""
    s1 = {"BULL": "uptrend", "BEAR": "downtrend", "NEUTRAL": "no clear trend"}[st["S1"]]
    return {
        "trend_1h": s1, "direction_short": {"UP": "rising", "DOWN": "falling", "FLAT": "flat"}[st["S2"]],
        "trend_4h": st["trend_4h"].lower(), "daily_above_50d_average": bool(st["daily_above_ema50"]),
        "rsi_1h": round(st["rsi1h"], 1), "rsi_15m": round(st["rsi15"], 1),
        "momentum_percentile": None if st["roc_pct"] is None else round(st["roc_pct"], 2),
        "quiet_now": bool(st["contracted_now"]), "volume_vs_normal_1h": None if st["vol1h"] is None else round(st["vol1h"], 2),
        "price": st["c15"], "near_support": bool(st["zones"]["in_support"]),
        "next_support": st["zones"]["support"], "next_resistance": st["zones"]["resistance"],
        "btc_trend_1h": {"BULL": "uptrend", "BEAR": "downtrend", "NEUTRAL": "no clear trend"}.get(st.get("btc_S1"), st.get("btc_S1")),
    }
