"""The decision chain (Madhav's framework, 2026-10-03): every coin walks the same ladder, fail-closed.

    REGIME -> STRUCTURAL TREND -> LOCATION -> TRIGGER -> INVALIDATION -> RISK -> EXPOSURE -> CANDIDATE

The first broken gate is the answer ("NO TRADE: stops at LOCATION ..."). Missing data is a gate failure, never "no setup".
Relative strength vs BTC, volume and the setup family are shown as evidence along the way; they are not gates until the repair
shop proves they help (docs/knowledge/hypotheses.json). Every threshold names its source: a verified Ananta variable (V01, V02),
a policy Madhav chose (P01, P02) or a teacher hypothesis (H11, H14).

Read-only: this explains how Ananta reasons. The paper Explorer still trades by its own rulebook.
"""
from __future__ import annotations

import statistics
from typing import Any

RISK_PCT = 0.01            # P01: risk 1% of the paper account per idea
MAX_STOP_PCT = 0.15        # P01: a stop farther than 15% cannot be sized sensibly
MAX_CORRELATED_LONGS = 5   # P02: at most 5 open longs that move with BTC
EXTENDED_PCT = 0.10        # H11: more than 10% above the 50-day average = stretched
NEAR_ATR = 1.0             # H11: 'at value' = within 1 daily ATR of the 20/50-day average or a support
STOP_BUFFER_ATR = 1.0      # H14: stop 1 daily ATR beyond the structure

GATES = [
    ("REGIME", "Is the market allowed to be long?"),
    ("TREND", "Is this coin in its own uptrend?"),
    ("LOCATION", "Is the price at a meaningful place?"),
    ("TRIGGER", "Did the expected signal happen?"),
    ("INVALIDATION", "Where is the idea proven wrong?"),
    ("RISK", "Can it be sized sensibly?"),
    ("EXPOSURE", "Does it add to bets we already hold?"),
]


def _g(key: str, ok: bool | None, why: str, source: str, values: dict | None = None) -> dict:
    status = "PASS" if ok is True else "FAIL" if ok is False else "UNKNOWN"
    return {"gate": key, "question": dict(GATES)[key], "status": status, "why": why, "source": source, "values": values or {}}


def _swing_lows(bars: list[tuple], k: int = 3) -> list[float]:
    out = []
    for i in range(k, len(bars) - k):
        if bars[i][3] == min(b[3] for b in bars[i - k:i + k + 1]):
            out.append(bars[i][3])
    return out


def _pct(a: float, b: float) -> float:
    return round(100 * (a / b - 1), 1) if b else 0.0


