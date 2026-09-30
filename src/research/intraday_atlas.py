"""Intraday probability atlas: what historically happened after each setup, by market condition.

    python -m src.research.intraday_atlas build --db LAB5 --ctx DIR_WITH_context_COIN.pkl --out DIR

For every 15-minute scan where a setup fired (E1-E8, plus an ANY baseline every 8th scan), entry = the open of
the next 5m bar. Outcomes on 5m bars (stop first when both levels are touched in one bar):
  * brackets: P(target first), P(stop first), P(neither by the time limit), gross and NDAX-net expectancy
  * ranges:   best move up / worst move down / close move at 1h, 4h, 24h (10th, 50th, 90th percentiles)
Grouped by setup, and by setup x our market bias (S1) x BTC's bias, separately for DISCOVERY (<2024) and
CONFIRM (2024 - Jul 2026). HOLDOUT is never loaded. Information only: nothing here trades.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

try:  # the research stack; the live Explorer only needs lookup(), which is pure Python
    import numpy as np
    import pandas as pd

    from src.research import explorer_replay as xr
except ImportError:  # pragma: no cover
    np = pd = xr = None

try:
    from numba import njit
except ImportError:  # tests without numba
    def njit(*a, **k):
        if a and callable(a[0]):
            return a[0]
        return lambda f: f

COINS = ["BTC", "ETH", "SOL", "ADA", "DOGE", "AVAX", "BCH", "LINK", "LTC", "XRP"]
HALF_SPREAD = {"BTC": 0.00178, "ETH": 0.00084, "SOL": 0.00289, "ADA": 0.00273, "DOGE": 0.00307,
               "AVAX": 0.00370, "BCH": 0.00400, "LINK": 0.00341, "LTC": 0.00334, "XRP": 0.00251}
FEE = 0.0020
DISC_END = 1704067200
BRACKETS = {  # name: (target, stop, bars of 5m)
    "0.5/0.5_1h": (0.005, 0.005, 12),
    "1/1_4h": (0.010, 0.010, 48),
    "1.5/1_4h": (0.015, 0.010, 48),
    "2/1_24h": (0.020, 0.010, 288),
    "3/1.5_24h": (0.030, 0.015, 288),
}
RANGES = {"1h": 12, "4h": 48, "24h": 288}
SETUPS = ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8", "ANY")
MIN_N = 100


@njit(cache=True)
def _bracket(o, h, lo, c, J, tgt, stp, H):
    """Per entry index j (bought at o[j]): +1 target first, -1 stop first, 0 neither; and the result return."""
    m = len(J)
    code = np.zeros(m, np.int8)
    res = np.full(m, np.nan)
    n = len(c)
    for q in range(m):
        j = J[q]
        if j < 0 or j + H > n:
            continue
        P = o[j]
        T, S = P * (1 + tgt), P * (1 - stp)
        done = False
        for k in range(j, j + H):
            if k > j and o[k] <= S:
                code[q], res[q], done = -1, o[k] / P - 1, True
                break
            if k > j and o[k] >= T:
                code[q], res[q], done = 1, o[k] / P - 1, True
                break
            if lo[k] <= S:
                code[q], res[q], done = -1, -stp, True
                break
            if h[k] >= T:
                code[q], res[q], done = 1, tgt, True
                break
        if not done:
            res[q] = c[j + H - 1] / P - 1
    return code, res


def _ranges(o, h, lo, c, J, H):
    n = len(c)
    ok = (J >= 0) & (J + H <= n)
    hs, ls = pd.Series(h), pd.Series(lo)
    mx = hs[::-1].rolling(H, min_periods=H).max()[::-1].to_numpy()
    mn = ls[::-1].rolling(H, min_periods=H).min()[::-1].to_numpy()
    Jc = np.clip(J, 0, n - 1)
    P = o[Jc]
    up = np.where(ok, mx[Jc] / P - 1, np.nan)
    dn = np.where(ok, mn[Jc] / P - 1, np.nan)
    cl = np.where(ok, c[np.clip(J + H - 1, 0, n - 1)] / P - 1, np.nan)
    return up, dn, cl


def sightings(db: str, ctx_dir: Path, coin: str) -> pd.DataFrame:
    b = xr.load_5m(db, coin)
    t = np.array([x[0] for x in b], dtype=np.int64)
    o, h, lo, c = (np.array([x[k] for x in b]) for k in (1, 2, 3, 4))
    cx = pd.read_pickle(ctx_dir / f"context_{coin}.pkl")
    rows = []
    fired = cx["setups"].fillna("").str.split(",")
    e6 = cx["rsi15"] < 30
    e7 = (cx["rsi1h"] < 40) & (cx["trend_4h"] == "DOWN")
    e8 = (~cx["daily_above_ema50"].astype(bool)) & (cx["roc_pct"].fillna(1) <= 0.30)
    anyb = (np.arange(len(cx)) % 8) == 0
    for i, (T, f) in enumerate(zip(cx["T"].to_numpy(), fired)):
        names = [x for x in f if x] + (["E6"] if e6.iat[i] else []) + (["E7"] if e7.iat[i] else []) + (["E8"] if e8.iat[i] else []) + (["ANY"] if anyb[i] else [])
        for s in names:
            rows.append((i, s))
    if not rows:
        return pd.DataFrame()
    idx = np.array([r[0] for r in rows])
    df = cx.iloc[idx][["T", "S1", "btc_S1"]].reset_index(drop=True)
    df["setup"] = [r[1] for r in rows]
    df["coin"] = coin
    J = np.searchsorted(t, df["T"].to_numpy())           # the 5m bar opening at the scan close
    J = np.where((J < len(t)) & (t[np.minimum(J, len(t) - 1)] == df["T"].to_numpy()), J, -1)
    for name, (tg, sp, H) in BRACKETS.items():
        code, res = _bracket(o, h, lo, c, J, tg, sp, H)
        df[f"b_{name}_code"] = code
        df[f"b_{name}_ret"] = res
    for lab, H in RANGES.items():
        up, dn, cl = _ranges(o, h, lo, c, J, H)
        df[f"up_{lab}"], df[f"dn_{lab}"], df[f"cl_{lab}"] = up, dn, cl
    df["cost_rt"] = 2 * (FEE + HALF_SPREAD.get(coin, 0.004))      # market in, market out (worst case)
    df["split"] = np.where(df["T"] < DISC_END, "DISCOVERY", "CONFIRM")
    return df


def summarize(g: pd.DataFrame) -> dict:
    out = {"n": int(len(g))}
    for name in BRACKETS:
        ok = g[f"b_{name}_ret"].notna()
        code, ret = g.loc[ok, f"b_{name}_code"], g.loc[ok, f"b_{name}_ret"]
        if not len(ret):
            continue
        out[name] = {"p_target": round(float((code == 1).mean()), 3), "p_stop": round(float((code == -1).mean()), 3),
                     "p_neither": round(float((code == 0).mean()), 3), "gross_pct": round(100 * float(ret.mean()), 3),
                     "net_pct": round(100 * float((ret - g.loc[ok, "cost_rt"]).mean()), 3)}
    for lab in RANGES:
        for k in ("up", "dn", "cl"):
            x = g[f"{k}_{lab}"].dropna()
            if len(x):
                out[f"{k}_{lab}_p10_p50_p90"] = [round(100 * float(x.quantile(q)), 2) for q in (0.1, 0.5, 0.9)]
    return out


def build(db: str, ctx_dir: Path, out: Path) -> dict:
    parts = [sightings(db, ctx_dir, c) for c in COINS if (ctx_dir / f"context_{c}.pkl").exists()]
    df = pd.concat([p for p in parts if len(p)], ignore_index=True)
    atlas: dict = {"version": "intraday.atlas.v1", "entry": "market at the next 5m open", "costs": "NDAX market both sides (worst case)",
                   "brackets": {k: {"target_pct": 100 * v[0], "stop_pct": 100 * v[1], "hours": v[2] / 12} for k, v in BRACKETS.items()},
                   "min_n": MIN_N, "setups": {}, "contexts": {}}
    for (s, sp), g in df.groupby(["setup", "split"]):
        atlas["setups"].setdefault(s, {})[sp] = summarize(g)
    for (s, s1, b1, sp), g in df.groupby(["setup", "S1", "btc_S1", "split"]):
        if len(g) >= MIN_N:
            atlas["contexts"].setdefault(f"{s}|{s1}|{b1}", {})[sp] = summarize(g)
    # stability flag: the same bracket has positive NET expectancy in both periods (the only thing worth an alert)
    for key, v in list(atlas["contexts"].items()) + [(k, v) for k, v in atlas["setups"].items()]:
        good = []
        for name in BRACKETS:
            d, c = v.get("DISCOVERY", {}).get(name), v.get("CONFIRM", {}).get(name)
            if d and c and d["net_pct"] > 0 and c["net_pct"] > 0 and v["DISCOVERY"]["n"] >= MIN_N and v["CONFIRM"]["n"] >= MIN_N:
                good.append(name)
        v["stable_positive_after_costs"] = good
    (out / "intraday_atlas.json").write_text(json.dumps(atlas, indent=1))
    df[["T", "coin", "setup", "S1", "btc_S1", "split"]].to_pickle(out / "sightings_index.pkl")
    return atlas


def lookup(atlas: dict, setup: str, s1: str | None, btc_s1: str | None) -> dict | None:
    """The most specific atlas entry for a live sighting (context first, then the setup overall)."""
    v = atlas.get("contexts", {}).get(f"{setup}|{s1}|{btc_s1}")
    level = "context"
    if not v or "CONFIRM" not in v:
        v, level = atlas.get("setups", {}).get(setup), "setup"
    if not v:
        return None
    return {"level": level, "recent": v.get("CONFIRM") or v.get("DISCOVERY"), "stable_positive_after_costs": v.get("stable_positive_after_costs", [])}


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build"])
    ap.add_argument("--db", required=True)
    ap.add_argument("--ctx", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    out = Path(os.path.expanduser(a.out))
    out.mkdir(parents=True, exist_ok=True)
    at = build(a.db, Path(os.path.expanduser(a.ctx)), out)
    stable = {k: v["stable_positive_after_costs"] for k, v in list(at["contexts"].items()) + list(at["setups"].items()) if v["stable_positive_after_costs"]}
    print(json.dumps({"setups": {k: {sp: {"n": x["n"], "1/1_4h": x.get("1/1_4h")} for sp, x in v.items() if isinstance(x, dict)} for k, v in at["setups"].items()},
                      "contexts": len(at["contexts"]), "stable_positive_after_costs": stable}, indent=1))


if __name__ == "__main__":
    main()
