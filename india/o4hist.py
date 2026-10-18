"""F05: O-04 reconstructed on history (estimated, to be calibrated against the recorder before it is trusted).

  python -m india.o4hist run        every index expiry day 2015-2023 with index minutes, all 8 O-04 variants plus a hold-to-15:15 reference

How the option prices are made (labelled SYNTHETIC everywhere): the real index 1-minute path (silver/kite_index/minute) drives Black-76 prices for the
at-the-money call and put of the expiring contract. Volatility = the previous session's settlement-implied volatility of that strike area for that expiry
(silver/fo_greeks, known before the expiry day opens), held flat through the afternoon; forward = spot (same-day expiry, carry negligible); time to expiry
= minutes left to 15:30 over 94,500 trading minutes a year. Intraday volatility moves, the smile and real bid-ask are NOT in this model: that is what the
recorder calibration (R01) measures. The rules are the live paper book's own code (india.optpaper.sim_o4), so the historical and live versions cannot drift.
Lot size: the futures lot estimate for that index on that day (value / contracts / price), rounded. Statistics: one trade per expiry day, intraday, so trades
do not overlap and the t-statistic is across days.
"""
from __future__ import annotations

import json
import math
import sys

import duckdb
import numpy as np
import pandas as pd

from india import greeks, optpaper, paths, registry

INDEX = optpaper.INDEX
STEP = optpaper.STEP
MIN_PER_YEAR = 94_500.0
SPLIT = 2018


def _minutes() -> pd.DataFrame:
    files = [str(p) for p in (paths.data_dir() / "silver/kite_index/minute").glob("year=*/part.parquet")]
    con = duckdb.connect()
    df = con.execute(f"select index_name, ts, open, high, low, close from read_parquet({files!r}) where list_contains(?, index_name) and hour(ts) >= 12",
                     [list(INDEX.values())]).df()
    con.close()
    df["ts"] = pd.to_datetime(df["ts"])
    return df


def _iv_prev(sym: str, day: pd.Timestamp, spot: float, g: pd.DataFrame) -> float | None:
    x = g[(g["symbol"] == sym) & (g["expiry"] == day) & (g["date"] < day) & g["iv"].notna() & (g["flag"] == "ok")]
    if x.empty:
        return None
    last = x["date"].max()
    x = x[x["date"] == last]
    x = x.iloc[(x["strike"] - spot).abs().argsort()[:4]]
    return float(x["iv"].median())


def _lots() -> pd.DataFrame:
    files = [str(p) for p in (paths.data_dir() / "silver/fo_bhavcopy").glob("year=*/part.parquet")]
    con = duckdb.connect()
    df = con.execute(f"select date, symbol, median(lot_est) as lot from read_parquet({files!r}, union_by_name=true) where instrument = 'FUTIDX' and lot_est > 0 "
                     f"and list_contains(?, symbol) group by 1, 2", [list(INDEX)]).df()
    con.close()
    df["date"] = pd.to_datetime(df["date"])
    return df


def _frame(spot: pd.DataFrame, day: pd.Timestamp, K: float, iv: float, call: bool) -> pd.DataFrame:
    close_t = day + pd.Timedelta(hours=15, minutes=30)
    t_open = ((close_t - spot.index).total_seconds() / 60.0).values
    t_close = t_open - 1.0
    F_o, F_c = spot["open"].values, spot["close"].values
    T_o = np.maximum(t_open, 0.5) / MIN_PER_YEAR
    T_c = np.maximum(t_close, 0.5) / MIN_PER_YEAR
    c = np.full(len(spot), call)
    po = greeks.black76(F_o, np.full(len(spot), K), T_o, np.full(len(spot), iv), c)[0]
    pc = greeks.black76(F_c, np.full(len(spot), K), T_c, np.full(len(spot), iv), c)[0]
    return pd.DataFrame({"open": np.maximum(po, 0.05), "close": np.maximum(pc, 0.05)}, index=spot.index)


