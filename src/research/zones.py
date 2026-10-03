"""Zones: price bands where the market reacted before or where traders watch (docs/research/ZONES_PROGRAM.md).

One engine for history and live:
  * zone_map(S, i, swing=None)   the zones in force on day i, built only from daily bars before day i
  * history: `python -m src.research.zones review6 --db .../lab5_5m.sqlite`  (review #6: do zones hold, does strength matter?)
  * live:    `live_zones(D)` for the Jarvis service (zones around the last close with their state)

Kinds: SWING (clustered daily swing points of the last 3 years, with touches / held / flips), EXTREME (52-week low or high),
AVERAGE (50- and 200-day averages as bands), BASE (floor / top of a quiet base). Overlapping zones merge into one zone that
keeps every kind (confluence). Strength of a SWING zone: NEW (no held touch), TESTED (1), STRONG (2 or more).
Engineering note: the SWING part of the map is rebuilt every 5 days (it is still built only from earlier bars, so this is
stricter point-in-time, never looser); EXTREME, AVERAGE and BASE are rebuilt every day.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from src.research import reads as R

DAY = 86400
SWING_K = 5
CLUSTER_PCT = 0.03
HOLD_ATR = 1.5           # rose this many daily ATR above the band = held
BREAK_ATR = 0.5          # closed this many ATR beyond the band = broken
OUTCOME_DAYS = 20
REFRESH = 5


class Arr:
    """Numpy views of a reads.Series (fast scans)."""

    def __init__(self, S: R.Series):
        self.S = S
        self.h, self.l, self.c, self.o = (np.array(x, dtype=float) for x in (S.h, S.l, S.c, S.o))
        self.atr = np.array([np.nan if a is None else a for a in S.atr], dtype=float)
        self.sma50 = R.sma(S.c, 50)


def _first(mask: np.ndarray) -> int | None:
    k = int(np.argmax(mask)) if mask.size else 0
    return k if mask.size and mask[k] else None


def touch_outcome(A: Arr, start: int, bot: float, top: float, atr: float, end: int, side: str = "support") -> str:
    """After price entered [bot, top] on day `start`: HELD, BROKEN or OPEN, judged on days up to `end` (exclusive)."""
    if side == "support":
        brk = A.c[start:end] < bot - BREAK_ATR * atr
        held = A.h[start + 1:end] >= top + HOLD_ATR * atr
    else:
        brk = A.c[start:end] > top + BREAK_ATR * atr
        held = A.l[start + 1:end] <= bot - HOLD_ATR * atr
    b = _first(brk)
    hd = _first(held)
    hd = None if hd is None else hd + 1
    if b is None and hd is None:
        return "OPEN"
    if hd is None or (b is not None and b <= hd):
        return "BROKEN"
    return "HELD"


def swing_zones(A: Arr, i: int) -> list[dict]:
    """SWING zones from confirmed daily swing points of the 3 years before day i (bars 0..i-1 only)."""
    lo = max(0, i - 3 * 365)
    hi = i - 1                                    # last usable bar
    piv = []
    for p in range(lo + SWING_K, hi - SWING_K + 1):
        w_l = A.l[p - SWING_K:p + SWING_K + 1]
        w_h = A.h[p - SWING_K:p + SWING_K + 1]
        if A.l[p] == w_l.min():
            piv.append((A.l[p], p, "LOW"))
        if A.h[p] == w_h.max():
            piv.append((A.h[p], p, "HIGH"))
    if not piv:
        return []
    piv.sort()
    clusters: list[list] = [[piv[0]]]
    for x in piv[1:]:
        if x[0] <= clusters[-1][0][0] * (1 + CLUSTER_PCT):
            clusters[-1].append(x)
        else:
            clusters.append([x])
    atr = A.atr[i - 1]
    out = []
    for c in clusters:
        bot, top = min(x[0] for x in c), max(x[0] for x in c)
        if top - bot < 0.5 * atr:
            mid = (top + bot) / 2
            bot, top = mid - 0.25 * atr, mid + 0.25 * atr
        first = min(x[1] for x in c)
        # touches as support: separate visits (a gap of more than 3 days starts a new one) after the first member
        inside = (A.l[first + 1:hi + 1] <= top) & (A.h[first + 1:hi + 1] >= bot)
        days = np.nonzero(inside)[0] + first + 1
        visits = []
        for d in days:
            if not visits or d - visits[-1][-1] > 3:
                visits.append([d])
            else:
                visits[-1].append(d)
        held = 0
        for v in visits:
            a = A.atr[v[0] - 1] if v[0] > 0 and not np.isnan(A.atr[v[0] - 1]) else atr
            if A.c[v[0] - 1] > top and touch_outcome(A, v[0], bot, top, a, hi + 1) == "HELD":
                held += 1
        kinds = {x[2] for x in c}
        last_high = max((x[1] for x in c if x[2] == "HIGH"), default=-1)
        last_low = max((x[1] for x in c if x[2] == "LOW"), default=-1)
        flips = int("HIGH" in kinds and "LOW" in kinds and min(x[1] for x in c if x[2] == "HIGH") < last_low)
        out.append({"bot": float(bot), "top": float(top), "kinds": {"SWING"}, "touches": len(visits), "held": held, "flips": flips,
                    "highs": sum(1 for x in c if x[2] == "HIGH"),
                    "members": len(c), "first": first, "last_touch": int(visits[-1][-1]) if visits else max(last_high, last_low),
                    "tier": "STRONG" if held >= 2 else "TESTED" if held == 1 else "NEW"})
    return out


def daily_zones(A: Arr, i: int) -> list[dict]:
    """EXTREME, AVERAGE and BASE zones as of the close before day i."""
    S, j = A.S, i - 1
    atr = A.atr[j]
    out = []
    if j >= 364:
        lo52 = float(A.l[j - 364:j + 1].min())
        hi52 = float(A.h[j - 364:j + 1].max())
        out.append({"bot": lo52 - 0.5 * atr, "top": lo52 + 0.5 * atr, "kinds": {"EXTREME"}, "label": "52-week low"})
        out.append({"bot": hi52 - 0.5 * atr, "top": hi52 + 0.5 * atr, "kinds": {"EXTREME"}, "label": "52-week high"})
    for n, arr in (("50", A.sma50), ("200", S.sma200)):
        v = arr[j]
        if v is not None:
            out.append({"bot": v - 0.5 * atr, "top": v + 0.5 * atr, "kinds": {f"AVERAGE-{n}"}, "label": f"{n}-day average"})
    n = R._base(S, j)
    if n:
        s = j - n + 1
        floor, top = float(A.l[s:j + 1].min()), float(A.h[s:j + 1].max())
        out.append({"bot": floor - 0.25 * atr, "top": floor + 0.25 * atr, "kinds": {"BASE"}, "label": f"base floor ({n} days)"})
        out.append({"bot": top - 0.25 * atr, "top": top + 0.25 * atr, "kinds": {"BASE"}, "label": f"base top ({n} days)"})
    return out


def merge(zones: list[dict]) -> list[dict]:
    """Overlapping zones merge into one band that keeps every kind (confluence) and the best SWING tier."""
    rank = {"NEW": 0, "TESTED": 1, "STRONG": 2}
    zs = sorted(zones, key=lambda z: z["bot"])
    out: list[dict] = []
    for z in zs:
        if out and z["bot"] <= out[-1]["top"]:
            m = out[-1]
            m["top"] = max(m["top"], z["top"])
            m["kinds"] = m["kinds"] | z["kinds"]
            if "tier" in z and ("tier" not in m or rank[z["tier"]] > rank[m["tier"]]):
                for k in ("tier", "touches", "held", "flips", "members", "first", "last_touch", "highs"):
                    m[k] = z.get(k)
            m.setdefault("labels", []).extend([z.get("label")] if z.get("label") else [])
        else:
            out.append({**z, "kinds": set(z["kinds"]), "labels": [z["label"]] if z.get("label") else []})
    return out


def zone_map(A: Arr, i: int, swing: list[dict] | None = None) -> list[dict]:
    if swing is None:
        swing = swing_zones(A, i)
    return merge([dict(z) for z in swing] + daily_zones(A, i))


def groups(z: dict) -> list[str]:
    g = []
    if "SWING" in z["kinds"]:
        g.append(f"SWING-{z.get('tier', 'NEW')}")
    g += [k for k in ("EXTREME", "AVERAGE-50", "AVERAGE-200", "BASE") if k in z["kinds"]]
    if len(z["kinds"]) >= 2:
        g.append("CONFLUENCE")
    return g


# ---------------------------------------------------------------------------
# review #6
# ---------------------------------------------------------------------------
def events_for(coin: str, S: R.Series, cost: float, rnd: random.Random, until: int) -> list[dict]:
    """Every approach from above into a support zone, and the same for RANDOM bands (Amendment 1: the baseline uses the
    identical event rule on bands of the same widths at random prices, refreshed with the zone map)."""
    A = Arr(S)
    out, last_by_group = [], {}
    swing, swing_at, rand_bands = None, -999, []
    n = len(S.t)
    for i in range(400, n - 1):
        if S.t[i] >= until or np.isnan(A.atr[i - 1]) or S.sma200[i - 1] is None:
            continue
        prev_c = A.c[i - 1]
        zm = None
        if i - swing_at >= REFRESH:
            swing, swing_at = swing_zones(A, i), i
            zm = zone_map(A, i, swing)
            widths = [z["top"] - z["bot"] for z in zm] or [A.atr[i - 1]]
            rand_bands = []
            for _ in range(30):
                mid = prev_c * math.exp(rnd.uniform(-0.35, 0.35))
                w = rnd.choice(widths)
                rand_bands.append({"bot": mid - w / 2, "top": mid + w / 2, "kinds": {"RANDOM"}})
        if zm is None:
            zm = zone_map(A, i, swing)
        for z in zm + rand_bands:
            bot, top = z["bot"], z["top"]
            if not (top < prev_c and A.l[i] <= top and A.l[i - 1] > top and (A.c[i - 3:i] > top).all()):
                continue
            atr = float(A.atr[i - 1])
            res = touch_outcome(A, i, bot, top, atr, min(n, i + OUTCOME_DAYS))
            r10 = float((A.o[i + 11] / A.o[i + 1]) * (1 - cost) ** 2 - 1) if i + 11 < n else None
            for g in (["RANDOM"] if "RANDOM" in z["kinds"] else groups(z)):
                if g in last_by_group and S.t[i] - last_by_group[g] <= 5 * DAY:
                    continue
                last_by_group[g] = S.t[i]
                out.append({"coin": coin, "t": S.t[i], "group": g, "result": res, "r10": r10, "touches": z.get("touches"),
                            "w_atr": round((top - bot) / atr, 3), "held_before": z.get("held"), "kinds": sorted(z["kinds"])})
    return out


def _rate(xs: list[str]) -> float | None:
    hb = [x for x in xs if x in ("HELD", "BROKEN")]
    return sum(1 for x in hb if x == "HELD") / len(hb) if hb else None


WIDTH_BINS = (0.75, 1.5, 3.0)          # band width in daily ATR: the baseline is matched on width (Amendment 1)


def wbin(w: float) -> int:
    return sum(1 for b in WIDTH_BINS if w >= b)


def baseline(evs: list[dict]) -> dict:
    """RANDOM bands' held rate per width bin."""
    return {b: _rate([e["result"] for e in evs if wbin(e["w_atr"]) == b]) for b in range(len(WIDTH_BINS) + 1)}


