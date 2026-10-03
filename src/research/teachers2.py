"""Review #13 (docs/research/REVIEW_13.md): the remaining teacher ideas.

    python -m src.research.teachers2 --db .../lab5_5m.sqlite --out ~/ananta_runs/teachers2

H07 RSI dip in an uptrend, H12 first pullback after a breakout, H13 false break of a support zone (entries, 20-day excess over the
same-condition average); H16 breadth (market idea); P03 book stop on T3 (book idea). Everything uses earlier bars only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from src.research import portfolio_trend as PT
from src.research import reads as R
from src.research import zones as Z

DAY = 86400
H = 20


def _gate(B: R.Series, t: int) -> bool:
    bi = B.at(t)
    return bool(bi is not None and B.ema50[bi] is not None and B.c[bi] > B.ema50[bi])


def _r(A: Z.Arr, k0: int, px: float, cost: float) -> float:
    return float(A.o[k0 + H] / px * (1 - cost) ** 2 - 1)


def entries(coin: str, S: R.Series, B: R.Series, until: int) -> list[dict]:
    """Signal events (entry index, entry price, variant)."""
    A = Z.Arr(S)
    rsi10 = R.rsi(S.c, 10)
    e20 = R.ema(S.c, 20)
    n = len(S.t)
    cost = R.cost(coin)
    out, last = [], {}
    swing, swing_at = None, -999
    pending = []                                   # H12: breakouts waiting for their first pullback
    for i in range(400, n - H - 2):
        if S.t[i] >= until or math.isnan(A.atr[i - 1]):
            continue
        mkt = _gate(B, S.t[i])
        found = []
        # H07
        if S.sma200[i] is not None and A.c[i] > S.sma200[i] and rsi10[i] is not None and rsi10[i] < 30:
            k0 = i + 1
            own = None
            for k in range(k0, min(k0 + 10, n - 1)):
                if rsi10[k] is not None and rsi10[k] > 40:
                    own = float(A.o[k + 1] / A.o[k0] * (1 - cost) ** 2 - 1)
                    break
            if own is None:
                own = float(A.o[min(k0 + 10, n - 1)] / A.o[k0] * (1 - cost) ** 2 - 1)
            found.append(("H07", k0, float(A.o[k0]), {"own_exit": own}))
        # H12
        if mkt and A.c[i] > max(A.h[i - 20:i]):
            pending.append({"start": i, "pull": None})
        still = []
        for p in pending:
            if p["pull"] is None:
                if i - p["start"] > 15:
                    continue
                if i > p["start"] and e20[i] is not None and A.l[i] <= e20[i] < A.c[i]:
                    p["pull"] = i
                still.append(p)
            else:
                if i - p["pull"] > 5:
                    continue
                if i > p["pull"] and A.h[i] > A.h[p["pull"]]:
                    px = max(float(A.o[i]), float(A.h[p["pull"]]))
                    if i + H < n:
                        found.append(("H12", i, px, {}))
                    continue
                still.append(p)
        pending = still
        # H13
        if mkt:
            if i - swing_at >= Z.REFRESH:
                swing, swing_at = Z.swing_zones(A, i), i
            for z in Z.zone_map(A, i, swing):
                if "EXTREME" in z["kinds"]:
                    continue
                if z["top"] < A.c[i - 1] and A.l[i] < z["bot"] and A.c[i] > z["bot"]:
                    found.append(("H13", i + 1, float(A.o[i + 1]), {}))
                    break
        for v, k0, px, extra in found:
            if v in last and S.t[i] - last[v] <= 5 * DAY:
                continue
            if k0 + H >= n:
                continue
            last[v] = S.t[i]
            out.append({"coin": coin, "t": S.t[i], "variant": v, "r20": _r(A, k0, px, cost), **extra})
    return out


def cond_drift(coin: str, S: R.Series, B: R.Series, lo: int, hi: int, need200: bool, needmkt: bool) -> float | None:
    A = Z.Arr(S)
    cost = R.cost(coin)
    xs = []
    for i in range(400, len(S.t) - H - 2):
        if not (lo <= S.t[i] < hi):
            continue
        if needmkt and not _gate(B, S.t[i]):
            continue
        if need200 and not (S.sma200[i] is not None and A.c[i] > S.sma200[i]):
            continue
        xs.append(_r(A, i + 1, float(A.o[i + 1]), cost))
    return statistics.mean(xs) if xs else None


def _mk(evs: list[dict]) -> list[list[dict]]:
    out: list[list[dict]] = []
    for e in sorted(evs, key=lambda x: x["t"]):
        if out and e["t"] - out[-1][0]["t"] <= 3 * DAY:
            out[-1].append(e)
        else:
            out.append([e])
    return out


def judge(evs: list[dict]) -> dict:
    res = {}
    for sp in ("DISCOVERY", "CONFIRM"):
        rr = [e for e in evs if e["split"] == sp]
        mk = _mk(rr)
        xs = [statistics.mean(x["x20"] for x in m) for m in mk]
        sd = statistics.stdev(xs) if len(xs) > 2 else None
        res[sp] = {"episodes": len(rr), "market_events": len(mk), "mean_excess20_pct": round(100 * statistics.mean(xs), 2) if xs else None,
                   "z": round(statistics.mean(xs) / (sd / len(xs) ** 0.5), 2) if sd else None,
                   "mean_net20_pct": round(100 * statistics.mean(e["r20"] for e in rr), 2) if rr else None,
                   "win20": round(sum(e["r20"] > 0 for e in rr) / len(rr), 3) if rr else None}
        if rr and "own_exit" in rr[0]:
            res[sp]["own_exit_mean_pct"] = round(100 * statistics.mean(e["own_exit"] for e in rr), 2)
            res[sp]["own_exit_win"] = round(sum(e["own_exit"] > 0 for e in rr) / len(rr), 3)
    d, c = res["DISCOVERY"], res["CONFIRM"]
    ok_d = d["market_events"] >= 30 and (d["mean_excess20_pct"] or -1) > 0 and (d["z"] or 0) >= 2.5
    res["status"] = "PASS" if ok_d and (c["mean_excess20_pct"] or -1) > 0 else "NOT_CONFIRMED" if ok_d else "FAIL"
    return res


def breadth(D: dict[str, list[tuple]]) -> dict:
    SS = {c: R.Series(v) for c, v in D.items()}
    B = SS["BTC"]
    days = [t for t in B.t if t >= B.t[0] + 400 * DAY]
    rows = []
    k = 0
    while k < len(days):
        t = days[k]
        if not _gate(B, t):
            k += 1
            continue
        above50 = above200 = n = 0
        rets = []
        for c, S in SS.items():
            i = S.at(t)
            if i is None or i + H + 1 >= len(S.t) or S.sma200[i] is None:
                continue
            n += 1
            e50 = R.ema(S.c[: i + 1], 50)[-1]
            above50 += S.c[i] > e50
            above200 += S.c[i] > S.sma200[i]
            rets.append(S.o[i + 1 + H] / S.o[i + 1] * (1 - R.cost(c)) ** 2 - 1)
        if n >= 8 and rets:
            rows.append({"t": t, "strong": above50 >= 0.7 * n and above200 >= 0.5 * n, "ret": statistics.mean(rets)})
            k += H                                           # one sample every 20 days: no overlap
        else:
            k += 1
    out = {}
    for sp, lo, hi in (("DISCOVERY", 0, R.DISC_END), ("CONFIRM", R.DISC_END, R.CONF_END)):
        s = [r["ret"] for r in rows if lo <= r["t"] < hi and r["strong"]]
        w = [r["ret"] for r in rows if lo <= r["t"] < hi and not r["strong"]]
        diff = statistics.mean(s) - statistics.mean(w) if s and w else None
        se = math.sqrt(statistics.variance(s) / len(s) + statistics.variance(w) / len(w)) if len(s) > 2 and len(w) > 2 else None
        out[sp] = {"strong_n": len(s), "weak_n": len(w), "strong_ret_pct": round(100 * statistics.mean(s), 2) if s else None,
                   "weak_ret_pct": round(100 * statistics.mean(w), 2) if w else None, "diff_pts": None if diff is None else round(100 * diff, 2),
                   "z": round(diff / se, 2) if diff is not None and se else None}
    d, c = out["DISCOVERY"], out["CONFIRM"]
    if d["strong_n"] < 30 or d["weak_n"] < 30:
        out["status"] = "INSUFFICIENT"
    else:
        ok_d = (d["diff_pts"] or -1) > 0 and (d["z"] or 0) >= 2.5
        out["status"] = "PASS" if ok_d and (c["diff_pts"] or -1) > 0 else "NOT_CONFIRMED" if ok_d else "FAIL"
    return out


def simulate_book_stop(data, days, on, avail, dd: float = 0.08, cool: int = 5) -> dict:
    """PT.simulate with P03: when equity falls dd under its high since the book last left cash, go to cash for `cool` days."""
    on = on.copy()
    O = pd.DataFrame({k: v["o"] for k, v in data.items()}).reindex(days).ffill()
    C = pd.DataFrame({k: v["c"] for k, v in data.items()}).reindex(days).ffill()
    coins = list(C.columns)
    units = np.zeros(len(coins))
    cash, trades, costs = 1.0, 0, 0.0
    eq = np.full(len(days), np.nan)
    exposure = np.zeros(len(days))
    prev_on = np.zeros(len(coins), dtype=bool)
    hs = np.array([PT.FEE + PT.HALF_SPREAD.get(c, 0.004) for c in coins])
    peak, frozen_until, stops = None, -1, 0
    for d in range(len(days)):
        if d > 0:
            sig = on.iloc[d - 1].to_numpy(dtype=bool).copy()
            if d <= frozen_until:
                sig[:] = False
            av = avail.iloc[d - 1].to_numpy(dtype=bool).copy()
            px = O.iloc[d].to_numpy()
            ok = ~np.isnan(px)
            sig &= ok
            n_av = int((av & ok).sum())
            value = units * np.nan_to_num(px)
            equity = cash + value.sum()
            weekly = days[d].weekday() == 0
            if n_av and (weekly or (sig != prev_on).any()):
                target = np.where(sig, equity / n_av, 0.0)
                delta = target - value
                delta[~ok] = 0.0
                c = (np.abs(delta) * hs).sum()
                trades += int(((np.abs(delta) > 1e-9) & ((sig != prev_on) | weekly)).sum())
                costs += c
                cash -= delta.sum() + c
                units = np.where(ok, (value + delta) / np.where(ok, px, 1.0), units)
            prev_on = sig
        cl = C.iloc[d].to_numpy()
        val = units * np.nan_to_num(cl)
        eq[d] = cash + val.sum()
        exposure[d] = val.sum() / eq[d] if eq[d] > 0 else 0.0
        if exposure[d] < 0.01:
            peak = None                                       # in cash: the next stint starts a new high mark
        else:
            peak = eq[d] if peak is None else max(peak, eq[d])
            if eq[d] < (1 - dd) * peak and d >= frozen_until:
                frozen_until = d + cool                         # decided at this close: cash from tomorrow for `cool` days
                stops += 1
                peak = None
    return {"equity": pd.Series(eq, index=days), "trades": trades, "costs": costs, "exposure": pd.Series(exposure, index=days), "stops": stops}


def book_stop(db: str) -> dict:
    data = {c: PT.daily(db, c) for c in PT.COINS}
    data = {k: v for k, v in data.items() if len(v)}
    days = pd.date_range(min(v.index.min() for v in data.values()), max(v.index.max() for v in data.values()), freq="D")
    sig = PT.signals(data, days)
    out = {}
    for name, sim in (("T3", PT.simulate(data, days, sig["T3"], sig["_avail"])),
                      ("T3_P03", simulate_book_stop(data, days, sig["T3"], sig["_avail"]))):
        eq, exp = sim["equity"], sim["exposure"]
        start = eq.index[eq.index >= eq.index[0] + pd.Timedelta(days=50)][0]
        eq = eq[eq.index >= start]
        out[name] = {"DISCOVERY": PT.metrics(eq[eq.index < PT.DISC_END], exp), "CONFIRM": PT.metrics(eq[eq.index >= PT.DISC_END], exp),
                     "trades": sim["trades"], "book_stops": sim.get("stops")}
    ok = all((out["T3_P03"][sp].get("mar") or -9) > (out["T3"][sp].get("mar") or -9) for sp in ("DISCOVERY", "CONFIRM"))
    out["status"] = "PASS" if ok else "FAIL"
    return out


def review13(db: str, cache: Path) -> dict:
    D = {c: R.cached_daily(db, c, cache, R.CONF_END) for c in R.COINS}
    B = R.Series(D["BTC"])
    splits = {"DISCOVERY": (0, R.DISC_END), "CONFIRM": (R.DISC_END, R.CONF_END)}
    evs = []
    for c, bars in D.items():
        S = B if c == "BTC" else R.Series(bars)
        base = {}
        for sp, (lo, hi) in splits.items():
            base[(sp, "H07")] = cond_drift(c, S, B, lo, hi, True, False)
            base[(sp, "MKT")] = cond_drift(c, S, B, lo, hi, False, True)
        for e in entries(c, S, B, R.CONF_END):
            sp = "DISCOVERY" if e["t"] < R.DISC_END else "CONFIRM"
            b = base[(sp, "H07" if e["variant"] == "H07" else "MKT")]
            if b is not None:
                evs.append({**e, "split": sp, "x20": e["r20"] - b})
        print(c, len(evs), file=sys.stderr)
    rep = {v: judge([e for e in evs if e["variant"] == v]) for v in ("H07", "H12", "H13")}
    rep["H16"] = breadth(D)
    rep["P03"] = book_stop(db)
    return rep


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", default="~/ananta_runs/teachers2")
    a = ap.parse_args(argv)
    out = Path(os.path.expanduser(a.out))
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rep = review13(a.db, Path(os.path.expanduser("~/ananta_runs/reads")))
    rep["_meta"] = {"run": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pre_registration": "docs/research/REVIEW_13.md"}
    (out / "review13_results.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps(rep, indent=1, default=str))
    print(f"{time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
