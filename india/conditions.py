"""Named conditions, defined once, used by the research (india.studies2) and by the live baseline book (india.paper / india.filters), so a filter that is
tested historically is the same filter that is sliced on the paper records. Each condition is known at the close of the signal day; nothing later.

Stock conditions read the features row of the signal day (gold/features in research, the decision journal in paper).
Market conditions read the daily context table built here: breadth of the 500 most liquid stocks, Nifty 50 and India VIX against their averages,
small caps against large caps, and global markets from FRED. FRED rows are US dates: a US close is used only from the next Indian session on
(as-of join on the day before), so no US number is known before it existed. Thresholds are round numbers fixed before any result was read.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from india import paths

# name -> (kind, description, expect: +1 the 'on' side should earn more, -1 less, 0 no stated direction, rule)
STOCK = {
    "ext_ret60_gt50": ("stock", "saturation: up more than 50% in 60 sessions (M-03/M-04)", -1, lambda x: x["ret_60"] > 0.5),
    "ext_sma50_gt20": ("stock", "saturation: close more than 20% above the 50-day average", -1, lambda x: x["dist_sma50"] > 0.2),
    "ext_ret20_gt25": ("stock", "saturation: up more than 25% in 20 sessions", -1, lambda x: x["ret_20"] > 0.25),
    "decline_ret60_lt_m30": ("stock", "saturation after a decline: down more than 30% in 60 sessions (M-13)", 1, lambda x: x["ret_60"] < -0.3),
    "pull_shallow": ("stock", "pullback 5-8% under the 20-day average (shallow), for PULL entries", 1, lambda x: (x["dist_sma20"] >= -0.08) & (x["dist_sma20"] < -0.05)),
    "pull_deep": ("stock", "pullback more than 12% under the 20-day average", -1, lambda x: x["dist_sma20"] < -0.12),
    "pull_above50": ("stock", "pullback holding above the 50-day average (M-05, TWT-H10)", 1, lambda x: x["dist_sma50"] > 0),
    "pull_lowvol": ("stock", "pullback on low volume: volume under its 20-day average (TWT-H18/19)", 1, lambda x: x["vol_ratio20"] < 1.0),
    "pull_healthy": ("stock", "healthy pullback: shallow-to-moderate (5-12%), above the 50-day, low volume", 1,
                     lambda x: (x["dist_sma20"] >= -0.12) & (x["dist_sma50"] > 0) & (x["vol_ratio20"] < 1.0)),
    "vol_heat2": ("stock", "volume heat: volume above 2x its 20-day average (C02, crypto H1)", 0, lambda x: x["vol_ratio20"] > 2.0),
    "deliv_high": ("stock", "delivery share above 60% (buyers taking delivery, M-10)", 1, lambda x: x["deliv_pct"] > 60),
    "rv20_high": ("stock", "own 20-day volatility in the top fifth of the day's universe", 0, None),  # cross-sectional: built in apply_stock
}
MARKET = {
    "breadth_lt30": ("market", "washout: under 30% of the liquid universe above its 200-day (TWT-H01, H30-33)", -1, lambda c: c["breadth200"] < 0.3),
    "breadth_lt40": ("market", "weak breadth: under 40% above the 200-day", -1, lambda c: c["breadth200"] < 0.4),
    "breadth_thrust": ("market", "breadth thrust: share above the 200-day up 20 points in 10 sessions", 1, lambda c: c["breadth200"] - c["breadth200"].shift(10) > 0.2),
    "nifty_gt50d": ("market", "Nifty 50 above its 50-day average", 1, lambda c: c["nifty_vs_sma50"] > 0),
    "nifty_gt200d": ("market", "Nifty 50 above its 200-day average", 1, lambda c: c["nifty_vs_sma200"] > 0),
    "vix_gt20": ("market", "India VIX above 20 (C05)", 0, lambda c: c["vix"] > 20),
    "vix_rising": ("market", "India VIX above its 50-day average", 0, lambda c: c["vix_vs_sma50"] > 0),
    "small_lead": ("market", "small caps leading: Nifty Smallcap 100 / Nifty 100 above its 50-day average (C07, TWT-H13/14)", 1, lambda c: c["small_ratio_vs_sma50"] > 0),
    "usdinr_rising": ("market", "rupee weakening: USDINR above its 50-day average (C09, TWT-H42)", -1, lambda c: c["usdinr_vs_sma50"] > 0),
    "brent_rising": ("market", "Brent above its 50-day average (C09, TWT-H44)", -1, lambda c: c["brent_vs_sma50"] > 0),
    "nasdaq_gt200d": ("market", "Nasdaq above its 200-day average, previous US close (C09, TWT-H45)", 1, lambda c: c["nasdaq_vs_sma200"] > 0),
    "us10y_up_60d": ("market", "US 10-year yield up over 60 sessions (C09, TWT-H47)", -1, lambda c: c["us10y_chg60"] > 0),
    "nifty_down2": ("market", "Nifty 50 fell more than 2% on the signal day (C01: what follows a shock day)", 0, lambda c: c["nifty_ret1"] < -0.02),
    "nifty_up2": ("market", "Nifty 50 rose more than 2% on the signal day", 0, lambda c: c["nifty_ret1"] > 0.02),
    "nifty_vol_high": ("market", "Nifty 20-day volatility above its own 80th percentile so far (expanding, no look-ahead) (C01 volatility regime)", 0,
                       lambda c: c["nifty_rv20"] > c["nifty_rv20_p80"]),
}
ALL = {**STOCK, **MARKET}


def _vs(s: pd.Series, n: int) -> pd.Series:
    return s / s.rolling(n, min_periods=n).mean() - 1


def context_table(features: pd.DataFrame, include_sealed: bool = False) -> pd.DataFrame:
    """Daily market context for research dates (silver only, to 2023). `features` is gold/features (date, liq_rank, dist_sma200)."""
    f = features[features["liq_rank"] <= 500]
    c = f.groupby("date")["dist_sma200"].apply(lambda x: float((x > 0).mean())).rename("breadth200").to_frame()
    ix = pd.read_parquet(paths.data_dir() / "silver/kite_index/day/day.parquet")
    ix["date"] = pd.to_datetime(ix["date"])
    piv = ix.pivot_table(index="date", columns="index_name", values="close", aggfunc="last").sort_index()
    out = pd.DataFrame(index=piv.index)
    out["nifty_vs_sma50"] = _vs(piv["NIFTY 50"], 50)
    out["nifty_vs_sma200"] = _vs(piv["NIFTY 50"], 200)
    out["vix"] = piv.get("INDIA VIX")
    out["vix_vs_sma50"] = _vs(piv["INDIA VIX"], 50) if "INDIA VIX" in piv else np.nan
    out["small_ratio_vs_sma50"] = _vs(piv["NIFTY SMLCAP 100"] / piv["NIFTY 100"], 50)
    r1 = piv["NIFTY 50"].pct_change()
    out["nifty_ret1"] = r1
    out["nifty_rv20"] = r1.rolling(20, min_periods=20).std()
    out["nifty_rv20_p80"] = out["nifty_rv20"].expanding(min_periods=250).quantile(0.8)
    c.index = pd.to_datetime(c.index)
    out = c.join(out, how="left")
    m = pd.read_parquet(paths.data_dir() / "silver/macro/macro.parquet")
    m["date"] = pd.to_datetime(m["date"])
    mp = m.pivot_table(index="date", columns="series", values="value", aggfunc="last").sort_index()
    mac = pd.DataFrame(index=mp.index)
    mac["usdinr_vs_sma50"] = _vs(mp["DEXINUS"].dropna(), 50)
    mac["brent_vs_sma50"] = _vs(mp["DCOILBRENTEU"].dropna(), 50)
    mac["nasdaq_vs_sma200"] = _vs(mp["NASDAQCOM"].dropna(), 200)
    g = mp["DGS10"].dropna()
    mac["us10y_chg60"] = g - g.shift(60)
    mac = mac.sort_index()
    # as-of join on the day before: a US close dated d is first usable on the Indian session after d
    idx = pd.DataFrame({"date": out.index, "known_by": out.index - pd.Timedelta(days=1)}).sort_values("known_by")
    mac_r = mac.reset_index().rename(columns={"date": "mdate"}).sort_values("mdate")
    j = pd.merge_asof(idx, mac_r, left_on="known_by", right_on="mdate", direction="backward").set_index("date").drop(columns=["known_by", "mdate"])
    out = out.join(j)
    out.index.name = "date"
    return out


def apply_stock(x: pd.DataFrame) -> pd.DataFrame:
    """Boolean columns cond_<name> for the stock conditions (NaN where an input is missing)."""
    out = pd.DataFrame(index=x.index)
    for name, (_, _, _, rule) in STOCK.items():
        if rule is None:
            continue
        try:
            out["cond_" + name] = rule(x).astype("float")
        except KeyError:
            out["cond_" + name] = np.nan  # input not recorded for these rows (e.g. the paper journal has no 60-day return): missing, not False
    if "rv20" in x.columns and "date" in x.columns:
        q = x.groupby("date")["rv20"].transform(lambda s: s.rank(pct=True))
        out["cond_rv20_high"] = (q > 0.8).astype(float).where(x["rv20"].notna())
    for name in STOCK:
        col = "cond_" + name
        if col in out:
            src = {"ext_ret60_gt50": "ret_60", "decline_ret60_lt_m30": "ret_60", "ext_sma50_gt20": "dist_sma50", "ext_ret20_gt25": "ret_20", "vol_heat2": "vol_ratio20",
                   "deliv_high": "deliv_pct", "pull_lowvol": "vol_ratio20", "pull_above50": "dist_sma50"}.get(name)
            if src and src in x.columns:
                out[col] = out[col].where(x[src].notna())
    return out


def apply_market(ctx: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(index=ctx.index)
    for name, (_, _, _, rule) in MARKET.items():
        try:
            out["cond_" + name] = rule(ctx).astype(float)
        except KeyError:
            out["cond_" + name] = np.nan  # input not available: the condition is missing, never guessed
    # a comparison against NaN is False in pandas: put the missing back from the inputs
    need = {"breadth_lt30": "breadth200", "breadth_lt40": "breadth200", "breadth_thrust": "breadth200", "nifty_gt50d": "nifty_vs_sma50", "nifty_gt200d": "nifty_vs_sma200",
            "vix_gt20": "vix", "vix_rising": "vix_vs_sma50", "small_lead": "small_ratio_vs_sma50", "usdinr_rising": "usdinr_vs_sma50", "brent_rising": "brent_vs_sma50",
            "nasdaq_gt200d": "nasdaq_vs_sma200", "us10y_up_60d": "us10y_chg60", "nifty_down2": "nifty_ret1", "nifty_up2": "nifty_ret1", "nifty_vol_high": "nifty_rv20_p80"}
    for name, col in need.items():
        if col in ctx.columns:
            out["cond_" + name] = out["cond_" + name].where(ctx[col].notna())
    return out