def summarize(evs: list[dict], base: dict | None = None) -> dict:
    """Held rate of a group's events vs RANDOM bands of the same width (in ATR) in the same split. `base` maps width bin ->
    random held rate. Market events = episodes of different coins within 3 days; z is over market events
    (each one's mean of held minus its width-matched random rate)."""
    if not evs:
        return {"episodes": 0, "market_events": 0}
    evs = sorted(evs, key=lambda e: e["t"])
    mk: list[list[dict]] = []
    for e in evs:
        if mk and e["t"] - mk[-1][0]["t"] <= 3 * DAY:
            mk[-1].append(e)
        else:
            mk.append([e])
    rate = _rate([e["result"] for e in evs])
    diffs, bases = [], []
    if base:
        for m in mk:
            ok = [e for e in m if e["result"] in ("HELD", "BROKEN") and base.get(wbin(e["w_atr"])) is not None]
            bases += [base[wbin(e["w_atr"])] for e in ok]
            if ok:
                diffs.append(statistics.mean((1.0 if e["result"] == "HELD" else 0.0) - base[wbin(e["w_atr"])] for e in ok))
    n = len(diffs)
    md = statistics.mean(diffs) if diffs else None
    z = md / (statistics.stdev(diffs) / n ** 0.5) if n > 2 and statistics.stdev(diffs) > 0 else None
    r10 = [e["r10"] for e in evs if e["r10"] is not None]
    return {"episodes": len(evs), "market_events": len(mk), "held": sum(e["result"] == "HELD" for e in evs),
            "broken": sum(e["result"] == "BROKEN" for e in evs), "open": sum(e["result"] == "OPEN" for e in evs),
            "held_rate": None if rate is None else round(rate, 3),
            "random_held_rate": round(statistics.mean(bases), 3) if bases else None,
            "edge_pts": None if md is None else round(100 * md, 1), "z": None if z is None else round(z, 2),
            "net10_pct": round(100 * statistics.mean(r10), 2) if r10 else None,
            "median_width_atr": round(statistics.median(e["w_atr"] for e in evs), 2)}


