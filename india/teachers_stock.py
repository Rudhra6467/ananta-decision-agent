"""Teacher claims on stocks, the index, sectors and the market's breadth (india/teachers.py runs them; Madhav, 25 Oct 2026: "extract all the
information that will be useful for Indian market and we will test all the needed strategies and keep their results").

Data: gold/features (adjusted daily bars and features of the liquid universe, to 2023-12-29) and silver/kite_index/day (Nifty, Bank Nifty, sector
indices, India VIX, to 2023), silver/macro for the dollar, crude and the Nasdaq (a US close is used from the next Indian session). Nothing sealed
is read. Development years 2000-2017 (index cards: from 2003, VIX cards: from 2009), validation 2018-2023, the same split as every India study.

Every test is one of two shapes, so no card picks its own statistics:
  split(on, off)   within a base set fixed by the claim, the mean outcome when the claim's condition holds minus when it does not, per calendar
                   quarter that has at least MIN_SIDE observations on each side; t across quarters (neighbouring days share overlapping holds,
                   quarters almost do not). The registry turns (dev mean, dev t, quarters) and (val ...) into the verdict at the family's strict bar.
  level(on)        the mean outcome of the signal set minus the mean of all base rows in the same quarter (the market's own drift that quarter).
Stock outcomes: buy at the next session's open, sell at the close h sessions later, net of the delivery round trip and the spread estimate for
the stock's liquidity rank. Index outcomes: from the next session's close to the close h sessions later (an index cannot be bought at the close
that produced the signal). Event signals keep one per stock per 10 sessions; state conditions are sampled every 5th session.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from india import costs, paths

SPLIT = 2018
MIN_SIDE = 5
H = (5, 10, 20, 40, 60, 120)
SECTORS = ["NIFTY AUTO", "NIFTY BANK", "NIFTY ENERGY", "NIFTY FIN SERVICE", "NIFTY FMCG", "NIFTY IT", "NIFTY MEDIA", "NIFTY METAL", "NIFTY PHARMA",
           "NIFTY PSU BANK", "NIFTY PVT BANK", "NIFTY REALTY", "NIFTY INFRA", "NIFTY PSE", "NIFTY MNC", "NIFTY CONSUMPTION", "NIFTY COMMODITIES",
           "NIFTY SERV SECTOR", "NIFTY CPSE", "NIFTY OIL AND GAS", "NIFTY HEALTHCARE", "NIFTY CONSR DURBL"]

_P: dict = {}


# ---------------------------------------------------------------------------------------------------------------- statistics

def _stat(x: pd.Series) -> tuple[float, float, int]:
    x = x.dropna()
    if len(x) < 3:
        return (float("nan"), float("nan"), int(len(x)))
    se = x.std(ddof=1) / math.sqrt(len(x))
    return (float(x.mean()), float(x.mean() / se) if se else float("nan"), int(len(x)))


def split(df: pd.DataFrame, on: pd.Series, col: str, date_col: str = "date", base: pd.Series | None = None) -> dict:
    """(dev, val) of the per-quarter difference mean(on) - mean(off) within base, plus the counts."""
    d = df if base is None else df[base.reindex(df.index, fill_value=False).astype(bool)]
    o = on.reindex(d.index)
    d = d.assign(_on=o.astype("float"), _y=d[col]).dropna(subset=["_on", "_y"])
    d = d.assign(_q=pd.to_datetime(d[date_col]).dt.to_period("Q"), _yr=pd.to_datetime(d[date_col]).dt.year)
    g = d.groupby(["_q", "_on"])["_y"].agg(["mean", "count"]).unstack("_on")
    out = {}
    for per, sel in (("dev", lambda q: q.year < SPLIT), ("val", lambda q: q.year >= SPLIT)):
        gg = g[[sel(q) for q in g.index]] if len(g) else g
        if len(gg) == 0 or ("mean", 1.0) not in gg.columns or ("mean", 0.0) not in gg.columns:
            out[per] = (float("nan"), float("nan"), 0)
            continue
        ok = (gg[("count", 1.0)] >= MIN_SIDE) & (gg[("count", 0.0)] >= MIN_SIDE)
        out[per] = _stat((gg[("mean", 1.0)] - gg[("mean", 0.0)])[ok])
    n_on = int((d["_on"] == 1).sum())
    out["extra"] = {"n_on": n_on, "n_off": int((d["_on"] == 0).sum()), "mean_on": float(d.loc[d["_on"] == 1, "_y"].mean()) if n_on else None,
                    "mean_off": float(d.loc[d["_on"] == 0, "_y"].mean()) if len(d) - n_on else None,
                    "on_dev_val": [float(d.loc[(d["_on"] == 1) & (d["_yr"] < SPLIT), "_y"].mean()), float(d.loc[(d["_on"] == 1) & (d["_yr"] >= SPLIT), "_y"].mean())]}
    return out


def level(df: pd.DataFrame, on: pd.Series, col: str, date_col: str = "date") -> dict:
    """The signal set's mean outcome minus the base's mean in the same quarter (the market's own drift), t across quarters."""
    d = df.assign(_on=on.reindex(df.index).fillna(False).astype(bool)).dropna(subset=[col])
    q = pd.to_datetime(d[date_col]).dt.to_period("Q")
    allm = d.groupby(q)[col].mean()
    sig = d[d["_on"]]
    sq = pd.to_datetime(sig[date_col]).dt.to_period("Q")
    sm = sig.groupby(sq)[col].agg(["mean", "count"])
    sm = sm[sm["count"] >= 3]
    diff = sm["mean"] - allm.reindex(sm.index)
    out = {"dev": _stat(diff[[p.year < SPLIT for p in diff.index]]), "val": _stat(diff[[p.year >= SPLIT for p in diff.index]])}
    out["extra"] = {"n_on": int(len(sig)), "mean_on": float(sig[col].mean()) if len(sig) else None, "mean_all": float(d[col].mean())}
    return out


def absolute(df: pd.DataFrame, on: pd.Series, col: str, date_col: str = "date") -> dict:
    """The signal set's own mean outcome (for 'this makes money' claims), quarter means, t across quarters."""
    sig = df[on.reindex(df.index).fillna(False).astype(bool)].dropna(subset=[col])
    q = pd.to_datetime(sig[date_col]).dt.to_period("Q")
    m = sig.groupby(q)[col].mean()
    return {"dev": _stat(m[[p.year < SPLIT for p in m.index]]), "val": _stat(m[[p.year >= SPLIT for p in m.index]]),
            "extra": {"n_on": int(len(sig)), "mean_on": float(sig[col].mean()) if len(sig) else None, "win_rate_info_only": float((sig[col] > 0).mean()) if len(sig) else None}}


# ---------------------------------------------------------------------------------------------------------------- stock panel

def _cooldown(df: pd.DataFrame, mask: pd.Series, days: int = 10) -> pd.Series:
    """First signal per stock, then none for `days` sessions (event signals)."""
    idx = df.index[mask.reindex(df.index, fill_value=False).astype(bool)]
    keep = []
    last: dict = {}
    for i, sid, n in zip(idx, df.loc[idx, "sid"].values, df.loc[idx, "n"].values):
        if sid not in last or n - last[sid] >= days:
            keep.append(i)
            last[sid] = n
    return pd.Series(True, index=pd.Index(keep)).reindex(df.index, fill_value=False)


def _rsi(c: pd.Series, n: int = 14) -> pd.Series:
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def _per_stock(g: pd.DataFrame, nifty500: pd.Series) -> pd.DataFrame:
    c, o, h, l, v = g["c"], g["o"], g["h"], g["l"], g["volume"]
    out = pd.DataFrame(index=g.index)
    out["n"] = np.arange(len(g))
    nxt_o = o.shift(-1)
    jump = (c.pct_change().abs() > 0.5).astype(int)
    for k in H:
        fwd = c.shift(-k) / nxt_o - 1
        bad = jump[::-1].rolling(k + 1, min_periods=1).sum()[::-1].shift(-1) > 0      # a >50% one-day move inside the window: an artefact, not a trade
        out[f"fwd{k}"] = fwd.where(~bad)
    out["minfwd60"] = (l[::-1].rolling(60, min_periods=20).min()[::-1].shift(-1) / nxt_o - 1)
    out["minfwd120"] = (l[::-1].rolling(120, min_periods=40).min()[::-1].shift(-1) / nxt_o - 1)
    out["maxfwd15"] = (h[::-1].rolling(15, min_periods=5).max()[::-1].shift(-1))
    sma50 = c.rolling(50, min_periods=50).mean()
    sma100 = c.rolling(100, min_periods=100).mean()
    sma150 = c.rolling(150, min_periods=150).mean()
    sma200 = c.rolling(200, min_periods=200).mean()
    out["sma50_up"] = sma50 > sma50.shift(10)
    out["sma150_up"] = sma150 > sma150.shift(20)
    out["above100"] = c > sma100
    out["above150"] = c > sma150
    out["dist_sma50"] = c / sma50 - 1
    out["dist_sma200"] = c / sma200 - 1
    hi252 = h.rolling(250, min_periods=120).max()
    out["dist_hi252"] = c / hi252 - 1
    out["ath"] = c >= h.cummax().shift(1)                              # a close above every earlier high in the data
    out["hi20_prev"] = h.rolling(20, min_periods=20).max().shift(1)
    out["hi60_prev"] = h.rolling(60, min_periods=60).max().shift(1)
    for w in (20, 40, 60, 120):
        out[f"rng{w}"] = h.rolling(w, min_periods=w).max().shift(1) / l.rolling(w, min_periods=w).min().shift(1) - 1
    rng = (h - l)
    out["range_vs_max20"] = rng / rng.rolling(20, min_periods=20).max().shift(1)
    out["close_pos"] = ((c - l) / rng.replace(0, np.nan))
    out["upper_wick"] = ((h - np.maximum(o, c)) / rng.replace(0, np.nan))
    out["vol50"] = v / v.rolling(50, min_periods=50).mean().shift(1)
    ix = nifty500.reindex(g["date"].values).values
    rs = c.values / ix
    rs = pd.Series(rs, index=g.index)
    out["rs_hi126"] = rs >= rs.rolling(126, min_periods=100).max() * 0.995
    out["rs_up20"] = rs > rs.shift(20)
    out["rs_ret63"] = rs / rs.shift(63) - 1
    out["rs_ret126"] = rs / rs.shift(126) - 1
    out["rsi14"] = _rsi(c, 14)
    ll15, hh15 = l.rolling(15, min_periods=15).min(), h.rolling(15, min_periods=15).max()
    k_raw = 100 * (c - ll15) / (hh15 - ll15).replace(0, np.nan)
    out["stoch_k"] = k_raw.rolling(3, min_periods=3).mean()
    out["stoch_d"] = out["stoch_k"].rolling(3, min_periods=3).mean()
    # ADX(14), Wilder
    up_m, dn_m = h.diff(), -l.diff()
    pdm = pd.Series(np.where((up_m > dn_m) & (up_m > 0), up_m, 0.0), index=g.index)
    ndm = pd.Series(np.where((dn_m > up_m) & (dn_m > 0), dn_m, 0.0), index=g.index)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr_w = tr.ewm(alpha=1 / 14, adjust=False).mean()
    pdi = 100 * pdm.ewm(alpha=1 / 14, adjust=False).mean() / atr_w
    ndi = 100 * ndm.ewm(alpha=1 / 14, adjust=False).mean() / atr_w
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
    out["adx"] = dx.ewm(alpha=1 / 14, adjust=False).mean()
    out["adx_up"] = out["adx"] > out["adx"].shift(3)
    out["pdi_gt"] = pdi > ndi
    ema20 = c.ewm(span=20, adjust=False).mean()
    out["touch_ema20"] = (l <= ema20) & (c >= ema20 * 0.99)
    out["break_prev_high"] = h > h.shift(1)
    # Ichimoku (the cloud at t is built from data 26 sessions earlier: known at t)
    tenkan = (h.rolling(9).max() + l.rolling(9).min()) / 2
    kijun = (h.rolling(26).max() + l.rolling(26).min()) / 2
    sa = ((tenkan + kijun) / 2).shift(26)
    sb = ((h.rolling(52).max() + l.rolling(52).min()) / 2).shift(26)
    out["above_cloud"] = c > np.maximum(sa, sb)
    out["cloud_cross"] = out["above_cloud"] & ~out["above_cloud"].shift(1, fill_value=False)
    out["ichi_aligned"] = out["cloud_cross"] & (sa > sa.shift(1)) & (sb >= sb.shift(1)) & (c > c.shift(26)) & (tenkan > tenkan.shift(1)) & (kijun >= kijun.shift(1))
    # swing structure: 20-session highs and lows higher than the 20 before (TWT-H30's higher-high / higher-low)
    out["hh_hl"] = (h.rolling(20).max() > h.rolling(20).max().shift(20)) & (l.rolling(20).min() > l.rolling(20).min().shift(20))
    # pivot lows confirmed 2 bars later: a low under the 2 lows before and the 2 after, known at t (the pivot is at t-2)
    piv = (l.shift(2) < l.shift(3)) & (l.shift(2) < l.shift(4)) & (l.shift(2) < l.shift(1)) & (l.shift(2) < l)
    pl_val = l.shift(2).where(piv)
    pr_val = out["rsi14"].shift(2).where(piv)
    out["last_pivot_low"] = pl_val.ffill()
    prev_pl = pl_val.ffill().shift(1).where(piv)
    prev_pr = pr_val.ffill().shift(1).where(piv)
    out["hidden_div"] = piv & (pl_val > prev_pl) & (pr_val < prev_pr) & (pr_val <= 35)
    out["below_swing"] = c < out["last_pivot_low"].shift(1)
    out["red_big"] = (c / c.shift(1) - 1) <= -0.015
    out["low_vs50"] = l / sma50 - 1
    out["dist_ath"] = c / h.cummax() - 1
    out["hi120_prev"] = h.rolling(120, min_periods=120).max().shift(1)
    out["fwd_minc5"] = c[::-1].rolling(5, min_periods=5).min()[::-1].shift(-1) / c - 1          # lowest close of the next 5 sessions
    out["fwd_minc10"] = c[::-1].rolling(10, min_periods=10).min()[::-1].shift(-1) / c - 1
    out["fwd_minl20"] = l[::-1].rolling(20, min_periods=20).min()[::-1].shift(-1) / c - 1
    # follow-through, known at the close of day 5 (TWT-H17): outcomes start there
    v50 = out["vol50"]
    vol_days = sum((v50.shift(-k) > 1).astype(int) for k in range(1, 6))
    out["ft"] = (c.shift(-1) > c) & (c.shift(-2) > c) & (c.shift(-3) > c) & (vol_days >= 3)
    for k in (20, 60):
        f5 = c.shift(-(5 + k)) / c.shift(-5) - 1
        out[f"p5fwd{k}"] = f5.where(~(jump[::-1].rolling(k + 6, min_periods=1).sum()[::-1].shift(-1) > 0))
    # Heikin Ashi (TWT-H50)
    ha_c = ((o + h + l + c) / 4).values
    ha_o = np.empty(len(g))
    ha_o[0] = (o.iloc[0] + c.iloc[0]) / 2
    for i in range(1, len(g)):
        ha_o[i] = (ha_o[i - 1] + ha_c[i - 1]) / 2
    green = pd.Series(ha_c > ha_o, index=g.index)
    out["ha_flip"] = green & ~green.shift(1, fill_value=True)
    init = green & ~green.shift(1, fill_value=True) & ~green.shift(2, fill_value=True) & ~green.shift(3, fill_value=True)
    out["ha_conf"] = green & init.shift(1, fill_value=False)
    wr_down = ((h - l) > 1.5 * g["atr14"]) & (c < o)
    out["wrd5"] = wr_down.astype(int).rolling(5, min_periods=1).sum()
    # weekly outside bars (TWT-H53): flagged on the week's last session
    wk = g["date"].dt.to_period("W-FRI")
    W = pd.DataFrame({"wk": wk.values, "o": o.values, "h": h.values, "l": l.values, "c": c.values, "v": v.values}).groupby("wk").agg(
        o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"), v=("v", "sum"))
    up8 = W["c"] / W["c"].shift(8) - 1
    bull = (W["h"] > W["h"].shift(1)) & (W["l"] < W["l"].shift(1)) & (W["c"] > W["h"].shift(1)) & (up8.shift(1) <= -0.10)
    bear = (W["h"] > W["h"].shift(1)) & (W["l"] < W["l"].shift(1)) & (W["c"] < W["l"].shift(1)) & (up8.shift(1) >= 0.10)
    vmax = W["v"] >= W["v"].rolling(52, min_periods=26).max()
    last = ~wk.duplicated(keep="last").values
    for name, ser in (("wk_out_bull", bull), ("wk_out_bear", bear), ("wk_out_bull_v", bull & vmax)):
        m = wk.map(ser.fillna(False).to_dict()).fillna(False).astype(bool).values
        out[name] = m & last
    # red day with no follow-through (OPT-H49): known at the close of day 3, outcomes start there
    out["nf3"] = out["red_big"] & (c[::-1].rolling(3, min_periods=3).min()[::-1].shift(-1) >= l)
    out["ff3"] = out["red_big"] & (c[::-1].rolling(3, min_periods=3).min()[::-1].shift(-1) < l)
    for k in (5, 20):
        f3 = c.shift(-(3 + k)) / c.shift(-3) - 1
        out[f"p3fwd{k}"] = f3.where(~(jump[::-1].rolling(k + 4, min_periods=1).sum()[::-1].shift(-1) > 0))
    # 20-EMA touch, then a break of that candle's high the next day (TWT-H54)
    out["ema_break"] = out["touch_ema20"].shift(1, fill_value=False) & (h > h.shift(1))
    out["ema_break_adx"] = out["ema_break"] & (out["adx"].shift(1) > 30) & out["adx_up"].shift(1, fill_value=False) & out["pdi_gt"].shift(1, fill_value=False)
    # 50-DMA pullback window (TWT-H09)
    out["touch50_3"] = (out["low_vs50"] <= 0.01).astype(int).rolling(3, min_periods=1).max().astype(bool)
    out["vol50_5"] = v50.rolling(5, min_periods=3).mean()
    # after a 60-session breakout: the first 3% pullback in days 3-15 (TWT-H18) and the first retest of the broken level in days 5-20 (OPT-H52)
    n = len(g)
    cc, hh_, ll_, vv = c.values, h.values, l.values, v50.values
    lvl = out["hi60_prev"].values
    brk = (cc > lvl) & ~np.isnan(lvl)
    pb = np.zeros(n, bool); pb_good = np.zeros(n, bool); pb_shallow = np.zeros(n, bool); pb_new = np.full(n, np.nan)
    rt = np.zeros(n, bool)
    last_b = -99
    for b in np.flatnonzero(brk):
        if b - last_b < 10:
            continue
        last_b = b
        run_max = hh_[b]
        got_pb = got_rt = False
        for j in range(b + 1, min(n, b + 21)):
            if not got_pb and j <= b + 15 and j >= b + 3 and cc[j] <= run_max * 0.97:
                got_pb = True
                pb[j] = True
                up_v = np.nanmean(vv[b:max(b + 1, j - 2)])
                dn_v = np.nanmean(vv[max(b, j - 2): j + 1])
                pb_good[j] = (cc[j] >= lvl[b]) and (dn_v < up_v)
                run = run_max - ll_[b]
                pb_shallow[j] = run > 0 and (run_max - cc[j]) / run < 0.382
                if j + 15 < n:
                    pb_new[j] = float(np.max(hh_[j + 1: j + 16]) > run_max)
            if not got_rt and j >= b + 5 and ll_[j] <= lvl[b] * 1.01 and cc[j] >= lvl[b] * 0.98:
                got_rt = True
                rt[j] = True
            if not got_pb:
                run_max = max(run_max, hh_[j])
    out["pb3"], out["pb3_good"], out["pb3_shallow"], out["pb3_newhigh15"], out["retest1"] = pb, pb_good, pb_shallow, pb_new, rt
    return out


def stock_panel(top: int = 500) -> pd.DataFrame:
    """The liquid universe (rank <= top) with every feature the stock cards use. Cached in memory and in gold/teachers/stock_panel.parquet."""
    if "stock" in _P:
        return _P["stock"]
    p = paths.gold() / "teachers" / "stock_panel.parquet"
    if p.exists():
        _P["stock"] = pd.read_parquet(p)
        return _P["stock"]
    f = pd.read_parquet(paths.gold() / "features" / "daily.parquet")
    f["date"] = pd.to_datetime(f["date"])
    f = f[(f["date"] < "2024-01-01")].sort_values(["sid", "date"])
    keep = f.groupby("sid")["liq_rank"].transform("min") <= top                 # stocks that were ever liquid: their whole history, for warm-up
    f = f[keep].reset_index(drop=True)
    ix = index_panel()
    n500 = ix["NIFTY 500"]
    parts = []
    for sid, g in f.groupby("sid", sort=False):
        if len(g) < 260:
            continue
        parts.append(pd.concat([g[["sid", "date", "symbol", "liq_rank", "o", "h", "l", "c", "volume", "ret_1", "ret_20", "ret_60", "dist_sma20", "atr14", "atr_pct",
                                   "vol_ratio20", "breakout20", "pos20", "range_pct", "rv20", "deliv_pct"]], _per_stock(g, n500)], axis=1))
    df = pd.concat(parts, ignore_index=True)
    df = df[(df["liq_rank"] <= top) & (df["date"] >= "2000-01-01")].reset_index(drop=True)
    # costs: delivery round trip on the paper notional plus the spread estimate for the rank (labelled estimate), by year and rank bucket
    df["rank_b"] = (df["liq_rank"] // 50 * 50 + 25).clip(upper=500)
    cache = {}
    for y, r in df[["date", "rank_b"]].assign(y=df["date"].dt.year)[["y", "rank_b"]].drop_duplicates().itertuples(index=False):
        cache[(y, r)] = costs.round_trip("delivery", 50_000, 50_000, year=int(y), turnover_rank=int(r))["total"] / 50_000
    df["cost"] = [cache[(y, r)] for y, r in zip(df["date"].dt.year, df["rank_b"])]
    for k in H:
        df[f"net{k}"] = df[f"fwd{k}"] - df["cost"]
    for k in (20, 60):
        df[f"p5net{k}"] = df[f"p5fwd{k}"] - df["cost"]
    b = pd.DataFrame({"date": df["date"], "breadth200": (df["dist_sma200"] > 0).where(df["dist_sma200"].notna()).astype(float),
                      "breadth50": (df["dist_sma50"] > 0).where(df["dist_sma50"].notna()).astype(float),
                      "hhhl": df["hh_hl"].astype(float).where(df["dist_sma50"].notna())})
    breadth = b.groupby("date")[["breadth200", "breadth50", "hhhl"]].mean()          # share of the liquid 500 with enough history
    df = df.merge(breadth, left_on="date", right_index=True, how="left")
    df = df.merge(market_context(), left_on="date", right_index=True, how="left")
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(p, index=False)
    _P["stock"] = df
    return df


def sample5(df: pd.DataFrame) -> pd.Series:
    """Every 5th session per stock: state conditions without five overlapping copies of the same hold."""
    return (df["n"] % 5) == 0


# ---------------------------------------------------------------------------------------------------------------- index panel

def index_panel() -> pd.DataFrame:
    if "index" in _P:
        return _P["index"]
    ix = pd.read_parquet(paths.data_dir() / "silver/kite_index/day/day.parquet")
    ix["date"] = pd.to_datetime(ix["date"])
    ix = ix[ix["date"] < "2024-01-01"]
    piv = ix.pivot_table(index="date", columns="index_name", values="close", aggfunc="last").sort_index()
    _P["index"] = piv
    hl = {k: ix.pivot_table(index="date", columns="index_name", values=k, aggfunc="last").sort_index() for k in ("open", "high", "low")}
    _P["index_ohl"] = hl
    return piv


def _fwd_close(s: pd.Series, k: int) -> pd.Series:
    return s.shift(-(k + 1)) / s.shift(-1) - 1


def market_context() -> pd.DataFrame:
    """Daily market facts known at each close (to 2023): Nifty and its averages, VIX, Bank Nifty, small/large caps, the dollar, crude, the Nasdaq."""
    if "ctx" in _P:
        return _P["ctx"]
    piv = index_panel()
    n = piv["NIFTY 50"]
    c = pd.DataFrame(index=piv.index)
    sma50, sma200 = n.rolling(50).mean(), n.rolling(200).mean()
    c["nifty"] = n
    c["nifty_vs50"] = n / sma50 - 1
    c["nifty_vs200"] = n / sma200 - 1
    c["nifty_50up"] = sma50 > sma50.shift(10)
    c["nifty_200up"] = sma200 > sma200.shift(20)
    c["nifty_below_both"] = (c["nifty_vs50"] < 0) & (c["nifty_vs200"] < 0)
    c["nifty_dd252"] = n / n.rolling(252, min_periods=60).max() - 1
    c["nifty_ath"] = n >= n.cummax().shift(1)
    c["nifty_ret5"] = n / n.shift(5) - 1
    c["vix"] = piv.get("INDIA VIX")
    c["vix_vs20"] = c["vix"] / c["vix"].rolling(20).mean() - 1
    c["vix_wk"] = c["vix"] / c["vix"].shift(5) - 1
    c["bank_vs200"] = piv["NIFTY BANK"] / piv["NIFTY BANK"].rolling(200).mean() - 1
    c["bank_ret5"] = piv["NIFTY BANK"] / piv["NIFTY BANK"].shift(5) - 1
    ratio = piv["NIFTY SMLCAP 100"] / piv["NIFTY 100"]
    c["sl_ratio"] = ratio
    c["sl_vs50"] = ratio / ratio.rolling(50).mean() - 1
    c["sl_ret40"] = ratio / ratio.shift(40) - 1
    for k in (5, 10, 21, 42, 63, 126, 252):
        c[f"nfwd{k}"] = _fwd_close(n, k)
        c[f"slfwd{k}"] = _fwd_close(ratio, k)
    r1 = n.pct_change()
    c["nrv_fwd21"] = r1[::-1].rolling(21).std()[::-1].shift(-1)
    c["n_mdd21"] = (n[::-1].rolling(21, min_periods=10).min()[::-1].shift(-1) / n - 1)
    c["n_mdd63"] = (n[::-1].rolling(63, min_periods=20).min()[::-1].shift(-1) / n - 1)
    rng = (_P["index_ohl"]["high"]["NIFTY 50"] - _P["index_ohl"]["low"]["NIFTY 50"]) / n
    c["n_rng10_vs50"] = rng.rolling(10).mean() / rng.rolling(50).mean()
    try:
        m = pd.read_parquet(paths.data_dir() / "silver/macro/macro.parquet")
        m["date"] = pd.to_datetime(m["date"])
        m = m[m["date"] < "2024-01-01"]
        mp = m.pivot_table(index="date", columns="series", values="value", aggfunc="last").sort_index()
        mac = pd.DataFrame(index=mp.index)
        dx = mp["DTWEXBGS"].dropna()
        mac["dxy_chg126"] = dx / dx.shift(126) - 1
        mac["dxy_break"] = dx > dx.rolling(756, min_periods=500).max().shift(1)
        br = mp["DCOILBRENTEU"].dropna()
        mac["brent"] = br
        mac["brent_vs50"] = br / br.rolling(50).mean() - 1
        nq = mp["NASDAQCOM"].dropna()
        mac["nq_vs50"] = nq / nq.rolling(50).mean() - 1
        mac["nq_dd60"] = nq / nq.rolling(60).max() - 1
        mac["nq_reclaim50"] = (mac["nq_vs50"] > 0) & (mac["nq_vs50"].shift(1) <= 0)
        idx = pd.DataFrame({"date": c.index, "known_by": c.index - pd.Timedelta(days=1)}).sort_values("known_by")
        j = pd.merge_asof(idx, mac.reset_index().rename(columns={"date": "mdate"}).sort_values("mdate"), left_on="known_by", right_on="mdate",
                          direction="backward").set_index("date").drop(columns=["known_by", "mdate"])
        c = c.join(j)
    except Exception:  # noqa: BLE001  a card that needs them says the data is missing
        pass
    c.index.name = "date"
    _P["ctx"] = c
    return c


def sector_panel() -> pd.DataFrame:
    """Sector index rows (sector, date) with structure, the 50-day average, relative strength against the Nifty 500, and forward excess returns."""
    piv = index_panel()
    b = piv["NIFTY 500"]
    rows = []
    for s in SECTORS:
        if s not in piv:
            continue
        x = piv[s].dropna()
        bb = b.reindex(x.index)
        d = pd.DataFrame({"date": x.index, "sector": s, "c": x.values})
        sma50 = x.rolling(50).mean()
        rs = x / bb
        hh = (x.rolling(20).max() > x.rolling(20).max().shift(20)) & (x.rolling(20).min() > x.rolling(20).min().shift(20))
        d["strong"] = (hh & (x > sma50) & (sma50 > sma50.shift(10)) & (rs > rs.shift(20))).values
        d["weak"] = ((x < sma50) & (sma50 < sma50.shift(10)) & (rs < rs.shift(20))).values
        d["rs63"] = (rs / rs.shift(63) - 1).values
        d["dd_from_hi"] = (x / x.rolling(252, min_periods=60).max() - 1).values
        for k in (21, 63, 126):
            d[f"xs{k}"] = (_fwd_close(x, k) - _fwd_close(bb, k)).values
        d["n"] = np.arange(len(d))
        rows.append(d)
    return pd.concat(rows, ignore_index=True)