def evaluate(ex, coin: str, open_trades: list[dict], equity: float) -> dict:
    eng = ex.st["engines"][coin]
    btc = ex.st["engines"]["BTC"]
    d1, b1 = eng.tf["1d"], btc.tf["1d"]
    bars, bbars = list(d1.bars), list(b1.bars)
    last5 = eng.tf["5m"].last
    if len(bars) < 60 or len(bbars) < 60 or not last5 or not d1.atrh:
        return {"coin": coin, "verdict": "NO TRADE", "stops_at": "REGIME", "summary": "Not enough daily history yet (data gap).",
                "gates": [_g("REGIME", None, "not enough daily history", "data")], "observations": {}}
    price = last5[4]
    atr = d1.atrh[-1]
    atr_pct = atr / price
    gates: list[dict] = []

    # 1 REGIME (V02, verified): BTC daily close above its 50-day average
    bc, be50 = b1.last[4], b1.e50h[-1]
    gates.append(_g("REGIME", bc > be50, f"BTC {'above' if bc > be50 else 'below'} its 50-day average ({_pct(bc, be50):+.1f}%)",
                    "V02 verified (KEEP)", {"btc_close": round(bc, 2), "btc_50d": round(be50, 2)}))

    # 2 TREND (V01, verified): coin above its 20- and 50-day averages, 50-day not falling
    c, e20, e50 = bars[-1][4], d1.e20h[-1], d1.e50h[-1]
    e50_ago = d1.ema_ago("50", 5) or e50
    up = c > e20 and c > e50 and e50 >= e50_ago
    why = ("above its 20- and 50-day averages, 50-day rising" if up else
           f"{'below' if c < e50 else 'above'} its 50-day average ({_pct(c, e50):+.1f}%), {'below' if c < e20 else 'above'} its 20-day"
           + ("" if e50 >= e50_ago else ", 50-day falling"))
    gates.append(_g("TREND", up, why, "V01 verified (KEEP)", {"close": round(c, 4), "ema20": round(e20, 4), "ema50": round(e50, 4)}))

    # 3 LOCATION (H11): near an area of value or at the top of a base; not stretched
    lows = [x for x in _swing_lows(bars[-60:]) if x < price]
    support = max(lows) if lows else None
    hi20 = max(b[2] for b in bars[-21:-1])
    areas = {"20-day average": e20, "50-day average": e50}
    if support:
        areas["recent swing low"] = support
    near = [n for n, lvl in areas.items() if abs(price - lvl) <= NEAR_ATR * atr]
    at_base_top = price >= hi20 - 0.5 * atr
    stretched = price / e50 - 1 > EXTENDED_PCT
    ok = (bool(near) or at_base_top) and not stretched
    if stretched:
        why = f"stretched: {_pct(price, e50):+.1f}% above its 50-day average (more than {int(EXTENDED_PCT * 100)}%); wait for it to come back to value"
    elif near:
        why = f"at value: within 1 daily range of its {', '.join(near)}"
    elif at_base_top:
        why = "at the top of its 20-day range (breakout location)"
    else:
        why = "in the middle: not near its averages, a support, or the top of its range"
    gates.append(_g("LOCATION", ok, why, "H11 hypothesis (teachers: area of value, do not chase)",
                    {"vs_50d_pct": _pct(price, e50), "vs_20d_pct": _pct(price, e20), "daily_atr_pct": round(100 * atr_pct, 1),
                     "support": round(support, 4) if support else None, "high_20d": round(hi20, 4)}))

    # 4 TRIGGER: an Explorer setup complete at the last 15-minute scan, or a daily close above the previous day's high
    fired: list[str] = []
    try:
        if eng.last_scan is not None and eng.ready():
            st = eng.state(eng.last_scan)
            fired = [s for s, _, _ in eng.setups(st, all_=True)]
    except Exception:  # noqa: BLE001
        fired = []
    daily_strength = len(bars) >= 2 and bars[-1][4] > bars[-2][2]
    trig = fired or (["daily close above the previous day's high"] if daily_strength else [])
    gates.append(_g("TRIGGER", bool(trig), ("seen: " + ", ".join(trig)) if trig else "no trigger yet (no setup complete at the last check)",
                    "Explorer setups E1-E6 / daily strength", {"setups": fired}))

    # 5 INVALIDATION (H14): structure below price, 1 daily ATR buffer
    struct = max([x for x in (support, e50 if e50 < price else None) if x], default=None)
    stop = struct - STOP_BUFFER_ATR * atr if struct else None
    stop_pct = (price - stop) / price if stop else None
    gates.append(_g("INVALIDATION", stop is not None and stop > 0,
                    f"below {('the swing low' if struct == support else 'the 50-day average')} with a 1-ATR buffer: stop {stop:,.4g} ({100 * stop_pct:.1f}% away)"
                    if stop else "no structure below the price to put a stop under", "H14 hypothesis (stop 1 ATR beyond structure)",
                    {"stop": round(stop, 4) if stop else None, "stop_pct": round(100 * stop_pct, 1) if stop_pct else None}))

    # 6 RISK (P01): 1% of the account, size from the stop distance
    if stop_pct:
        risk_usd = RISK_PCT * equity
        size = risk_usd / stop_pct
        ok = stop_pct <= MAX_STOP_PCT
        gates.append(_g("RISK", ok, (f"risk ${risk_usd:,.0f} (1% of ${equity:,.0f}) / {100 * stop_pct:.1f}% stop = position ${size:,.0f}") if ok else
                        f"stop {100 * stop_pct:.1f}% away is too wide to size sensibly (limit {int(MAX_STOP_PCT * 100)}%)",
                        "P01 policy (risk 1% per idea)", {"risk_usd": round(risk_usd, 2), "position_usd": round(size, 2)}))
    else:
        gates.append(_g("RISK", None, "cannot size without a stop", "P01 policy"))

    # 7 EXPOSURE (P02): correlated longs share one budget
    rets = lambda bs: [bs[i][4] / bs[i - 1][4] - 1 for i in range(len(bs) - 30, len(bs))]
    corr = None
    if coin != "BTC" and len(bars) > 31 and len(bbars) > 31:
        try:
            corr = round(statistics.correlation(rets(bars), rets(bbars)), 2)
        except Exception:  # noqa: BLE001
            corr = None
    longs = [t for t in open_trades if t.get("coin")]
    same = [t for t in longs if t.get("coin") == coin]
    ok = len(longs) < MAX_CORRELATED_LONGS
    gates.append(_g("EXPOSURE", ok, (f"{len(longs)} open longs already move with BTC (limit {MAX_CORRELATED_LONGS})" if not ok else
                                     f"{len(longs)} open longs; this one {'adds to a coin we already hold' if same else 'is a new coin'}"
                                     + (f"; moves with BTC (correlation {corr})" if corr is not None else "")),
                    "P02 policy (correlated longs are one bet)", {"open_longs": len(longs), "same_coin": len(same), "btc_corr_30d": corr}))

    # observations (evidence, not gates)
    rs = None
    if coin != "BTC" and len(bars) > 31 and len(bbars) > 31:
        ratio_now, ratio_30 = price / b1.last[4], bars[-31][4] / bbars[-31][4]
        ch = ratio_now / ratio_30 - 1
        rs = {"vs_btc_30d_pct": round(100 * ch, 1), "state": "rising" if ch > 0.03 else "falling" if ch < -0.03 else "flat",
              "source": "H08 hypothesis (not a gate)"}
    vr = d1.vol_ratio()
    up_day = bars[-1][4] >= bars[-1][1]
    vol = {"state": "unavailable" if vr is None else "present" if vr >= 1.5 and up_day else "conflicting" if vr >= 1.5 else "absent",
           "last_day_vs_20d": round(vr, 2) if vr else None, "source": "H09 hypothesis (not a gate)"}
    atr_mean = sum(d1.atrh) / len(d1.atrh)
    family = ("compression" if atr < 0.8 * atr_mean else "breakout" if at_base_top else
              "pullback" if near and up else "false_break" if len(bars) > 2 and bars[-1][3] < (support or 0) < bars[-1][4] else "none")

    first_fail = next((g for g in gates if g["status"] != "PASS"), None)
    reached = True
    for g in gates:
        g["reached"] = reached
        if g is first_fail:
            reached = False
    verdict = "CANDIDATE" if first_fail is None else "NO TRADE"
    summary = (f"{coin}: candidate. Every gate passed; risk ${gates[5]['values'].get('risk_usd', 0):,.0f}, stop {gates[4]['values'].get('stop_pct')}% away."
               if first_fail is None else f"{coin} stops at {first_fail['gate']}: {first_fail['why']}.")
    return {"coin": coin, "price": round(price, 6), "verdict": verdict, "stops_at": first_fail["gate"] if first_fail else None,
            "summary": summary, "gates": gates,
            "observations": {"relative_strength": rs, "volume": vol, "setup_family": family, "daily_atr_pct": round(100 * atr_pct, 1)}}