GROUPS = ["SWING-NEW", "SWING-TESTED", "SWING-STRONG", "EXTREME", "AVERAGE-50", "AVERAGE-200", "CONFLUENCE", "BASE"]


def rw_bias() -> dict:
    """Amendment 2: each group's edge on synthetic random walks (frozen before the real run)."""
    p = Path(__file__).resolve().parents[2] / "docs" / "research" / "zones_rw_calibration.json"
    return {g: v.get("edge_pts") or 0.0 for g, v in json.loads(p.read_text())["groups"].items()} if p.exists() else {}


def corrected(d: dict, bias: float) -> dict:
    if d.get("edge_pts") is None:
        return {**d, "edge_corrected_pts": None, "z_corrected": None}
    e = d["edge_pts"] - bias
    se = abs(d["edge_pts"] / d["z"]) if d.get("z") else None
    return {**d, "rw_bias_pts": bias, "edge_corrected_pts": round(e, 1), "z_corrected": round(e / se, 2) if se else None}


def review6(D: dict[str, list[tuple]], seed: int = 6) -> dict:
    rnd = random.Random(seed)
    bias = rw_bias()
    evs = []
    for c, bars in D.items():
        S = R.Series(bars)
        evs += events_for(c, S, R.cost(c), rnd, R.CONF_END)
        print(c, len(evs), file=sys.stderr)
    out = {}
    split = {"DISCOVERY": lambda t: t < R.DISC_END, "CONFIRM": lambda t: R.DISC_END <= t < R.CONF_END}
    rnd_ev = {k: [e for e in evs if e["group"] == "RANDOM" and f(e["t"])] for k, f in split.items()}
    base = {k: baseline(v) for k, v in rnd_ev.items()}
    out["RANDOM"] = {**{k: {**summarize(v), "by_width": base[k]} for k, v in rnd_ev.items()}, "status": "BASELINE"}
    for g in GROUPS:
        b = bias.get(g, 0.0)
        d = corrected(summarize([e for e in evs if e["group"] == g and split["DISCOVERY"](e["t"])], base["DISCOVERY"]), b)
        cf = corrected(summarize([e for e in evs if e["group"] == g and split["CONFIRM"](e["t"])], base["CONFIRM"]), b)
        ok_d = (d.get("edge_corrected_pts") is not None and d["edge_corrected_pts"] >= 8 and (d.get("z_corrected") or 0) >= 2.5
                and d.get("market_events", 0) >= 30)
        ok_c = cf.get("edge_corrected_pts") is not None and cf["edge_corrected_pts"] > 0
        status = "PASS" if ok_d and ok_c else "NOT_CONFIRMED" if ok_d else "FAIL"
        out[g] = {"DISCOVERY": d, "CONFIRM": cf, "status": status}
    sd, nd = out["SWING-STRONG"]["DISCOVERY"].get("held_rate"), out["SWING-NEW"]["DISCOVERY"].get("held_rate")
    out["_strength_matters"] = bool(sd is not None and nd is not None and sd > nd)
    return {"groups": out, "events": [{k: v for k, v in e.items() if k != "rand"} for e in evs]}