def run() -> dict:
    cal = pd.read_parquet(paths.data_dir() / "silver/fo_calendar/expiries.parquet")
    cal = cal[(cal["instrument"] == "OPTIDX") & cal["symbol"].isin(list(INDEX))]
    cal["expiry"] = pd.to_datetime(cal["expiry"])
    cal = cal[(cal["expiry"] >= "2015-01-12") & (cal["expiry"] <= "2023-12-31")]
    mins = _minutes()
    gfiles = [str(p) for p in (paths.data_dir() / "silver/fo_greeks").glob("year=*/part.parquet")]
    g = duckdb.connect().execute(f"select date, symbol, expiry, strike, opt_type, iv, flag from read_parquet({gfiles!r}) where date >= '2015-01-01' and list_contains(?, symbol)",
                                 [list(INDEX)]).df()
    g["date"], g["expiry"] = pd.to_datetime(g["date"]), pd.to_datetime(g["expiry"])
    lots = _lots().set_index(["symbol", "date"])["lot"]
    reg = registry.register("F05-O04", family="options_intraday", title="O-04 expiry-day straddle reconstructed on index minutes (synthetic prices)",
                            hypothesis="O-04 (13:30 ATM straddle, opening-range break closes the loser, winner trailed, combined-premium stop) earns more than zero, and more than "
                                       "holding the same straddle to 15:15, net of costs and a half-spread, in dev (2015-2017) and validation (2018-2023).",
                            variants=[f"stop{v['stop']}_trail{v['trail']}_nb{v['nobreak']}" for v in optpaper.VARIANTS_O4] + [f"vs_hold|stop{v['stop']}_trail{v['trail']}_nb{v['nobreak']}" for v in optpaper.VARIANTS_O4],
                            note="synthetic Black-76 prices from the index path, previous-day IV held flat; one trade per expiry day: t across days; see india/o4hist.py")
    rows, skips = [], {}
    for r in cal.itertuples():
        day = r.expiry
        name = r.symbol
        sp = mins[(mins["index_name"] == INDEX[name]) & (mins["ts"].dt.normalize() == day)].set_index("ts").sort_index()
        if len(sp) < 150:
            skips["no_minutes"] = skips.get("no_minutes", 0) + 1
            continue
        s1329 = sp[(sp.index >= day + pd.Timedelta(hours=13, minutes=29)) & (sp.index < day + pd.Timedelta(hours=13, minutes=30))]
        if s1329.empty:
            skips["no_1329"] = skips.get("no_1329", 0) + 1
            continue
        K = round(float(s1329["close"].iloc[0]) / STEP[name]) * STEP[name]
        iv = _iv_prev(name, day, K, g)
        if iv is None or not (0.03 < iv < 1.5):
            skips["no_prev_iv"] = skips.get("no_prev_iv", 0) + 1
            continue
        lot = lots.get((name, day))
        if lot is None or not lot == lot:
            skips["no_lot"] = skips.get("no_lot", 0) + 1
            continue
        ce, pe = _frame(sp, day, K, iv, True), _frame(sp, day, K, iv, False)
        # the hold-to-15:15 reference: same entry, no stop (0% of paid can never be reached), a range that can never break
        hold = optpaper.sim_o4(name, day.strftime("%Y-%m-%d"), {"stop": 0.0, "trail": 1.0, "nobreak": "15:15"}, ce, pe, sp.assign(high=np.inf, low=-np.inf), int(lot))
        for v in optpaper.VARIANTS_O4:
            res = optpaper.sim_o4(name, day.strftime("%Y-%m-%d"), v, ce, pe, sp, int(lot))
            if res is None:
                continue
            res.update({"iv_prev": iv, "strike": K, "monthly": bool(r.is_monthly_last), "hold_net_ret": hold["net_ret_on_book"] if hold else None, "synthetic": True})
            rows.append(res)
    df = pd.DataFrame(rows)
    df.to_parquet(paths.gold() / "studies" / "F05-O04_trades.parquet")
    df["year"] = pd.to_datetime(df["day"]).dt.year
    out = {"trades": len(df), "skips": skips, "days": int(df["day"].nunique()) if len(df) else 0}
    for vname, g2 in df.groupby("variant"):
        st = {}
        for tag, col in (("abs", "net_ret_on_book"), ("vs_hold", None)):
            vals = g2[col] if col else g2["net_ret_on_book"] - g2["hold_net_ret"]
            per = {}
            for p, m in (("dev", g2["year"] < SPLIT), ("val", g2["year"] >= SPLIT)):
                x = vals[m].dropna()
                se = x.std(ddof=1) / math.sqrt(len(x)) if len(x) > 2 else float("nan")
                per[p] = (float(x.mean()) if len(x) else float("nan"), float(x.mean() / se) if se and se == se else float("nan"), int(len(x)))
            vn = vname if tag == "abs" else f"vs_hold|{vname}"
            extra = {"by_index": g2.groupby("index")["net_ret_on_book"].agg(["size", "mean"]).round(5).to_dict(orient="index"),
                     "worst_day": float(g2["net_ret_on_book"].min()), "share_broke": float(g2["broke"].notna().mean()), "exit_reasons": g2["exit_reason"].value_counts().to_dict()}
            line = registry.record(reg, vn, per["dev"], per["val"], extra=extra, expect=1)
            st[tag] = (per, line["verdict"])
            print(f"F05 {vn:42s} {line['verdict']:12s} dev {per['dev'][0]*100:+.3f}% t {per['dev'][1]:+.1f} n{per['dev'][2]} | val {per['val'][0]*100:+.3f}% t {per['val'][1]:+.1f} n{per['val'][2]}", flush=True)
        out[vname] = {k: v[1] for k, v in st.items()}
    registry.mirror_to_catalog()
    print(json.dumps({k: v for k, v in out.items() if k in ("trades", "skips", "days")}), flush=True)
    return out


if __name__ == "__main__":
    paths.ensure()
    run()