def board(j) -> dict[str, Any]:
    ex = j._explorer()
    if not ex:
        return {"error": "the Explorer is not running", "coins": []}
    s = ex.status()
    open_trades = [{"coin": t["coin"], "setup": t.get("setup")} for t in s.get("open", [])]
    out = []
    for coin in ex.st["engines"]:
        try:
            out.append(evaluate(ex, coin, open_trades, float(s.get("equity") or 2000)))
        except Exception as exc:  # noqa: BLE001
            out.append({"coin": coin, "verdict": "NO TRADE", "stops_at": "REGIME", "summary": f"{coin}: could not evaluate ({str(exc)[:80]}).",
                        "gates": [], "observations": {}})
    try:                                                   # Madhav's three reads ride along as evidence (never a gate)
        from jarvis.service import reads_watch

        rb = {r["coin"]: r for r in reads_watch.board(j).get("coins", [])}
        for r in out:
            rr = rb.get(r["coin"])
            if rr:
                r.setdefault("observations", {})["your_setups"] = [
                    {k: x.get(k) for k in ("variant", "name", "state", "met", "of", "history")} for x in rr["reads"] if x["state"] in ("FIRED", "CLOSE")]
    except Exception:  # noqa: BLE001  evidence is optional
        pass
    try:                                                   # where price sits among zones, and how much attention it deserves (evidence)
        from jarvis.service import zones_watch

        zb = {r["coin"]: r for r in zones_watch.board(j).get("coins", [])}
        for r in out:
            z = zb.get(r["coin"])
            if z:
                f = (z["inside"] or [None])[0] or z.get("tested")
                r.setdefault("observations", {})["zone"] = {
                    "where": ("inside " if z["inside"] else "testing ") + "+".join(f["kinds"]).lower() if f else "between zones",
                    "history": f.get("history") if f else None, "attention": z["attention"]["level"],
                    "next_support_pct": (z.get("next_support") or {}).get("distance_pct"),
                    "next_resistance_pct": (z.get("next_resistance") or {}).get("distance_pct")}
    except Exception:  # noqa: BLE001
        pass
    counts: dict[str, int] = {}
    for r in out:
        k = r["stops_at"] or "CANDIDATE"
        counts[k] = counts.get(k, 0) + 1
    return {"framework": "Regime -> Trend -> Location -> Trigger -> Invalidation -> Risk -> Exposure (first broken gate = no trade)",
            "gates": [{"gate": k, "question": q} for k, q in GATES], "stops": counts, "coins": out,
            "note": "Read-only reasoning view. Thresholds: V = verified Ananta variable, P = Madhav's policy, H = teacher hypothesis (untested)."}