# ---------------------------------------------------------------------------
# review #7: the lookout (which reactions inside a support zone make HELD more likely)
# ---------------------------------------------------------------------------
REACTIONS = {"F1": "Rejection (long lower wick)", "F2": "Closed back above the zone", "F3": "Volume 1.5x its 20-day average",
             "F4": "Momentum divergence (lower close, higher RSI than 10 days ago)", "F5": "Stronger than BTC (30 days)",
             "F6": "Market allowed (BTC above its 50-day average)", "F7": "Good zone kind (200-day, confluence or new swing)"}
GOOD_GROUPS = {"AVERAGE-200", "CONFLUENCE", "SWING-NEW"}


def reactions(S: R.Series, A: Arr, B: R.Series | None, i: int, z: dict) -> dict:
    """The seven reactions at the close of day i (bars 0..i only)."""
    h, l, c = A.h[i], A.l[i], A.c[i]
    vol20 = statistics.mean(S.v[i - 20:i]) if i >= 20 else None
    out = {"F1": bool(h > l and (c - l) / (h - l) >= 0.5), "F2": bool(c > z["top"]),
           "F3": bool(vol20 and S.v[i] >= 1.5 * vol20),
           "F4": bool(i >= 10 and S.rsi[i] is not None and S.rsi[i - 10] is not None and c < A.c[i - 10] and S.rsi[i] > S.rsi[i - 10])}
    bi = B.at(S.t[i]) if B is not None else None
    if bi is not None and bi >= 30 and i >= 30:
        out["F5"] = bool(S.c[i] / S.c[i - 30] > B.c[bi] / B.c[bi - 30])
        out["F6"] = bool(B.ema50[bi] is not None and B.c[bi] > B.ema50[bi])
    else:
        out["F5"] = out["F6"] = False
    out["F7"] = bool(set(groups(z)) & GOOD_GROUPS)
    return out


def lookout_events(coin: str, S: R.Series, B: R.Series, until: int) -> list[dict]:
    A = Arr(S)
    out, last, swing, swing_at = [], None, None, -999
    n = len(S.t)
    for i in range(400, n - 1):
        if S.t[i] >= until or np.isnan(A.atr[i - 1]) or S.sma200[i - 1] is None:
            continue
        if last is not None and S.t[i] - last <= 5 * DAY:
            continue
        if i - swing_at >= REFRESH:
            swing, swing_at = swing_zones(A, i), i
        prev_c = A.c[i - 1]
        hits = [z for z in zone_map(A, i, swing)
                if z["top"] < prev_c and A.l[i] <= z["top"] and A.l[i - 1] > z["top"] and (A.c[i - 3:i] > z["top"]).all()]
        if not hits:
            continue
        zm_all = zone_map(A, i, swing)
        z = max(hits, key=lambda x: (len(x["kinds"]), x["top"]))
        atr = float(A.atr[i - 1])
        res = touch_outcome(A, i, z["bot"], z["top"], atr, min(n, i + OUTCOME_DAYS))
        r10 = float((A.o[i + 11] / A.o[i + 1]) * (1 - R.cost(coin)) ** 2 - 1) if i + 11 < n else None
        last = S.t[i]
        ups = [x["bot"] for x in zm_all if i + 1 < n and x["bot"] > A.o[i + 1]]
        out.append({"coin": coin, "t": S.t[i], "i": i, "bot": float(z["bot"]), "top": float(z["top"]), "atr": atr,
                    "next_up": float(min(ups)) if ups else None, "result": res, "r10": r10, "groups": groups(z), **reactions(S, A, B, i, z)})
    return out


