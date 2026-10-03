"""First look: the rule-based systems taught on Trading with Rayner and Trade With Trend, on our 10 coins.

Exactly the parameters the teachers state (no tuning), daily / weekly bars built from our 5m Binance data, NDAX costs
(0.20% fee + the coin's half-spread, each side). BTC is the "index" wherever a teacher uses one.
DISCOVERY < 2024-01-01 <= CONFIRM < 2026-08-01; the Aug-Sep 2026 holdout is never loaded (same rule as every study).
This is a first look for Madhav, not a validation: 5 variants are tried here and all 5 are reported.

  S1  Rayner weekly breakout trend-following: BTC above its 100-week average; buy the week after a close above the
      50-week high; sell the week after a close below the 40-week low.
  S2  Rayner Bollinger breakout: BTC above its 300-day average; buy after a close above the 200-day band at +4 SD;
      sell after a close below the 200-day band at -0.5 SD.
  S3  Rayner mean reversion: close above the 200-day average and below the 20-day band at -2.5 SD; buy with a limit
      3% under that close the next day; sell after RSI(2) closes above 50, or after 10 days.
  S4  Weinstein stage 2 (as taught on Trade With Trend, 30-week average): weekly close above a rising 30-week average,
      above the highest close of the prior 26 weeks, on at least 2x the 10-week average volume, with relative strength
      vs BTC above its own 52-week average; sell the week after a close below the 30-week average. (BTC itself skipped.)
  S4b the same with Trade With Trend's 50-week average.
Each coin is its own 10% slot (equal weight); a slot is in cash when out of a trade.

    python -m src.research.teacher_systems --db ~/code/ananta-decision-agent/ananta-quant-research-db/lab5_5m.sqlite
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sqlite3
import statistics
from pathlib import Path

from src.intelligence.explorer_engine import COINS, HALF_SPREAD, NDAX_FEE
from src.research.explorer_replay import CONF_END, DISC_END

DAY = 86400
PERIODS = {"DISCOVERY": (0, DISC_END), "CONFIRM": (DISC_END, CONF_END)}


def cost(coin: str) -> float:
    return NDAX_FEE + HALF_SPREAD.get(coin, 0.004)


def daily(db: str, coin: str) -> list[tuple]:
    """UTC daily bars from 5m (days with at least 200 of 288 bars), never past the holdout start."""
    con = sqlite3.connect(f"file:{os.path.expanduser(db)}?mode=ro", uri=True)
    try:
        cur = con.execute("SELECT event_unix, open, high, low, close, volume FROM bars WHERE instrument=? AND event_unix < ? "
                          "ORDER BY event_unix", (f"{coin}-USD-SPOT", CONF_END))
        out, day, acc = [], None, []
        for r in cur:
            d = r[0] // DAY
            if d != day:
                if len(acc) >= 200:
                    out.append((day * DAY, acc[0][1], max(x[2] for x in acc), min(x[3] for x in acc), acc[-1][4], sum(x[5] for x in acc)))
                day, acc = d, []
            acc.append(r)
        if len(acc) >= 200:
            out.append((day * DAY, acc[0][1], max(x[2] for x in acc), min(x[3] for x in acc), acc[-1][4], sum(x[5] for x in acc)))
        return out
    finally:
        con.close()


def weekly(D: list[tuple]) -> list[tuple]:
    """Monday-to-Sunday weeks (complete weeks only); t = the Monday."""
    out, cur, key = [], [], None
    for b in D:
        k = (b[0] // DAY - 4) // 7                # day 4 since 1970-01-01 was a Monday
        if k != key:
            if len(cur) == 7:
                out.append((cur[0][0], cur[0][1], max(x[2] for x in cur), min(x[3] for x in cur), cur[-1][4], sum(x[5] for x in cur)))
            cur, key = [], k
        cur.append(b)
    if len(cur) == 7:
        out.append((cur[0][0], cur[0][1], max(x[2] for x in cur), min(x[3] for x in cur), cur[-1][4], sum(x[5] for x in cur)))
    return out


def sma(x: list[float], n: int) -> list[float | None]:
    out, s = [None] * len(x), 0.0
    for i, v in enumerate(x):
        s += v
        if i >= n:
            s -= x[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def sd(x: list[float], n: int) -> list[float | None]:
    out = [None] * len(x)
    for i in range(n - 1, len(x)):
        out[i] = statistics.pstdev(x[i - n + 1:i + 1])
    return out


def rsi2(c: list[float]) -> list[float | None]:
    out = [None] * len(c)
    ag = al = None
    for i in range(1, len(c)):
        g, l_ = max(c[i] - c[i - 1], 0), max(c[i - 1] - c[i], 0)
        if i < 2:
            continue
        if ag is None:
            ag = (max(c[1] - c[0], 0) + g) / 2
            al = (max(c[0] - c[1], 0) + l_) / 2
        else:
            ag, al = (ag + g) / 2, (al + l_) / 2
        out[i] = 100.0 if al == 0 else 100 - 100 / (1 + ag / al)
    return out


# ---------------------------------------------------------------------------
# signals -> trades: (entry_t, entry_px, exit_t, exit_px). Signals act at the NEXT bar's open (no look-ahead).
# ---------------------------------------------------------------------------
def s1(W: list[tuple], btcW: list[tuple]) -> list[tuple]:
    bt = {b[0]: b[4] for b in btcW}
    bts = [b[0] for b in btcW]
    bma = dict(zip(bts, sma([b[4] for b in btcW], 100)))
    tr, pos = [], None
    for i in range(50, len(W) - 1):
        c = W[i][4]
        if pos is None:
            hi50 = max(b[2] for b in W[i - 50:i])
            m = bma.get(W[i][0])
            if c > hi50 and m is not None and bt.get(W[i][0], 0) > m:
                pos = (W[i + 1][0], W[i + 1][1])
        else:
            lo40 = min(b[3] for b in W[max(0, i - 40):i])
            if c < lo40:
                tr.append((*pos, W[i + 1][0], W[i + 1][1]))
                pos = None
    if pos:
        tr.append((*pos, W[-1][0] + 7 * DAY, W[-1][4]))
    return tr


def s2(D: list[tuple], btcD: list[tuple]) -> list[tuple]:
    bclose = {b[0]: b[4] for b in btcD}
    bma = dict(zip([b[0] for b in btcD], sma([b[4] for b in btcD], 300)))
    c = [b[4] for b in D]
    m, s = sma(c, 200), sd(c, 200)
    tr, pos = [], None
    for i in range(200, len(D) - 1):
        if m[i] is None:
            continue
        if pos is None:
            bm = bma.get(D[i][0])
            if c[i] > m[i] + 4 * s[i] and bm is not None and bclose.get(D[i][0], 0) > bm:
                pos = (D[i + 1][0], D[i + 1][1])
        elif c[i] < m[i] - 0.5 * s[i]:
            tr.append((*pos, D[i + 1][0], D[i + 1][1]))
            pos = None
    if pos:
        tr.append((*pos, D[-1][0] + DAY, D[-1][4]))
    return tr


def s3(D: list[tuple]) -> list[tuple]:
    c = [b[4] for b in D]
    m200, m20, s20, r = sma(c, 200), sma(c, 20), sd(c, 20), rsi2(c)
    tr, i = [], 200
    while i < len(D) - 1:
        if m200[i] is not None and c[i] > m200[i] and c[i] < m20[i] - 2.5 * s20[i]:
            lim = 0.97 * c[i]
            nb = D[i + 1]
            if nb[3] <= lim:                                   # filled next day
                px = min(nb[1], lim)
                j, k = i + 1, None
                while j < len(D) - 1:
                    if (r[j] is not None and r[j] > 50) or j - (i + 1) >= 9:   # exit next open (max 10 days held)
                        k = j
                        break
                    j += 1
                if k is None:
                    tr.append((nb[0], px, D[-1][0] + DAY, D[-1][4]))
                    break
                tr.append((nb[0], px, D[k + 1][0], D[k + 1][1]))
                i = k + 1
                continue
        i += 1
    return tr


def s4(W: list[tuple], btcW: list[tuple], ma_n: int = 30) -> list[tuple]:
    bc = {b[0]: b[4] for b in btcW}
    c = [b[4] for b in W]
    v = [b[5] for b in W]
    m = sma(c, ma_n)
    rs = [c[i] / bc[W[i][0]] if W[i][0] in bc else None for i in range(len(W))]
    tr, pos = [], None
    for i in range(max(ma_n + 4, 52), len(W) - 1):
        if m[i] is None or m[i - 4] is None:
            continue
        if pos is None:
            rsw = [x for x in rs[i - 51:i + 1] if x is not None]
            if rs[i] is None or len(rsw) < 40:
                continue
            ok = (c[i] > m[i] and m[i] > m[i - 4] and c[i] > max(c[i - 26:i])
                  and v[i] >= 2 * statistics.mean(v[i - 10:i]) and rs[i] > statistics.mean(rsw))
            if ok:
                pos = (W[i + 1][0], W[i + 1][1])
        elif c[i] < m[i]:
            tr.append((*pos, W[i + 1][0], W[i + 1][1]))
            pos = None
    if pos:
        tr.append((*pos, W[-1][0] + 7 * DAY, W[-1][4]))
    return tr


# ---------------------------------------------------------------------------
def score(trades: dict[str, list[tuple]], D: dict[str, list[tuple]], p0: int, p1: int, seed: int = 7) -> dict:
    """Trades entered inside [p0, p1) (an open trade is marked at the period's last close); equal-weight 10% slots."""
    rnd = random.Random(seed)
    rows, rand, slot_growth = [], [], []
    for coin, tl in trades.items():
        days = [b for b in D[coin] if p0 <= b[0] < p1]
        if not days:
            continue
        g = 1.0
        for (et, ep, xt, xp) in tl:
            if not (p0 <= et < p1):
                continue
            if xt >= p1:                                    # still open at period end: mark at the last close
                xt, xp = days[-1][0] + DAY, days[-1][4]
            net = (xp / ep) * (1 - cost(coin)) ** 2 - 1
            rows.append({"coin": coin, "ret": net, "days": max(1, (xt - et) // DAY)})
            g *= 1 + net
            # random baseline: same coin, same holding length, random start inside the period
            hold = max(1, (xt - et) // DAY)
            if len(days) > hold + 1:
                draws = []
                for _ in range(50):
                    k = rnd.randrange(0, len(days) - hold)
                    draws.append((days[k + hold][1] / days[k][1]) * (1 - cost(coin)) ** 2 - 1)
                rand.append(statistics.mean(draws))
        slot_growth.append(g)
    if not rows:
        return {"trades": 0}
    rets = [r["ret"] for r in rows]
    hold_bh = []
    for coin in trades:
        days = [b for b in D[coin] if p0 <= b[0] < p1]
        if len(days) > 30:
            hold_bh.append(days[-1][4] / days[0][1] - 1)
    in_mkt = sum(r["days"] for r in rows)
    span = sum(len([b for b in D[c] if p0 <= b[0] < p1]) for c in trades)
    return {"trades": len(rows), "win_rate": round(sum(1 for x in rets if x > 0) / len(rets), 3),
            "avg_trade_pct": round(100 * statistics.mean(rets), 2), "median_trade_pct": round(100 * statistics.median(rets), 2),
            "best_pct": round(100 * max(rets), 1), "worst_pct": round(100 * min(rets), 1),
            "avg_hold_days": round(statistics.mean(r["days"] for r in rows), 1),
            "random_same_hold_avg_pct": round(100 * statistics.mean(rand), 2) if rand else None,
            "portfolio_growth_pct": round(100 * (statistics.mean(slot_growth + [1.0] * (len(trades) - len(slot_growth))) - 1), 1),
            "buy_hold_equal_weight_pct": round(100 * statistics.mean(hold_bh), 1) if hold_bh else None,
            "time_in_market_pct": round(100 * in_mkt / span, 1) if span else None}


def run(db: str, out: str | None = None) -> dict:
    D = {c: daily(db, c) for c in COINS}
    W = {c: weekly(D[c]) for c in COINS}
    systems = {
        "S1_rayner_weekly_breakout": {c: s1(W[c], W["BTC"]) for c in COINS},
        "S2_rayner_bollinger_breakout": {c: s2(D[c], D["BTC"]) for c in COINS},
        "S3_rayner_mean_reversion": {c: s3(D[c]) for c in COINS},
        "S4_weinstein_stage2_30w": {c: s4(W[c], W["BTC"], 30) for c in COINS if c != "BTC"},
        "S4b_weinstein_stage2_50w_twt": {c: s4(W[c], W["BTC"], 50) for c in COINS if c != "BTC"},
    }
    res = {"data": {c: [local_day(D[c][0][0]), local_day(D[c][-1][0])] for c in COINS},
           "costs_round_trip_pct": {c: round(200 * cost(c), 2) for c in COINS}, "systems": {}}
    for name, tr in systems.items():
        res["systems"][name] = {p: score(tr, D, a, b) for p, (a, b) in PERIODS.items()}
    if out:
        Path(out).write_text(json.dumps(res, indent=1))
    return res


def local_day(t: int) -> str:
    import time
    return time.strftime("%Y-%m-%d", time.gmtime(t))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    print(json.dumps(run(a.db, a.out), indent=1))


if __name__ == "__main__":
    main()
