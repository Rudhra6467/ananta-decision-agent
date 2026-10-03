"""Casebook: Madhav's own trades rebuilt from candles, next to what Ananta saw at the same moment.

    python -m src.research.casebook --db ~/code/ananta-decision-agent/ananta-quant-research-db/lab5_5m.sqlite \
        --fx ~/ananta_runs/casebook/usdcad.json --cases docs/casebook/cases.json \
        --live-bars ~/code/ananta-decision-agent/explorer_bars.sqlite --out ~/ananta_runs/casebook

For each case:
  1. pin   - find the 5-minute bar on his (Toronto) date where SOL traded at his CAD price (USD candles x Bank of Canada rate)
  2. read  - everything a human trader looks at, using only data BEFORE that moment: where the price sits in its year
             (52-week low/high), the support and resistance zones of the last 3 years and how often they held,
             how long and how deep the fall was, selling exhaustion (volume spike, then drying up), momentum divergence
             (a lower low in price with a higher RSI = the bear weakening), and BTC / ETH at the same moment
  3. ananta - the SAME Explorer engine the live system runs, replayed around the moment (rules v0 and wide mode W1):
             what it saw, what it would have bought, and how that ended
  4. after - what the price did next (1 day .. 90 days, the deepest drop after the buy, today)
News is not in the database, so "no strong bad news" cannot be checked here (noted as such).
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
import sqlite3
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from src.intelligence import explorer_engine as xe
from src.research.explorer_replay import event_stream, resample

TZ = ZoneInfo("America/Toronto")
DAY = 86400


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------
def load(db: str, coin: str, t0: int, t1: int) -> list[tuple]:
    con = sqlite3.connect(f"file:{os.path.expanduser(db)}?mode=ro", uri=True)
    try:
        return [tuple(r) for r in con.execute(
            "SELECT event_unix, open, high, low, close, volume FROM bars WHERE instrument=? AND event_unix>=? AND event_unix<? "
            "ORDER BY event_unix", (f"{coin}-USD-SPOT", t0, t1))]
    finally:
        con.close()


def live_daily(path: str | None, coin: str) -> list[tuple]:
    if not path or not os.path.exists(os.path.expanduser(path)):
        return []
    con = sqlite3.connect(f"file:{os.path.expanduser(path)}?mode=ro", uri=True)
    try:
        return [tuple(r) for r in con.execute("SELECT t, o, h, l, c, v FROM bars WHERE coin=? AND tf='1d' ORDER BY t", (coin,))]
    finally:
        con.close()


class FX:
    """USD -> CAD from Bank of Canada daily rates (latest published on or before the Toronto date)."""

    def __init__(self, path: str):
        d = json.loads(Path(os.path.expanduser(path)).read_text())
        self.m = {o["d"]: float(o["FXUSDCAD"]["v"]) for o in d["observations"]}
        self.days = sorted(self.m)

    def at(self, ts: float) -> float:
        day = datetime.fromtimestamp(ts, TZ).strftime("%Y-%m-%d")
        i = bisect.bisect_right(self.days, day) - 1
        return self.m[self.days[max(i, 0)]]


def local(ts: float, fmt: str = "%Y-%m-%d %H:%M") -> str:
    return datetime.fromtimestamp(ts, TZ).strftime(fmt)


def day_start(date: str) -> int:
    y, m, d = map(int, date.split("-"))
    return int(datetime(y, m, d, tzinfo=TZ).timestamp())


# ---------------------------------------------------------------------------
# indicators
# ---------------------------------------------------------------------------
def rsi_series(closes: list[float], n: int = 14) -> list[float | None]:
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= n:
        return out
    g = [max(closes[i] - closes[i - 1], 0) for i in range(1, len(closes))]
    l_ = [max(closes[i - 1] - closes[i], 0) for i in range(1, len(closes))]
    ag, al = sum(g[:n]) / n, sum(l_[:n]) / n
    out[n] = 100 - 100 / (1 + ag / al) if al > 0 else 100.0
    for i in range(n + 1, len(closes)):
        ag = (ag * (n - 1) + g[i - 1]) / n
        al = (al * (n - 1) + l_[i - 1]) / n
        out[i] = 100 - 100 / (1 + ag / al) if al > 0 else 100.0
    return out


def sma_series(x: list[float], n: int) -> list[float | None]:
    out: list[float | None] = [None] * len(x)
    s = 0.0
    for i, v in enumerate(x):
        s += v
        if i >= n:
            s -= x[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def pivots(bars: list[tuple], k: int) -> list[tuple[int, float, str]]:
    """Confirmed swing lows / highs: the lowest low (highest high) of k bars on each side."""
    out = []
    for i in range(k, len(bars) - k):
        w = bars[i - k:i + k + 1]
        if bars[i][3] == min(b[3] for b in w):
            out.append((i, bars[i][3], "LOW"))
        if bars[i][2] == max(b[2] for b in w):
            out.append((i, bars[i][2], "HIGH"))
    return out


def r2(x, d=2):
    return None if x is None else round(x, d)


def pct(a, b):
    return None if (a is None or b in (None, 0)) else round(100 * (a / b - 1), 1)


# ---------------------------------------------------------------------------
# 1. pin his buy to a moment
# ---------------------------------------------------------------------------
def pin(b5: list[tuple], fx: FX, date: str, price_cad: float) -> dict:
    s = day_start(date)
    e = int((datetime.fromtimestamp(s, TZ) + timedelta(days=1)).timestamp())
    day = [b for b in b5 if s <= b[0] < e]
    if not day:
        raise SystemExit(f"no candles on {date}")
    r = fx.at(s + 43200)
    hit = [b for b in day if b[3] * r <= price_cad <= b[2] * r]
    lo, hi = min(b[3] for b in day) * r, max(b[2] for b in day) * r
    if hit:
        b, gap = hit[0], 0.0
    else:
        b = min(day, key=lambda x: min(abs(x[3] * r - price_cad), abs(x[2] * r - price_cad)))
        edge = b[2] * r if price_cad > b[2] * r else b[3] * r
        gap = 100 * (price_cad / edge - 1)
    return {"t": b[0] + 300, "fx": r, "price_usd": price_cad / r, "matched": bool(hit), "gap_pct": round(gap, 2),
            "hours_at_price": round(len(hit) * 5 / 60, 1), "first_at_price": local(hit[0][0]) if hit else None,
            "last_at_price": local(hit[-1][0] + 300) if hit else None, "moment": local(b[0] + 300),
            "day_low_cad": r2(lo), "day_high_cad": r2(hi), "where_in_day_pct": round(100 * (price_cad - lo) / (hi - lo)) if hi > lo else None}


# ---------------------------------------------------------------------------
# 2. the human read (point in time: only bars that closed before the moment)
# ---------------------------------------------------------------------------
def read(b5: list[tuple], t: int, price: float) -> dict:
    past = [b for b in b5 if b[0] + 300 <= t]
    D = [b for b in resample(past, DAY) if b[0] + DAY <= t]            # closed daily bars
    today = [b for b in past if b[0] >= t - t % DAY]                   # this UTC day so far
    closes = [b[4] for b in D]
    yr = D[-365:]
    low52 = min(b[3] for b in yr)
    low52_t = next(b[0] for b in yr if b[3] == low52)
    high52 = max(b[2] for b in yr)
    high52_t = next(b[0] for b in yr if b[2] == high52)
    ath = max(b[2] for b in D)
    ath_t = next(b[0] for b in D if b[2] == ath)
    loc = {"price_usd": r2(price, 3), "low_52w": r2(low52, 3), "low_52w_on": local(low52_t, "%Y-%m-%d"),
           "above_52w_low_pct": pct(price, low52), "high_52w": r2(high52, 3), "high_52w_on": local(high52_t, "%Y-%m-%d"),
           "below_52w_high_pct": pct(price, high52), "days_since_52w_high": int((t - high52_t) // DAY),
           "where_in_52w_range_pct": round(100 * (price - low52) / (high52 - low52)), "ath": r2(ath, 2),
           "ath_on": local(ath_t, "%Y-%m-%d"), "below_ath_pct": pct(price, ath),
           "new_52w_low_today": bool(today) and min(b[3] for b in today) < low52}

    # support / resistance zones from 3 years of daily swings (a level that was support and resistance counts twice)
    W = D[-3 * 365:]
    off = len(D) - len(W)
    pv = pivots(W, 5)
    pv.sort(key=lambda x: x[1])
    clusters: list[list] = []
    for p in pv:
        if clusters and p[1] <= clusters[-1][0][1] * 1.03:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    zones = []
    for c in clusters:
        lvl = statistics.median(x[1] for x in c)
        lo, hi = min(x[1] for x in c), max(x[1] for x in c)
        bounces = []
        for i, _, kind in c:
            if kind == "LOW":
                nxt = W[i + 1:i + 21]
                if nxt:
                    bounces.append(100 * (max(b[2] for b in nxt) / W[i][3] - 1))
        held = sum(1 for b in W if lo * 0.985 <= b[3] <= hi * 1.015 and b[4] > lo)
        zones.append({"level": r2(lvl, 3), "from": r2(lo, 3), "to": r2(hi, 3), "touches": len(c),
                      "as_support": sum(1 for x in c if x[2] == "LOW"), "as_resistance": sum(1 for x in c if x[2] == "HIGH"),
                      "first": local(W[min(x[0] for x in c)][0], "%Y-%m"), "last": local(W[max(x[0] for x in c)][0], "%Y-%m-%d"),
                      "days_tested_and_held": held, "avg_bounce_20d_pct": r2(statistics.mean(bounces), 1) if bounces else None,
                      "distance_pct": pct(price, lvl)})
    sup = sorted([z for z in zones if z["level"] <= price * 1.02 and z["level"] >= price * 0.75], key=lambda z: -z["level"])[:4]
    res = sorted([z for z in zones if z["level"] > price * 1.02 and z["level"] <= price * 1.4], key=lambda z: z["level"])[:4]

    # trend and how long the fall has lasted
    s50, s200 = sma_series(closes, 50), sma_series(closes, 200)
    below200 = 0
    for i in range(len(closes) - 1, -1, -1):
        if s200[i] is None or closes[i] >= s200[i]:
            break
        below200 += 1
    cross = None
    for i in range(len(closes) - 1, 0, -1):
        if None in (s50[i], s200[i], s50[i - 1], s200[i - 1]):
            break
        if s50[i] < s200[i] and s50[i - 1] >= s200[i - 1]:
            cross = local(D[i][0], "%Y-%m-%d")
            break
        if s50[i] >= s200[i]:
            break
    rets = {f"{n}d": pct(price, closes[-n]) for n in (7, 30, 90) if len(closes) >= n}
    trend = {"sma50": r2(s50[-1], 2), "sma200": r2(s200[-1], 2), "vs_sma200_pct": pct(price, s200[-1]),
             "days_below_sma200": below200, "sma50_below_sma200_since": cross, "returns_pct": rets}

    # selling exhaustion
    vols = [b[5] for b in D]
    med90 = statistics.median(vols[-90:])
    last10 = D[-10:]
    sp = max(last10, key=lambda b: b[5])
    frac = (t % DAY) / DAY
    today_v = sum(b[5] for b in today)
    H = [b for b in resample(past, 3600) if b[0] + 3600 <= t]
    hv = [b[5] for b in H[-30 * 24:]]
    med1h = statistics.median(hv) if hv else None
    h48 = H[-48:]
    hs = max(h48, key=lambda b: b[5]) if h48 else None
    rng = [(b[2] - b[3]) / b[4] for b in D]
    exhaust = {
        "biggest_volume_day_last_10d": {"on": local(sp[0], "%Y-%m-%d"), "x_median_90d": r2(sp[5] / med90, 1),
                                        "day_change_pct": pct(sp[4], sp[1]),
                                        "closed_off_low_pct": round(100 * (sp[4] - sp[3]) / (sp[2] - sp[3])) if sp[2] > sp[3] else None},
        "last_3_days_volume_vs_that_day": r2(statistics.mean(vols[-3:]) / sp[5], 2),
        "today_volume_projected_x_median": r2(today_v / frac / med90, 1) if frac > 0.15 else None,
        "biggest_1h_volume_last_48h": ({"at": local(hs[0] + 3600), "x_median_30d": r2(hs[5] / med1h, 1), "hour_change_pct": pct(hs[4], hs[1]),
                                         "lower_wick_pct_of_range": round(100 * (min(hs[1], hs[4]) - hs[3]) / (hs[2] - hs[3])) if hs[2] > hs[3] else None}
                                        if hs and med1h else None),
        "red_days_last_10": sum(1 for b in last10 if b[4] < b[1]),
        "daily_range_7d_vs_prior_30d": r2(statistics.mean(rng[-7:]) / statistics.mean(rng[-37:-7]), 2),
    }

    # the bear weakening: lower low in price with a higher RSI (divergence), on 4h and daily
    def divergence(bars: list[tuple], k: int, lookback: int) -> dict:
        cl = [b[4] for b in bars] + [price]                  # the moment's price as the provisional close
        rs = rsi_series(cl)
        now_rsi = rs[-1]
        pv_ = [p for p in pivots(bars, k) if p[2] == "LOW" and p[0] >= len(bars) - lookback]
        if not pv_:
            return {"rsi_now": r2(now_rsi, 1), "previous_low": None}
        i, p, _ = min(pv_, key=lambda x: x[1])               # the lowest confirmed swing low in the lookback
        div = price < p and now_rsi is not None and rs[i] is not None and now_rsi > rs[i]
        return {"rsi_now": r2(now_rsi, 1), "previous_low": r2(p, 3), "previous_low_on": local(bars[i][0], "%Y-%m-%d %H:%M"),
                "rsi_at_previous_low": r2(rs[i], 1), "price_vs_previous_low_pct": pct(price, p),
                "bullish_divergence": bool(div)}

    F = [b for b in resample(past, 14400) if b[0] + 14400 <= t]
    weak = {"4h": divergence(F[-180:], 3, 90), "daily": divergence(D[-200:], 3, 90)}
    return {"location": loc, "support": sup, "resistance": res, "trend": trend, "exhaustion": exhaust, "momentum": weak,
            "base": {f"band_{int(b * 100)}pct": base(D, price, b) for b in (0.06, 0.08, 0.10)}}


def base(D: list[tuple], price: float, band: float = 0.08) -> dict | None:
    """The 'stuck' phase right before the moment: the longest run of the latest daily closes that all stayed inside
    one band (default 8% from lowest to highest close). Then: how it was built and what came before it."""
    n = 0
    for k in range(5, min(120, len(D)) + 1):
        w = D[-k:]
        if max(b[4] for b in w) / min(b[4] for b in w) - 1 <= band:
            n = k
        else:
            break                                          # a longer window only gets wider
    if not n:
        return None
    w, pre = D[-n:], D[-n - 20:-n]
    floor, top = min(b[3] for b in w), max(b[2] for b in w)
    half = n // 2
    rng = lambda bars: statistics.mean((b[2] - b[3]) / b[4] for b in bars) if bars else None
    # the move into the base: lowest low of the 90 days before it, then the highest high after that low
    before = D[-n - 90:-n] or D[:1]
    i0 = min(range(len(before)), key=lambda i: before[i][3])
    j0 = max(range(i0, len(before)), key=lambda i: before[i][2])
    run_lo, run_hi = before[i0], before[j0]
    return {"days": n, "from": local(w[0][0], "%Y-%m-%d"), "close_low": r2(min(b[4] for b in w), 3), "close_high": r2(max(b[4] for b in w), 3),
            "floor": r2(floor, 3), "top": r2(top, 3), "width_pct": pct(top, floor),
            "floor_tests": sum(1 for b in w if b[3] <= floor * 1.02), "top_tests": sum(1 for b in w if b[2] >= top * 0.98),
            "higher_lows": min(b[3] for b in w[half:]) > min(b[3] for b in w[:half]) if half else None,
            "volume_vs_20d_before": r2(statistics.mean(b[5] for b in w) / statistics.mean(b[5] for b in pre), 2) if pre else None,
            "daily_range_vs_20d_before": r2(rng(w) / rng(pre), 2) if pre else None,
            "price_in_base_pct": round(100 * (price - floor) / (top - floor)) if top > floor else None,
            "move_before": {"low": r2(run_lo[3], 3), "low_on": local(run_lo[0], "%Y-%m-%d"), "high": r2(run_hi[2], 3),
                            "high_on": local(run_hi[0], "%Y-%m-%d"), "run_up_pct": pct(run_hi[2], run_lo[3]),
                            "pullback_to_floor_pct": pct(floor, run_hi[2])}}


def breakout_after(b5: list[tuple], t: int, bs: dict | None, entry: float) -> dict | None:
    """Which way the base broke after the buy: the first daily close above its top or below its floor."""
    if not bs:
        return None
    D = [b for b in resample([b for b in b5 if b[0] >= t - t % DAY], DAY)]
    for k, b in enumerate(D):
        side = "UP" if b[4] > bs["top"] else "DOWN" if b[4] < bs["floor"] else None
        if side:
            nxt = D[k:k + 30]
            return {"first_break": side, "on": local(b[0], "%Y-%m-%d"), "days_after_buy": k,
                    "best_30d_after_break_pct": pct(max(x[2] for x in nxt), b[4]), "worst_30d_after_break_pct": pct(min(x[3] for x in nxt), b[4]),
                    "buy_vs_floor_pct": pct(entry, bs["floor"])}
    return {"first_break": "NONE_YET"}


def weekly_cad(b5: list[tuple], t: int, fx: "FX", weeks: int = 10) -> list[dict]:
    W = [b for b in resample([b for b in b5 if t - weeks * 7 * DAY - 7 * DAY <= b[0] < t], 7 * DAY)]
    out = []
    for b in W[-weeks:]:
        r = fx.at(b[0] + 3 * DAY)
        out.append({"week_of": local(b[0], "%Y-%m-%d"), "high_cad": r2(b[2] * r, 1), "low_cad": r2(b[3] * r, 1), "close_cad": r2(b[4] * r, 1)})
    return out


def market(b5: list[tuple], t: int) -> dict:
    past = [b for b in b5 if b[0] + 300 <= t]
    price = past[-1][4]
    D = [b for b in resample(past, DAY) if b[0] + DAY <= t]
    yr = D[-365:]
    low52, high52 = min(b[3] for b in yr), max(b[2] for b in yr)
    cl = [b[4] for b in D] + [price]
    s200 = sma_series([b[4] for b in D], 200)[-1]
    lo30 = min(b[3] for b in D[-30:])
    return {"price_usd": r2(price, 2), "above_52w_low_pct": pct(price, low52), "below_52w_high_pct": pct(price, high52),
            "vs_sma200_pct": pct(price, s200), "rsi_daily": r2(rsi_series(cl)[-1], 1),
            "ret_7d_pct": pct(price, D[-7][4]), "ret_30d_pct": pct(price, D[-30][4]),
            "at_new_30d_low": min(b[3] for b in past[-288:]) <= lo30}


# ---------------------------------------------------------------------------
# 3. what Ananta's Explorer did around the moment (same engine as live)
# ---------------------------------------------------------------------------
def ananta(db: str, coin: str, t: int, rules: str, b5: list[tuple], btc5: list[tuple]) -> dict:
    lo, hi = t - 150 * DAY, t + 30 * DAY
    sb = [b for b in b5 if lo <= b[0] < hi]
    b1h = resample([b for b in btc5 if lo <= b[0] < hi], 3600)
    s = xe.TfState("1h")
    ts, ctx = [], []
    for b in b1h:
        s.add(*b)
        if s.n < 60:
            continue
        c = b[4]
        e50, e50_5, e20, e20_3 = s.e50h[-1], s.ema_ago("50", 5), s.e20h[-1], s.ema_ago("20", 3)
        ts.append(b[0] + 3600)
        ctx.append({"btc_S1": "BULL" if c > e50 and e50 > e50_5 else "BEAR" if c < e50 and e50 < e50_5 else "NEUTRAL",
                    "btc_S2": "UP" if c > e20 and e20 > e20_3 else "DOWN" if c < e20 and e20 < e20_3 else "FLAT",
                    "btc_1h_ret": c / b[1] - 1})

    def bctx(T: int) -> dict:
        i = bisect.bisect_right(ts, T) - 1
        return ctx[i] if i >= 0 and T - ts[i] <= 2 * 3600 else {}

    events: list[dict] = []
    w0, w1 = t - 3 * DAY, t + 3 * DAY
    eng = xe.CoinEngine(coin, trade_from_t=w0, btc_ctx=bctx, rules=xe.RULESETS[rules], random_rate=0.0,
                        on_event=lambda e: events.append(e))
    seen: dict[str, int] = {}
    view = None
    ev = event_stream(sb)
    i, n = 0, len(ev)
    while i < n:
        T = ev[i][0]
        while i < n and ev[i][0] == T:
            eng.on_bar(ev[i][2], ev[i][3])
            i += 1
        if T % 900 == 0:
            if T > w1:
                eng.trade_from_t = 10 ** 12          # stop new entries after the window; open trades still run
            rec = eng.scan(T)
            if w0 <= T <= w1:
                for x in rec.get("sightings", []):
                    seen[x] = seen.get(x, 0) + 1
            if T <= t and eng.ready():
                view = (T, rec.get("state"), eng.state(T)["zones"])
    orders = [{"at": local(e["t"]), "setup": e["setup"], "type": e["type"], "limit_usd": r2(e["limit"], 3),
               "taken": e.get("shadow") is None, "why_not": e.get("shadow")} for e in events if e["kind"] == "ORDER"]
    rows = eng.trade_rows(eng.closed + [tr for tr in eng.trades])
    trades = [{"setup": r["setup"], "type": r["type"], "real": not r["shadow"], "why_not": r["shadow"] or None,
               "entry_usd": r2(r["entry"], 3), "entry_at": local(r["entry_t"]), "net_usd_per_100": r["ACTUAL_net"],
               "exit": r["ACTUAL_bell"], "exit_at": local(r["ACTUAL_exit_t"]) if r["ACTUAL_exit_t"] else None}
              for r in rows if r["entry_t"] >= w0]
    T0, tags, z = view if view else (None, {}, {})
    return {"rules": rules, "window": f"{local(w0)} .. {local(w1)}", "sightings": seen, "orders": orders, "trades": trades,
            "view_at_moment": {"scan": local(T0) if T0 else None, **(tags or {}),
                               "its_support_usd": r2(z.get("support"), 3), "its_resistance_usd": r2(z.get("resistance"), 3)}}


# ---------------------------------------------------------------------------
# 4. what happened next
# ---------------------------------------------------------------------------
def after(b5: list[tuple], t: int, entry: float, live_d: list[tuple], fx: FX) -> dict:
    nxt = [b for b in b5 if b[0] >= t]
    out: dict = {"data_to": local(nxt[-1][0], "%Y-%m-%d") if nxt else None}
    for h in (1, 7, 30, 60, 90):
        w = [b for b in nxt if b[0] < t + h * DAY]
        if not w or w[-1][0] < t + h * DAY - 3600:
            continue
        out[f"{h}d"] = {"best_pct": pct(max(b[2] for b in w), entry), "worst_pct": pct(min(b[3] for b in w), entry),
                        "close_pct": pct(w[-1][4], entry)}
    path = [(b[0], b[2], b[3], b[4]) for b in nxt]
    end = nxt[-1][0] if nxt else t
    path += [(b[0], b[2], b[3], b[4]) for b in live_d if b[0] > end]          # after the lab data ends: live daily bars
    if path:
        lo = min(path, key=lambda x: x[2])
        out["deepest_drop_after"] = {"pct": pct(lo[2], entry), "on": local(lo[0], "%Y-%m-%d"), "usd": r2(lo[2], 3),
                                     "cad": r2(lo[2] * fx.at(lo[0]), 2)}
        for g in (10, 20, 30):
            hit = next((x for x in path if x[1] >= entry * (1 + g / 100)), None)
            out[f"first_+{g}pct"] = local(hit[0], "%Y-%m-%d") if hit else None
        last = path[-1]
        out["latest"] = {"on": local(last[0], "%Y-%m-%d"), "usd": r2(last[3], 3), "cad": r2(last[3] * fx.at(last[0]), 2),
                         "vs_entry_pct": pct(last[3], entry)}
    return out


# ---------------------------------------------------------------------------
def run(db: str, fx_path: str, cases_path: str, live_bars: str | None, out: str) -> dict:
    fx = FX(fx_path)
    cases = json.loads(Path(cases_path).read_text())["cases"]
    t_min = min(day_start(c["date"]) for c in cases) - 3 * 365 * DAY - 30 * DAY
    t_max = max(day_start(c["date"]) for c in cases) + 120 * DAY
    data = {k: load(db, k, t_min, t_max) for k in {"BTC", "ETH", *(c["coin"] for c in cases)}}
    res = []
    for c in cases:
        b5 = data[c["coin"]]
        p = pin(b5, fx, c["date"], c["price_cad"])
        t, entry = p["t"], p["price_usd"]
        rd = read(b5, t, entry)
        row = {"case": c, "pin": p, "read": rd,
               "market": {k: market(data[k], t) for k in ("BTC", "ETH") if k != c["coin"]},
               "ananta": {r: ananta(db, c["coin"], t, r, b5, data["BTC"]) for r in ("C0", "W1")},
               "after": after(b5, t, entry, live_daily(live_bars, c["coin"]), fx),
               "base_break": breakout_after(b5, t, rd["base"]["band_8pct"], entry),
               "weeks_cad": weekly_cad(b5, t, fx)}
        eth = row["market"].get("ETH")
        if eth:
            eth["price_cad"] = r2(eth["price_usd"] * p["fx"], 0)
        res.append(row)
    Path(out).mkdir(parents=True, exist_ok=True)
    Path(out, "casebook_rebuild.json").write_text(json.dumps(res, indent=1, default=str))
    return {"cases": len(res), "out": str(Path(out, "casebook_rebuild.json"))}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--fx", required=True)
    ap.add_argument("--cases", default="docs/casebook/cases.json")
    ap.add_argument("--live-bars", default=None)
    ap.add_argument("--out", default=os.path.expanduser("~/ananta_runs/casebook"))
    a = ap.parse_args(argv)
    print(json.dumps(run(a.db, a.fx, a.cases, a.live_bars, a.out), indent=1))


if __name__ == "__main__":
    main()