def _market_events(evs: list[dict]) -> list[list[dict]]:
    mk: list[list[dict]] = []
    for e in sorted(evs, key=lambda e: e["t"]):
        if mk and e["t"] - mk[-1][0]["t"] <= 3 * DAY:
            mk[-1].append(e)
        else:
            mk.append([e])
    return mk


def reaction_effect(evs: list[dict], f: str, seed: int = 7, boots: int = 400) -> dict:
    """Held rate with the reaction minus without; z from a bootstrap over market events (crypto moves together)."""
    ok = [e for e in evs if e["result"] in ("HELD", "BROKEN")]
    mk = _market_events(ok)

    def diff(groups_: list[list[dict]]):
        w = [e for m in groups_ for e in m if e[f]]
        wo = [e for m in groups_ for e in m if not e[f]]
        if not w or not wo:
            return None
        return sum(e["result"] == "HELD" for e in w) / len(w) - sum(e["result"] == "HELD" for e in wo) / len(wo)
    d = diff(mk)
    rnd = random.Random(seed)
    bs = [x for x in (diff([mk[rnd.randrange(len(mk))] for _ in mk]) for _ in range(boots)) if x is not None] if mk else []
    sd = statistics.stdev(bs) if len(bs) > 2 else None
    w = [e for e in ok if e[f]]
    wo = [e for e in ok if not e[f]]
    r = lambda xs: round(100 * statistics.mean(xs), 2) if xs else None                  # noqa: E731
    return {"with": len(w), "without": len(wo), "market_events_with": len(_market_events(w)),
            "held_with": round(sum(e["result"] == "HELD" for e in w) / len(w), 3) if w else None,
            "held_without": round(sum(e["result"] == "HELD" for e in wo) / len(wo), 3) if wo else None,
            "diff_pts": None if d is None else round(100 * d, 1), "z": round(d / sd, 2) if d is not None and sd else None,
            "net10_with_pct": r([e["r10"] for e in w if e["r10"] is not None]), "net10_without_pct": r([e["r10"] for e in wo if e["r10"] is not None])}


def lookout_bias() -> dict:
    p = Path(__file__).resolve().parents[2] / "docs" / "research" / "lookout_rw_calibration.json"
    return {f: v.get("diff_pts") or 0.0 for f, v in json.loads(p.read_text())["reactions"].items()} if p.exists() else {}


def _corr(d: dict, bias: float) -> dict:
    if d.get("diff_pts") is None:
        return {**d, "diff_corrected_pts": None, "z_corrected": None}
    e = d["diff_pts"] - bias
    se = abs(d["diff_pts"] / d["z"]) if d.get("z") else None
    return {**d, "rw_bias_pts": bias, "diff_corrected_pts": round(e, 1), "z_corrected": round(e / se, 2) if se else None}


def review7(D: dict[str, list[tuple]]) -> dict:
    B = R.Series(D["BTC"])
    evs = []
    for c, bars in D.items():
        S = B if c == "BTC" else R.Series(bars)
        evs += lookout_events(c, S, B, R.CONF_END)
        print(c, len(evs), file=sys.stderr)
    split = {"DISCOVERY": [e for e in evs if e["t"] < R.DISC_END], "CONFIRM": [e for e in evs if R.DISC_END <= e["t"] < R.CONF_END]}
    out = {}
    bias = lookout_bias()
    for f in REACTIONS:
        d, cf = _corr(reaction_effect(split["DISCOVERY"], f), bias.get(f, 0.0)), _corr(reaction_effect(split["CONFIRM"], f), bias.get(f, 0.0))
        ok_d = (d["diff_corrected_pts"] is not None and d["diff_corrected_pts"] >= 8 and (d["z_corrected"] or 0) >= 2.5
                and d["market_events_with"] >= 30)
        ok_c = cf["diff_corrected_pts"] is not None and cf["diff_corrected_pts"] > 0
        out[f] = {"name": REACTIONS[f], "DISCOVERY": d, "CONFIRM": cf, "status": "PASS" if ok_d and ok_c else "NOT_CONFIRMED" if ok_d else "FAIL"}
    passing = [f for f in REACTIONS if out[f]["status"] in ("PASS", "NOT_CONFIRMED")]
    score = {}
    for k, evl in split.items():
        rows = {}
        for e in evl:
            if e["result"] not in ("HELD", "BROKEN"):
                continue
            sc = sum(e[f] for f in passing)
            rows.setdefault(sc, []).append(e["result"] == "HELD")
        score[k] = {str(sc): {"n": len(v), "held": round(sum(v) / len(v), 3)} for sc, v in sorted(rows.items())}
    base = {k: {"events": len(v), "held_rate": _rate([e["result"] for e in v])} for k, v in split.items()}
    return {"reactions": out, "score_uses": passing, "score": score, "base": base, "events": evs}


