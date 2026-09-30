"""Review #4 (docs/repair_shop/REVIEW_4.md): portfolio trend exposure with crash protection vs buy-and-hold.

    python -m src.research.portfolio_trend run --db LAB5 --out DIR

Daily decisions on UTC daily closes (built from 5m, holdout never loaded), traded at the next day's open,
NDAX market costs (0.20% fee + coin half-spread) on every change. Equal target share per available coin.
Interpretation note (T3): "exit on EMA20, re-enter on the T2 rule" is implemented as holding only while
close > EMA50 AND close > EMA20 AND the BTC gate is on, so an EMA20 exit is not undone the next day.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
from pathlib import Path

import numpy as np
import pandas as pd

COINS = ["BTC", "ETH", "SOL", "ADA", "DOGE", "AVAX", "BCH", "LINK", "LTC", "XRP"]
HALF_SPREAD = {"BTC": 0.00178, "ETH": 0.00084, "SOL": 0.00289, "ADA": 0.00273, "DOGE": 0.00307,
               "AVAX": 0.00370, "BCH": 0.00400, "LINK": 0.00341, "LTC": 0.00334, "XRP": 0.00251}
FEE = 0.0020
CUT = 1785542400                   # 2026-08-01: holdout starts
DISC_END = pd.Timestamp("2024-01-01")
STRATS = ("BH", "T1", "T2", "T3", "T4")
CRISES = {"COVID_2020": ("2020-03-05", "2020-03-20"), "MAY_2021": ("2021-05-10", "2021-05-25"),
          "LUNA_3AC_2022": ("2022-05-05", "2022-06-20"), "FTX_2022": ("2022-11-05", "2022-11-15"),
          "AUG_2024": ("2024-08-01", "2024-08-08"), "OCT_2025": ("2025-10-09", "2025-10-12")}


def daily(db: str, coin: str) -> pd.DataFrame:
    con = sqlite3.connect(f"file:{os.path.expanduser(db)}?mode=ro", uri=True)
    try:
        a = pd.read_sql_query("SELECT event_unix t, open o, close c FROM bars WHERE instrument=? AND event_unix < ? ORDER BY t",
                              con, params=(f"{coin}-USD-SPOT", CUT))
    finally:
        con.close()
    a["day"] = pd.to_datetime(a["t"] // 86400 * 86400, unit="s")
    g = a.groupby("day").agg(o=("o", "first"), c=("c", "last"), n=("t", "size"))
    return g[g["n"] >= 280][["o", "c"]]            # complete-enough UTC days only


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def signals(data: dict[str, pd.DataFrame], days: pd.DatetimeIndex) -> dict[str, pd.DataFrame]:
    """on[d, coin] decided at the close of day d (True = hold on day d+1)."""
    C = pd.DataFrame({k: v["c"] for k, v in data.items()}).reindex(days)
    avail = pd.DataFrame({k: v["c"].reindex(days).notna().cumsum() >= 50 for k, v in data.items()}) & C.notna()
    e50 = pd.DataFrame({k: ema(v["c"], 50).reindex(days) for k, v in data.items()})
    e20 = pd.DataFrame({k: ema(v["c"], 20).reindex(days) for k, v in data.items()})
    above50 = (C > e50) & avail
    btc = (C["BTC"] > e50["BTC"]).fillna(False)
    gate = pd.DataFrame({k: btc for k in C.columns})
    return {
        "BH": avail,
        "T1": above50,
        "T2": above50 & gate,
        "T3": above50 & (C > e20) & gate,
        "T4": avail & gate,
        "_avail": avail,
    }


def simulate(data: dict[str, pd.DataFrame], days: pd.DatetimeIndex, on: pd.DataFrame, avail: pd.DataFrame) -> dict:
    O = pd.DataFrame({k: v["o"] for k, v in data.items()}).reindex(days).ffill()
    C = pd.DataFrame({k: v["c"] for k, v in data.items()}).reindex(days).ffill()
    coins = list(C.columns)
    units = np.zeros(len(coins))
    cash = 1.0
    eq = np.full(len(days), np.nan)
    trades = 0
    costs = 0.0
    exposure = np.zeros(len(days))
    prev_on = np.zeros(len(coins), dtype=bool)
    hs = np.array([FEE + HALF_SPREAD.get(c, 0.004) for c in coins])
    for d in range(len(days)):
        if d > 0:
            sig = on.iloc[d - 1].to_numpy(dtype=bool).copy()
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
    return {"equity": pd.Series(eq, index=days), "trades": trades, "costs": costs, "exposure": pd.Series(exposure, index=days)}


def metrics(eq: pd.Series, exp: pd.Series) -> dict:
    eq = eq.dropna()
    if len(eq) < 30:
        return {}
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    tot = eq.iloc[-1] / eq.iloc[0] - 1
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else float("nan")
    dd = float((1 - eq / eq.cummax()).max())
    fresh = []
    for s in pd.date_range(eq.index[0].normalize(), eq.index[-1], freq="QS"):
        e = s + pd.DateOffset(years=1)
        a, b = eq[eq.index >= s], eq[eq.index <= e]
        if len(a) and b.index[-1] >= e - pd.Timedelta(days=3) and a.index[0] <= s + pd.Timedelta(days=5):
            fresh.append((s.strftime("%Y-%m"), round(100 * (b.iloc[-1] / a.iloc[0] - 1), 1)))
    r = eq.pct_change().dropna()
    return {"total_return_pct": round(100 * tot, 1), "cagr_pct": round(100 * cagr, 1), "max_dd_pct": round(100 * dd, 1),
            "mar": round(cagr / dd, 3) if dd > 0 else None, "sharpe_daily": round(float(r.mean() / r.std() * np.sqrt(365)), 2) if r.std() > 0 else None,
            "worst_12m": min(fresh, key=lambda x: x[1]) if fresh else None,
            "median_12m_pct": float(np.median([f[1] for f in fresh])) if fresh else None,
            "time_in_market_pct": round(100 * float(exp.loc[eq.index].mean()), 1)}


def run(db: str, out: Path) -> dict:
    data = {c: daily(db, c) for c in COINS}
    data = {k: v for k, v in data.items() if len(v)}
    days = pd.date_range(min(v.index.min() for v in data.values()), max(v.index.max() for v in data.values()), freq="D")
    sig = signals(data, days)
    rep: dict = {"version": "portfolio.trend.v1", "coins": list(data), "first_day": str(days[0].date()), "last_day": str(days[-1].date()),
                 "costs": "NDAX market: 0.20% fee + half-spread per trade", "strategies": {}}
    curves = {}
    for s in STRATS:
        sim = simulate(data, days, sig[s], sig["_avail"])
        eq, exp = sim["equity"], sim["exposure"]
        start = eq.index[eq.index >= eq.index[0] + pd.Timedelta(days=50)][0]   # after the 50-day warm-up
        eq = eq[eq.index >= start]
        curves[s] = eq
        disc, conf = eq[eq.index < DISC_END], eq[eq.index >= DISC_END]
        crisis = {}
        for k, (a, b) in CRISES.items():
            w = eq[(eq.index >= pd.Timestamp(a) - pd.Timedelta(days=1)) & (eq.index <= pd.Timestamp(b))]
            crisis[k] = round(100 * (w.iloc[-1] / w.iloc[0] - 1), 1) if len(w) > 1 else None
        rep["strategies"][s] = {"ALL": metrics(eq, exp), "DISCOVERY": metrics(disc, exp), "CONFIRM": metrics(conf, exp),
                                "trades": sim["trades"], "costs_paid_pct_of_start": round(100 * sim["costs"], 2), "crisis_pct": crisis}
    bh = rep["strategies"]["BH"]
    for s in STRATS[1:]:
        x = rep["strategies"][s]
        checks = {}
        for sp in ("DISCOVERY", "CONFIRM"):
            a, b = x[sp], bh[sp]
            checks[sp] = {"return>0": a["total_return_pct"] > 0, "dd<BH": a["max_dd_pct"] < b["max_dd_pct"],
                          "mar>BH": (a["mar"] or -9) > (b["mar"] or -9)}
        x["checks"] = checks
        x["PASS"] = all(all(v.values()) for v in checks.values())
    pd.DataFrame(curves).to_csv(out / "equity_curves.csv")
    (out / "review4_report.json").write_text(json.dumps(rep, indent=1, default=str))
    return rep


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run"])
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(os.path.expanduser(a.out))
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    r = run(a.db, out)
    for s, x in r["strategies"].items():
        print(s, "PASS" if x.get("PASS") else ("" if s == "BH" else "fail"), json.dumps({k: x[k] for k in ("DISCOVERY", "CONFIRM", "trades", "costs_paid_pct_of_start", "crisis_pct")}))
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
