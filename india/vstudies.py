"""Event studies (dev 2007-2017, validation 2018-2023). Events come with their exchange broadcast time, so the reaction day is known exactly.

  python -m india.vstudies v01     quarterly results: the reaction day, the drift after it, and what holding through results costs (exit before results?)

Reaction day (day 0): a filing broadcast before 15:30 IST reacts that session; after 15:30, the next session. Abnormal return = stock close-to-close minus Nifty 50.
Drift = abnormal return from the close of day 0 to the close of day 20, signed by the day-0 reaction (positive = continuation).
Universe: companies in the 500 most liquid on the day before the event (lab universe), one event per company and period (first broadcast).
"""
from __future__ import annotations

import glob
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import paths, registry

SPLIT = 2018


def _stat(x: pd.Series) -> tuple[float, float, int]:
    x = x.dropna()
    if len(x) < 3:
        return float("nan"), float("nan"), int(len(x))
    se = x.std(ddof=1) / math.sqrt(len(x))
    return float(x.mean()), float(x.mean() / se) if se else float("nan"), int(len(x))


def _q(df: pd.DataFrame, col: str) -> tuple[float, float, int]:
    return _stat(df.groupby(df["day0"].dt.to_period("Q"))[col].mean())


def events() -> pd.DataFrame:
    rows = []
    for fp in glob.glob(str(paths.bronze("results_index") / "*" / "*.json")):
        for x in json.loads(Path(fp).read_text()):
            rows.append({"isin": x.get("isin"), "symbol": x.get("symbol"), "broadcast": x.get("broadCastDate"), "period": x.get("period"), "to": x.get("toDate"),
                         "consolidated": x.get("consolidated")})
    e = pd.DataFrame(rows)
    e["at"] = pd.to_datetime(e["broadcast"], format="%d-%b-%Y %H:%M:%S", errors="coerce")
    e = e.dropna(subset=["at", "isin"])
    e = e[(e["at"] < "2024-01-01") & (e["period"] == "Quarterly")]
    e = e.sort_values("at").drop_duplicates(["isin", "to"], keep="first")  # first broadcast per company and period
    names = pd.read_parquet(paths.data_dir() / "silver/security_master/names.parquet", columns=["isin", "entity"]).drop_duplicates("isin")
    e = e.merge(names, on="isin", how="left")
    e["sid"] = e["entity"].fillna(e["isin"])
    return e


def v01() -> dict:
    e = events()
    bars = pd.read_parquet(paths.gold() / "bars" / "adj_daily.parquet", columns=["sid", "date", "c"])
    bars["date"] = pd.to_datetime(bars["date"])
    uni = pd.read_parquet(paths.gold() / "universe" / "u_liq_in.parquet", columns=["sid", "date", "top500"])
    uni["date"] = pd.to_datetime(uni["date"])
    ix = pd.read_parquet(paths.data_dir() / "silver/kite_index/day/day.parquet")
    nifty = ix[ix["index_name"] == "NIFTY 50"].assign(date=lambda d: pd.to_datetime(d["date"])).set_index("date")["close"].sort_index()
    nret = nifty.pct_change()
    sessions = pd.DatetimeIndex(sorted(bars["date"].unique()))
    by = {s: g.set_index("date")["c"] for s, g in bars.groupby("sid")}
    top = set(zip(uni.loc[uni["top500"], "sid"], uni.loc[uni["top500"], "date"]))
    rows = []
    for r in e.itertuples():
        c = by.get(r.sid)
        if c is None:
            continue
        cut = r.at.normalize() + pd.Timedelta(hours=15, minutes=30)
        i0 = sessions.searchsorted(r.at.normalize()) if r.at < cut else sessions.searchsorted(r.at.normalize() + pd.Timedelta(days=1))
        if i0 < 21 or i0 + 20 >= len(sessions):
            continue
        d0, dprev = sessions[i0], sessions[i0 - 1]
        if (r.sid, dprev) not in top or d0 not in c.index or dprev not in c.index:
            continue
        d20 = sessions[i0 + 20]
        if d20 not in c.index or d0 not in nret.index or d20 not in nifty.index:
            continue
        ret0 = c[d0] / c[dprev] - 1
        if abs(ret0) > 0.5:
            continue  # artefact guard, counted with the data-hygiene rule
        ab0 = ret0 - nret.get(d0, np.nan)
        drift = (c[d20] / c[d0] - 1) - (nifty[d20] / nifty[d0] - 1)
        # a normal day for the same stock: 30 sessions before, as the noise yardstick
        dn, dnp = sessions[i0 - 21], sessions[i0 - 22]
        normal = (c[dn] / c[dnp] - 1) - nret.get(dn, np.nan) if dn in c.index and dnp in c.index else np.nan
        rows.append({"sid": r.sid, "symbol": r.symbol, "at": r.at, "day0": d0, "ab0": ab0, "drift20": drift, "abs_ab0": abs(ab0), "abs_normal": abs(normal) if normal == normal else np.nan})
    df = pd.DataFrame(rows)
    df.to_parquet(paths.gold() / "studies" / "V01_results_events.parquet")
    df["y"] = df["day0"].dt.year
    df["cont"] = np.sign(df["ab0"]) * df["drift20"]
    df["excess_abs"] = df["abs_ab0"] - df["abs_normal"]
    reg = registry.register("V01", family="events", title="Quarterly results: reaction day, 20-day drift, and the cost of holding through results",
                            hypothesis="(a) the 20-day abnormal drift continues the day-0 reaction; (b) results days move more than normal days (holding through results adds risk)",
                            variants=["drift_after_up", "drift_after_down", "drift_signed", "abs_reaction_excess"], note="top-500 companies; Nifty 50 as the market; quarter blocks")
    out = {}
    tests = {"drift_after_up": (df[df["ab0"] > 0.02], "drift20", 1), "drift_after_down": (df[df["ab0"] < -0.02], "drift20", -1), "drift_signed": (df, "cont", 1),
             "abs_reaction_excess": (df, "excess_abs", 1)}
    for name, (x, col, ex) in tests.items():
        dev, val = _q(x[x["y"] < SPLIT], col), _q(x[x["y"] >= SPLIT], col)
        line = registry.record(reg, name, dev, val, extra={"n": int(len(x)), "median_abs_ab0": float(df["abs_ab0"].median()), "median_abs_normal": float(df["abs_normal"].median())}, expect=ex)
        out[name] = line["verdict"]
        print(f"V01 {name:20s} {line['verdict']:12s} dev {dev[0]*100:+.2f}% t {dev[1]:+.1f} q{dev[2]} | val {val[0]*100:+.2f}% t {val[1]:+.1f} q{val[2]} | n {len(x)}", flush=True)
    print(f"V01 events {len(df)}; median |day-0 abnormal| {df['abs_ab0'].median()*100:.2f}% vs a normal day {df['abs_normal'].median()*100:.2f}%; "
          f"5th/95th percentile day-0 abnormal {df['ab0'].quantile(0.05)*100:.1f}% / {df['ab0'].quantile(0.95)*100:.1f}%", flush=True)
    registry.mirror_to_catalog()
    return out


if __name__ == "__main__":
    paths.ensure()
    v01()