# ---------------------------------------------------------------------------
# review #10: stops and exits at zones (docs/research/REVIEW_10.md)
# ---------------------------------------------------------------------------
def exits(A: Arr, e: dict, cost: float) -> dict | None:
    """The four pre-registered exits for one entry (bought at the open after the zone entry day)."""
    n = len(A.c)
    k0 = e["i"] + 1
    if k0 + 40 >= n:
        return None
    px = float(A.o[k0])
    net = lambda x: (x / px) * (1 - cost) ** 2 - 1                         # noqa: E731
    out = {"X1": {"net": net(float(A.o[k0 + 20])), "days": 20, "stopped": False}}
    # X2 zone stop (close under bot - 0.5 ATR -> next open), target the next zone above, else 40 days
    stop_c = e["bot"] - 0.5 * e["atr"]
    res = None
    for k in range(k0, k0 + 40):
        if e["next_up"] is not None and A.h[k] >= e["next_up"]:
            res = {"net": net(max(e["next_up"], float(A.o[k]))), "days": k - k0 + 1, "stopped": False, "target": True}
            break
        if A.c[k] < stop_c:
            res = {"net": net(float(A.o[k + 1])), "days": k - k0 + 1, "stopped": True}
            break
    out["X2"] = res or {"net": net(float(A.o[k0 + 40])), "days": 40, "stopped": False}
    for name, stop in (("X3", px - 2 * e["atr"]), ("X4", px * 0.98)):
        r = None
        for k in range(k0, k0 + 20):
            if A.o[k] <= stop:
                r = {"net": net(float(A.o[k])), "days": k - k0 + 1, "stopped": True}
                break
            if A.l[k] <= stop:
                r = {"net": net(stop), "days": k - k0 + 1, "stopped": True}
                break
        out[name] = r or {"net": net(float(A.o[k0 + 20])), "days": 20, "stopped": False}
    return out


def _paired(rows: list[dict], a: str, b: str) -> dict:
    mk = _market_events(rows)
    d = [statistics.mean(r["x"][a]["net"] - r["x"][b]["net"] for r in m) for m in mk]
    if len(d) < 3:
        return {"diff_pct": None, "z": None, "market_events": len(d)}
    sd = statistics.stdev(d)
    return {"diff_pct": round(100 * statistics.mean(d), 2), "z": round(statistics.mean(d) / (sd / len(d) ** 0.5), 2) if sd > 0 else None,
            "market_events": len(d)}


def review10(D: dict[str, list[tuple]]) -> dict:
    B = R.Series(D["BTC"])
    rows = []
    for c, bars in D.items():
        S = B if c == "BTC" else R.Series(bars)
        A = Arr(S)
        for e in lookout_events(c, S, B, R.CONF_END):
            if not e["F6"]:
                continue
            x = exits(A, e, R.cost(c))
            if x:
                rows.append({"coin": c, "t": e["t"], "x": x})
        print(c, len(rows), file=sys.stderr)
    out = {}
    for sp, lo, hi in (("DISCOVERY", 0, R.DISC_END), ("CONFIRM", R.DISC_END, R.CONF_END)):
        rr = [r for r in rows if lo <= r["t"] < hi]
        o = {"trades": len(rr), "market_events": len(_market_events(rr))}
        for k in ("X1", "X2", "X3", "X4"):
            nets = [r["x"][k]["net"] for r in rr]
            o[k] = {"mean_net_pct": round(100 * statistics.mean(nets), 2) if nets else None,
                    "median_net_pct": round(100 * statistics.median(nets), 2) if nets else None,
                    "win": round(sum(x > 0 for x in nets) / len(nets), 3) if nets else None,
                    "worst_pct": round(100 * min(nets), 1) if nets else None,
                    "stopped": round(sum(r["x"][k]["stopped"] for r in rr) / len(rr), 3) if rr else None,
                    "avg_days": round(statistics.mean(r["x"][k]["days"] for r in rr), 1) if rr else None}
        o["X2_target_hit"] = round(sum(bool(r["x"]["X2"].get("target")) for r in rr) / len(rr), 3) if rr else None
        o["X2_vs"] = {k: _paired(rr, "X2", k) for k in ("X1", "X3", "X4")}
        out[sp] = o
    d, c = out["DISCOVERY"], out["CONFIRM"]
    ok_d = (d["X2"]["mean_net_pct"] or -1) > 0 and all((d["X2_vs"][k]["z"] or 0) >= 2 for k in ("X1", "X3", "X4"))
    ok_c = all(c["X2"]["mean_net_pct"] is not None and c[k]["mean_net_pct"] is not None and c["X2"]["mean_net_pct"] > c[k]["mean_net_pct"]
               for k in ("X1", "X3", "X4"))
    out["status"] = "PASS" if ok_d and ok_c else "NOT_CONFIRMED" if ok_d else "FAIL"
    return out


# ---------------------------------------------------------------------------
# review #11: teacher ideas redone with zones (docs/research/REVIEW_11.md)
# ---------------------------------------------------------------------------
def review11_events(coin: str, S: R.Series, B: R.Series, until: int) -> list[dict]:
    A = Arr(S)
    n = len(S.t)
    out, last = [], {}
    swing, swing_at = None, -999
    for i in range(400, n - 21):
        if S.t[i] >= until or np.isnan(A.atr[i - 1]):
            continue
        bi = B.at(S.t[i - 1])
        mkt = bool(bi is not None and B.ema50[bi] is not None and B.c[bi] > B.ema50[bi])
        if not mkt:
            continue
        if i - swing_at >= REFRESH:
            swing, swing_at = swing_zones(A, i), i
        zm = zone_map(A, i, swing)
        r20 = float((A.o[i + 21] / A.o[i + 1]) * (1 - R.cost(coin)) ** 2 - 1)
        vol20 = statistics.mean(S.v[i - 20:i])
        above200 = S.sma200[i - 1] is not None and A.c[i - 1] > S.sma200[i - 1]
        found = set()
        for z in zm:
            if ("AVERAGE-50" in z["kinds"] and above200 and z["top"] < A.c[i - 1] and A.l[i] <= z["top"] and A.l[i - 1] > z["top"]
                    and (A.c[i - 3:i] > z["top"]).all()):
                found.add("A1")
            if z["bot"] > A.c[i - 1] and A.c[i] > z["top"] and (A.c[i - 3:i] <= z["top"]).all():
                found.add("B1")
                if "SWING" in z["kinds"] and (z.get("highs") or 0) >= 2:
                    found.add("B2")
                if S.v[i] >= 1.5 * vol20:
                    found.add("B3")
        for v in found:
            if v in last and S.t[i] - last[v] <= 5 * DAY:
                continue
            last[v] = S.t[i]
            out.append({"coin": coin, "t": S.t[i], "variant": v, "r20": r20})
    return out


def _cond_drift(coin: str, S: R.Series, B: R.Series, A: Arr, lo: int, hi: int, need200: bool) -> float | None:
    xs = []
    for i in range(400, len(S.t) - 21):
        if not (lo <= S.t[i] < hi):
            continue
        bi = B.at(S.t[i - 1])
        if not (bi is not None and B.ema50[bi] is not None and B.c[bi] > B.ema50[bi]):
            continue
        if need200 and not (S.sma200[i - 1] is not None and A.c[i - 1] > S.sma200[i - 1]):
            continue
        xs.append(float((A.o[i + 21] / A.o[i + 1]) * (1 - R.cost(coin)) ** 2 - 1))
    return statistics.mean(xs) if xs else None


def review11(D: dict[str, list[tuple]]) -> dict:
    B = R.Series(D["BTC"])
    splits = {"DISCOVERY": (0, R.DISC_END), "CONFIRM": (R.DISC_END, R.CONF_END)}
    evs = []
    for c, bars in D.items():
        S = B if c == "BTC" else R.Series(bars)
        A = Arr(S)
        base = {(sp, f): _cond_drift(c, S, B, A, lo, hi, f) for sp, (lo, hi) in splits.items() for f in (True, False)}
        for e in review11_events(c, S, B, R.CONF_END):
            sp = "DISCOVERY" if e["t"] < R.DISC_END else "CONFIRM"
            b = base[(sp, e["variant"] == "A1")]
            if b is not None:
                evs.append({**e, "split": sp, "x20": e["r20"] - b})
        print(c, len(evs), file=sys.stderr)
    out = {}
    for v in ("A1", "B1", "B2", "B3"):
        res = {}
        for sp in splits:
            rr = [e for e in evs if e["variant"] == v and e["split"] == sp]
            mk = _market_events(rr)
            xs = [statistics.mean(x["x20"] for x in m) for m in mk]
            sd = statistics.stdev(xs) if len(xs) > 2 else None
            res[sp] = {"episodes": len(rr), "market_events": len(mk),
                       "mean_excess20_pct": round(100 * statistics.mean(xs), 2) if xs else None,
                       "z": round(statistics.mean(xs) / (sd / len(xs) ** 0.5), 2) if sd else None,
                       "mean_net20_pct": round(100 * statistics.mean(e["r20"] for e in rr), 2) if rr else None,
                       "win20": round(sum(e["r20"] > 0 for e in rr) / len(rr), 3) if rr else None}
        d, c = res["DISCOVERY"], res["CONFIRM"]
        ok_d = d["market_events"] >= 30 and (d["mean_excess20_pct"] or -1) > 0 and (d["z"] or 0) >= 2.5
        ok_c = (c["mean_excess20_pct"] or -1) > 0
        out[v] = {**res, "status": "PASS" if ok_d and ok_c else "NOT_CONFIRMED" if ok_d else "FAIL"}
    return out


# ---------------------------------------------------------------------------
# live
# ---------------------------------------------------------------------------
def live_zones(D: list[tuple], near_atr: float = 3.0) -> dict:
    """Zones around the last close: where price is, what is just below (support) and above (resistance), with states."""
    S = R.Series(D)
    A = Arr(S)
    n = len(D)
    zs = zone_map(A, n)                                   # built from every closed bar ('tomorrow's map')
    px, atr, lo, hi = float(D[-1][4]), float(A.atr[n - 1]), float(D[-1][3]), float(D[-1][2])
    rows = []
    for z in zs:
        bot, top = z["bot"], z["top"]
        dist = 0.0 if bot <= px <= top else (px - top) / atr if px > top else (px - bot) / atr
        # INSIDE = the close sits in the band (price is here now); TESTED = the day traded into it but closed outside
        state = ("INSIDE" if bot <= px <= top else "TESTED" if lo <= top and hi >= bot else "APPROACHING" if abs(dist) <= 2 else "FAR")
        # the last 20 days: did price visit this band, and how did that visit end so far?
        recent = None
        for k in range(max(1, n - OUTCOME_DAYS), n):
            if D[k][3] <= top and D[k][2] >= bot and D[k - 1][4] > top:
                recent = {"entered": datetime.fromtimestamp(D[k][0], timezone.utc).strftime("%Y-%m-%d"),
                          "so_far": touch_outcome(Arr(S), k, bot, top, float(A.atr[k - 1]), n)}
        if abs(dist) > near_atr and state == "FAR":
            continue
        rows.append({"bot": round(float(bot), 6), "top": round(float(top), 6), "side": "support" if top < px else "resistance" if bot > px else "here",
                     "distance_atr": round(float(dist), 2), "distance_pct": round(float(100 * ((top if px > top else bot) / px - 1)), 2) if state != "INSIDE" else 0.0,
                     "kinds": sorted(z["kinds"]), "labels": z.get("labels", []), "tier": z.get("tier"),
                     "held": None if z.get("held") is None else int(z["held"]), "touches": None if z.get("touches") is None else int(z["touches"]), "state": state, "recent": recent, "groups": groups(z)})
    rows.sort(key=lambda r: -r["top"])
    return {"price": px, "atr": round(atr, 6), "day": datetime.fromtimestamp(D[-1][0], timezone.utc).strftime("%Y-%m-%d"), "zones": rows,
            "in_zone": any(r["state"] == "INSIDE" for r in rows)}


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["review6", "review7", "review10", "review11"])
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", default="~/ananta_runs/zones")
    a = ap.parse_args(argv)
    out = Path(os.path.expanduser(a.out))
    out.mkdir(parents=True, exist_ok=True)
    cache = Path(os.path.expanduser("~/ananta_runs/reads"))
    D = {c: R.cached_daily(a.db, c, cache, R.CONF_END) for c in R.COINS}
    if a.mode == "review11":
        res = review11(D)
        res["_meta"] = {"run": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pre_registration": "docs/research/REVIEW_11.md"}
        (out / "review11_results.json").write_text(json.dumps(res, indent=1))
        print(json.dumps(res, indent=1))
        return
    if a.mode == "review10":
        res = review10(D)
        res["_meta"] = {"run": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pre_registration": "docs/research/REVIEW_10.md"}
        (out / "review10_results.json").write_text(json.dumps(res, indent=1))
        print(json.dumps(res, indent=1))
        return
    if a.mode == "review7":
        res = review7(D)
        res["_meta"] = {"run": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pre_registration": "docs/research/ZONES_PROGRAM.md#6"}
        (out / "review7_results.json").write_text(json.dumps(res, indent=1, default=list))
        print("base", res["base"])
        for f, v in res["reactions"].items():
            d, c = v["DISCOVERY"], v["CONFIRM"]
            print(f, f"{v['status']:13}", v["name"][:34].ljust(34), f"DISC with {d['with']}/{d['market_events_with']}ev held {d['held_with']} vs {d['held_without']} diff {d['diff_pts']}->{d['diff_corrected_pts']} z {d['z_corrected']} r10 {d['net10_with_pct']}/{d['net10_without_pct']}",
                  f"| CONF held {c['held_with']} vs {c['held_without']} diff {c['diff_pts']}->{c['diff_corrected_pts']} z {c['z_corrected']} r10 {c['net10_with_pct']}/{c['net10_without_pct']}")
        print("score uses", res["score_uses"], res["score"])
        return
    res = review6(D)
    res["_meta"] = {"run": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pre_registration": "docs/research/ZONES_PROGRAM.md"}
    (out / "review6_results.json").write_text(json.dumps(res, indent=1, default=list))
    for g, v in res["groups"].items():
        if g.startswith("_"):
            print(g, v)
            continue
        d, c = v["DISCOVERY"], v["CONFIRM"]
        print(f"{g:13} {v['status']:13} DISC ev {d.get('market_events', 0):4} held {d.get('held_rate')} rand {d.get('random_held_rate')} "
              f"edge {d.get('edge_pts')}->{d.get('edge_corrected_pts')} z {d.get('z_corrected')} r10 {d.get('net10_pct')}/{d.get('random_net10_pct')} | CONF ev {c.get('market_events', 0):4} "
              f"held {c.get('held_rate')} rand {c.get('random_held_rate')} edge {c.get('edge_pts')}->{c.get('edge_corrected_pts')} r10 {c.get('net10_pct')}/{c.get('random_net10_pct')}")


if __name__ == "__main__":
    main()
