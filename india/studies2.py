"""Second batch of registered studies (dev 2000-2017, validation 2018-2023; silver and gold only).

  python -m india.studies2 conditions        E04 saturation, E05 pullback depth, C02 volume/delivery, C05 VIX, C07 small caps, C08 breadth, C09 intermarket
  python -m india.studies2 e06               ride and reposition against simply holding (M-12)
  python -m india.studies2 e09               staged entries against one entry (TWT-H20/21)
  python -m india.studies2 all

Condition studies use the trades already produced by E02 (same 8,000 entries per set, same exits), so nothing about the entries or exits is chosen here:
for each condition (india/conditions.py, round thresholds fixed in advance) and each of five exit policies, the mean net return of trades signalled while the
condition is on minus those signalled while it is off, within each quarter that has both, t across quarters. A quarter needs at least 5 trades on each side.
Each condition is both a candidate no-entry filter and context for the exit work: the paper baseline book records the same fields, so the same split can be
read on live paper records (india/filters.py).
"""
from __future__ import annotations

import json
import math
import sys
import time

import numpy as np
import pandas as pd

from india import catalog, conditions, costs, exitlab, paths, registry, studies

SPLIT = studies.SPLIT_YEAR
POLS = ["hold_20d", "hold_60d", "atr_trail_4", "sma_close_50", "swing_low_20"]
MIN_SIDE = 5
GROUPS = {
    "E04": ("filter", "Saturation after long runs and declines (M-03/04/13) as a no-entry filter", ["ext_ret60_gt50", "ext_sma50_gt20", "ext_ret20_gt25", "decline_ret60_lt_m30"], ["BRK", "PULL", "ANY"]),
    "E05": ("filter", "Pullback depth and healthy pullbacks (M-05, TWT-H10/18/19), PULL entries", ["pull_shallow", "pull_deep", "pull_above50", "pull_lowvol", "pull_healthy"], ["PULL"]),
    "C02": ("context", "Volume heat, delivery share and own volatility at entry (crypto H1/H2 port, M-10)", ["vol_heat2", "deliv_high", "rv20_high"], ["BRK", "PULL", "ANY"]),
    "C05": ("context", "India VIX regimes at entry", ["vix_gt20", "vix_rising"], ["BRK", "PULL", "ANY"]),
    "C07": ("context", "Small caps leading large caps at entry (TWT-H13/14)", ["small_lead"], ["BRK", "PULL", "ANY"]),
    "C08": ("context", "Breadth washouts and thrusts at entry (TWT-H01, H30-33)", ["breadth_lt30", "breadth_lt40", "breadth_thrust"], ["BRK", "PULL", "ANY"]),
    "C01": ("context", "Market state after shock days and in high-volatility regimes (crypto C-series port)", ["nifty_down2", "nifty_up2", "nifty_vol_high"], ["BRK", "PULL", "ANY"]),
    "C09": ("context", "Intermarket at entry: rupee, crude, Nasdaq, US 10-year (TWT-H42-47); Nifty valuation (D30) not yet available", ["usdinr_rising", "brent_rising", "nasdaq_gt200d", "us10y_up_60d"], ["BRK", "PULL", "ANY"]),
}


def _qdiff(y: pd.DataFrame, flag: str) -> tuple[float, float, int, dict]:
    y = y[y[flag].notna()]
    q = y.assign(q=y["signal_date"].dt.to_period("Q"), on=y[flag] > 0.5)
    cnt = q.groupby(["q", "on"])["net_ret"].agg(["mean", "size"]).unstack()
    if ("size", True) not in cnt.columns or ("size", False) not in cnt.columns:
        return float("nan"), float("nan"), 0, {"n_on": int((q["on"]).sum()), "n_off": int((~q["on"]).sum())}
    ok = (cnt[("size", True)] >= MIN_SIDE) & (cnt[("size", False)] >= MIN_SIDE)
    d = (cnt[("mean", True)] - cnt[("mean", False)])[ok].dropna()
    info = {"n_on": int(q["on"].sum()), "n_off": int((~q["on"]).sum()), "mean_on": float(q.loc[q["on"], "net_ret"].mean()) if q["on"].any() else None,
            "mean_off": float(q.loc[~q["on"], "net_ret"].mean()) if (~q["on"]).any() else None, "share_on": float(q["on"].mean()) if len(q) else None}
    if len(d) < 3:
        return float("nan"), float("nan"), int(len(d)), info
    se = d.std(ddof=1) / math.sqrt(len(d))
    return float(d.mean()), float(d.mean() / se) if se else float("nan"), int(len(d)), info


def conditions_run(only: list[str] | None = None) -> dict:
    f = studies.load_features()
    ctx = conditions.context_table(f)
    mc = conditions.apply_market(ctx).reset_index()
    feat_cols = ["sid", "date", "ret_20", "ret_60", "dist_sma20", "dist_sma50", "vol_ratio20", "deliv_pct", "rv20"]
    fx = f[feat_cols].copy()
    sc = conditions.apply_stock(fx)
    fx = pd.concat([fx[["sid", "date"]], sc], axis=1)
    out = {}
    for study, (family, title, conds, sets) in GROUPS.items():
        if only and study not in only:
            continue
        for name in sets:
            tr = pd.read_parquet(paths.gold() / "studies" / f"E02-{name}_trades.parquet", columns=["sid", "signal_date", "policy", "net_ret"])
            tr = tr[tr["policy"].isin(POLS) & (tr["signal_date"] >= "2000-01-01")]
            tr = tr.merge(fx, left_on=["sid", "signal_date"], right_on=["sid", "date"], how="left").drop(columns="date")
            tr = tr.merge(mc, left_on="signal_date", right_on="date", how="left").drop(columns="date")
            sid = f"{study}-{name}"
            reg = registry.register(sid, family=family, title=f"{title} ({name} entries)",
                                    hypothesis="Trades signalled while the condition is on earn a different net return than trades signalled while it is off (direction as stated per condition), "
                                               "within quarters, in dev and validation.",
                                    variants=[f"{c}|{p}" for c in conds for p in POLS], note=f"E02-{name} trades; quarter blocks with >= {MIN_SIDE} trades per side; conditions in india/conditions.py")
            for c in conds:
                flag = "cond_" + c
                if flag not in tr.columns or tr[flag].notna().sum() == 0:
                    print(f"{sid:9s} {c:22s} MISSING input: condition not computable on these rows", flush=True)
                    continue
                expect = conditions.ALL[c][2]
                for p in POLS:
                    x = tr[tr["policy"] == p]
                    dev = x[x["signal_date"].dt.year < SPLIT]
                    val = x[x["signal_date"].dt.year >= SPLIT]
                    d_m, d_t, d_n, d_i = _qdiff(dev, flag)
                    v_m, v_t, v_n, v_i = _qdiff(val, flag)
                    line = registry.record(reg, f"{c}|{p}", (d_m, d_t, d_n), (v_m, v_t, v_n), extra={"entry_set": name, "dev": d_i, "val": v_i, "expect": expect}, expect=expect)
                    out.setdefault(sid, {})[f"{c}|{p}"] = line["verdict"]
                    print(f"{sid:9s} {c:22s} {p:13s} {line['verdict']:12s} dev on-off {d_m*100:+.2f}% t {d_t:+.1f} q{d_n} | val {v_m*100:+.2f}% t {v_t:+.1f} q{v_n} | "
                          f"share on val {v_i.get('share_on') or 0:.0%}", flush=True)
    registry.mirror_to_catalog()
    catalog.heartbeat("studies2.conditions", True, json.dumps({k: len(v) for k, v in out.items()}))
    return out


# ----------------------------------------------------------------------------------------------- E06 ride and reposition

def _sma(c: np.ndarray, n: int) -> np.ndarray:
    cs = np.cumsum(np.r_[0.0, c])
    out = np.full(len(c), np.nan)
    out[n - 1:] = (cs[n:] - cs[:-n]) / n
    return out


def _hh(h: np.ndarray, n: int) -> np.ndarray:
    """highest high of the n sessions before each day (not including it)."""
    s = pd.Series(h).rolling(n, min_periods=n).max().shift(1)
    return s.values


def _rr_path(o, c, ma, reentry, i0, j_end, year, rank):
    """In at the open of i0. Close below the average: out at the next open. Out and close above the re-entry level: back in at the next open. Out at the open of j_end."""
    capital = 1.0
    inside, entry_px = True, o[i0]
    trades = 0
    k = i0
    while k < j_end:
        if inside and c[k] < ma[k] and k + 1 < j_end:
            px = o[k + 1]
            gross = capital * px / entry_px
            fee = costs.round_trip("delivery", 50_000.0 * capital, 50_000.0 * gross, year=year, turnover_rank=rank)["total"] / 50_000.0
            capital = gross - fee
            inside, trades = False, trades + 1
            k += 1
            continue
        if not inside and c[k] > reentry[k] and k + 1 < j_end:
            entry_px = o[k + 1]
            inside = True
            k += 1
            continue
        k += 1
    if inside:
        gross = capital * o[j_end] / entry_px
        fee = costs.round_trip("delivery", 50_000.0 * capital, 50_000.0 * gross, year=year, turnover_rank=rank)["total"] / 50_000.0
        capital = gross - fee
        trades += 1
    return capital - 1.0, trades


def e06(max_signals: int = 8000, horizon: int = 60) -> dict:
    """M-12: is riding the trend and stepping aside on weakness (then back in on strength) better than simply holding, after costs, over 60 sessions?
    No stops in either arm, so the only difference is the reposition rule. Paired per signal; quarter-block t."""
    f = studies.load_features()
    sets = studies.entry_sets(f, max_signals)
    bars = exitlab.load_bars()
    rank_of = f.set_index(["sid", "date"])["liq_rank"]
    variants = {"rr_sma20_hh10": (20, "hh", 10), "rr_sma20_sma20": (20, "sma", 20), "rr_sma50_hh20": (50, "hh", 20)}
    out = {}
    for name, ent in sets.items():
        reg = registry.register(f"E06-{name}", family="reposition", title=f"Ride and reposition vs hold, {name} entries",
                                hypothesis="Stepping out on a close below the moving average and back in on strength earns more over 60 sessions than holding, net of costs (M-12).",
                                variants=list(variants), note="no stops in either arm; each round trip pays delivery costs; tax not modelled (same holding-period class)")
        rows = []
        for sid, sig in zip(ent["sid"], pd.to_datetime(ent["signal_date"])):
            b = bars.get(sid)
            if b is None:
                continue
            dates, o, h, l, c, v = b
            i0 = int(np.searchsorted(dates, np.datetime64(sig.date()), side="right"))
            j_end = i0 + horizon
            if j_end >= len(dates) or i0 < 60:
                continue
            seg = c[i0:j_end + 1]
            if np.any(np.abs(seg[1:] / seg[:-1] - 1) > 0.5):
                continue
            rank = int(rank_of.get((sid, sig), 250))
            yr = sig.year
            hold_gross = o[j_end] / o[i0]
            hold = hold_gross - 1 - costs.round_trip("delivery", 50_000.0, 50_000.0 * hold_gross, year=yr, turnover_rank=rank)["total"] / 50_000.0
            r = {"sid": sid, "signal_date": sig, "hold": hold}
            for vn, (n_ma, kind, n_re) in variants.items():
                ma = _sma(c, n_ma)
                re = _hh(h, n_re) if kind == "hh" else _sma(c, n_re)
                ret, ntr = _rr_path(o, c, ma, re, i0, j_end, yr, rank)
                r[vn], r[vn + "_trades"] = ret, ntr
            rows.append(r)
        df = pd.DataFrame(rows)
        df.to_parquet(paths.gold() / "studies" / f"E06-{name}_trades.parquet")
        for vn in variants:
            df["d"] = df[vn] - df["hold"]
            st = {}
            for per, m in (("dev", df["signal_date"].dt.year < SPLIT), ("val", df["signal_date"].dt.year >= SPLIT)):
                d = studies._blk(df[m], "d")
                se = d.std(ddof=1) / math.sqrt(len(d)) if len(d) > 2 else float("nan")
                st[per] = (float(d.mean()), float(d.mean() / se) if se else float("nan"), int(len(d)))
                st[per + "_x"] = {"mean_variant": float(df.loc[m, vn].mean()), "mean_hold": float(df.loc[m, "hold"].mean()), "trades": float(df.loc[m, vn + "_trades"].mean()),
                                  "p5_variant": float(df.loc[m, vn].quantile(0.05)), "p5_hold": float(df.loc[m, "hold"].quantile(0.05))}
            line = registry.record(reg, vn, st["dev"], st["val"], extra={"entry_set": name, "dev": st["dev_x"], "val": st["val_x"]}, expect=1)
            out.setdefault(name, {})[vn] = line["verdict"]
            x = st["val_x"]
            print(f"E06-{name:5s} {vn:16s} {line['verdict']:12s} dev {st['dev'][0]*100:+.2f}% t {st['dev'][1]:+.1f} | val {st['val'][0]*100:+.2f}% t {st['val'][1]:+.1f} | "
                  f"val mean {x['mean_variant']*100:+.2f}% vs hold {x['mean_hold']*100:+.2f}%, trades {x['trades']:.1f}, p5 {x['p5_variant']*100:.1f}% vs {x['p5_hold']*100:.1f}%", flush=True)
    registry.mirror_to_catalog()
    return out


# ----------------------------------------------------------------------------------------------- E09 staged entries

def e09(max_signals: int = 8000, horizon: int = 20) -> dict:
    """TWT-H20/21: split the buy. 25% at the signal open and 75% on a 3% pullback within 10 sessions (else at the open of day 10), or four weekly 25% buys,
    against all of it at the signal open. Same exit for every arm: everything out at the open of day 20. Return per rupee deployed, net of every order's costs."""
    f = studies.load_features()
    sets = studies.entry_sets(f, max_signals)
    bars = exitlab.load_bars()
    rank_of = f.set_index(["sid", "date"])["liq_rank"]
    out = {}
    for name, ent in sets.items():
        reg = registry.register(f"E09-{name}", family="staging", title=f"Staged entries vs one entry, {name} entries",
                                hypothesis="Splitting the entry (25/75 on a pullback, or weekly quarters) earns more per rupee deployed than one entry at the signal open, same exit (TWT-H20/21).",
                                variants=["stage_25_75_pullback", "stage_weekly4"], note="exit for all arms at the open of session 20; no stop; tail (5th percentile) reported")
        rows = []
        for sid, sig in zip(ent["sid"], pd.to_datetime(ent["signal_date"])):
            b = bars.get(sid)
            if b is None:
                continue
            dates, o, h, l, c, v = b
            i0 = int(np.searchsorted(dates, np.datetime64(sig.date()), side="right"))
            j = i0 + horizon
            if j >= len(dates):
                continue
            seg = c[i0:j + 1]
            if np.any(np.abs(seg[1:] / seg[:-1] - 1) > 0.5):
                continue
            rank, yr = int(rank_of.get((sid, sig), 250)), sig.year

            def arm(buys):  # buys: list of (day index, weight)
                pnl = 0.0
                for k, w in buys:
                    notional = 50_000.0 * w
                    sell = notional * o[j] / o[k]
                    pnl += sell - notional - costs.round_trip("delivery", notional, sell, year=yr, turnover_rank=rank)["total"]
                return pnl / 50_000.0
            one = arm([(i0, 1.0)])
            pb = next((k + 1 for k in range(i0, min(i0 + 10, j - 1)) if c[k] <= o[i0] * 0.97), i0 + 10)
            staged = arm([(i0, 0.25), (min(pb, j - 1), 0.75)])
            weekly = arm([(i0 + d, 0.25) for d in (0, 5, 10, 15) if i0 + d < j])
            rows.append({"sid": sid, "signal_date": sig, "one": one, "stage_25_75_pullback": staged, "stage_weekly4": weekly, "pullback_hit": pb < i0 + 10})
        df = pd.DataFrame(rows)
        df.to_parquet(paths.gold() / "studies" / f"E09-{name}_trades.parquet")
        for vn in ("stage_25_75_pullback", "stage_weekly4"):
            df["d"] = df[vn] - df["one"]
            st = {}
            for per, m in (("dev", df["signal_date"].dt.year < SPLIT), ("val", df["signal_date"].dt.year >= SPLIT)):
                d = studies._blk(df[m], "d")
                se = d.std(ddof=1) / math.sqrt(len(d)) if len(d) > 2 else float("nan")
                st[per] = (float(d.mean()), float(d.mean() / se) if se else float("nan"), int(len(d)))
                st[per + "_x"] = {"mean_variant": float(df.loc[m, vn].mean()), "mean_one": float(df.loc[m, "one"].mean()), "p5_variant": float(df.loc[m, vn].quantile(0.05)),
                                  "p5_one": float(df.loc[m, "one"].quantile(0.05)), "pullback_hit": float(df.loc[m, "pullback_hit"].mean())}
            line = registry.record(reg, vn, st["dev"], st["val"], extra={"entry_set": name, "dev": st["dev_x"], "val": st["val_x"]}, expect=1)
            out.setdefault(name, {})[vn] = line["verdict"]
            x = st["val_x"]
            print(f"E09-{name:5s} {vn:22s} {line['verdict']:12s} dev {st['dev'][0]*100:+.2f}% t {st['dev'][1]:+.1f} | val {st['val'][0]*100:+.2f}% t {st['val'][1]:+.1f} | "
                  f"val {x['mean_variant']*100:+.2f}% vs {x['mean_one']*100:+.2f}%, p5 {x['p5_variant']*100:.1f}% vs {x['p5_one']*100:.1f}%", flush=True)
    registry.mirror_to_catalog()
    return out


if __name__ == "__main__":
    paths.ensure()
    w = sys.argv[1] if len(sys.argv) > 1 else "all"
    t0 = time.time()
    if w in ("conditions", "all"):
        conditions_run()
    if w in ("e06", "all"):
        e06()
    if w in ("e09", "all"):
        e09()
    print(f"done in {time.time() - t0:.0f}s", flush=True)


# ----------------------------------------------------------------------------------------------- rare market states as declustered events

EVENT_CONDS = ["nifty_down2", "nifty_up2", "nifty_vol_high", "breadth_lt30", "vix_gt20", "breadth_thrust"]


def market_events(entry_set: str = "ANY") -> dict:
    """Registered 18 Oct after the within-quarter design came back INCONCLUSIVE for rare market states (too few quarters with both sides); the change of
    method is disclosed here and in the registration. Unit = an event day: the first day a market condition turns on after 20 sessions off. Outcome = mean net
    return of the entries signalled on the event day minus the mean of the entries signalled 21-40 sessions earlier (the same stocks' universe, the regime
    just before). Events at least 20 sessions apart, so their 20-day outcomes barely overlap; t across events."""
    f = studies.load_features()
    ctx = conditions.context_table(f)
    mc = conditions.apply_market(ctx)
    tr = pd.read_parquet(paths.gold() / "studies" / f"E02-{entry_set}_trades.parquet", columns=["sid", "signal_date", "policy", "net_ret"])
    tr = tr[tr["policy"].isin(POLS) & (tr["signal_date"] >= "2000-01-01")]
    days = pd.DatetimeIndex(sorted(mc.index))
    reg = registry.register(f"CEV-{entry_set}", family="context_events", title=f"Rare market states as declustered events ({entry_set} entries)",
                            hypothesis="Entries signalled on the first day of a market state earn a different net return than entries signalled 21-40 sessions before it.",
                            variants=[f"{c}|{p}" for c in EVENT_CONDS for p in POLS], note="method chosen after the within-quarter design was INCONCLUSIVE; disclosed")
    out = {}
    for c in EVENT_CONDS:
        col = "cond_" + c
        if col not in mc:
            continue
        on = mc[col].fillna(0) > 0.5
        prev_off = ~on.shift(1, fill_value=False).rolling(20, min_periods=1).max().astype(bool)
        starts = on & prev_off
        ev, last = [], None
        for d in days[starts.reindex(days).fillna(False).values]:
            if last is None or days.get_loc(d) - days.get_loc(last) >= 20:
                ev.append(d)
                last = d
        for p in POLS:
            x = tr[tr["policy"] == p].groupby("signal_date")["net_ret"].mean()
            diffs = []
            for d in ev:
                i = days.get_loc(d)
                if i < 40:
                    continue
                base = x.reindex(days[i - 40:i - 20]).dropna()
                if d in x.index and len(base) >= 5:
                    diffs.append((d, x[d] - base.mean()))
            s = pd.Series({d: v for d, v in diffs})
            dev = _stat(s[s.index.year < SPLIT]) if len(s) else (np.nan, np.nan, 0)
            val = _stat(s[s.index.year >= SPLIT]) if len(s) else (np.nan, np.nan, 0)
            line = registry.record(reg, f"{c}|{p}", dev, val, extra={"events": len(ev), "expect": conditions.ALL[c][2]}, expect=conditions.ALL[c][2])
            out[f"{c}|{p}"] = line["verdict"]
            print(f"CEV-{entry_set} {c:15s} {p:13s} {line['verdict']:12s} dev {dev[0]*100:+.2f}% t {dev[1]:+.1f} n{dev[2]} | val {val[0]*100:+.2f}% t {val[1]:+.1f} n{val[2]}", flush=True)
    registry.mirror_to_catalog()
    return out


def _stat(x: pd.Series) -> tuple[float, float, int]:
    x = x.dropna()
    if len(x) < 3:
        return float("nan"), float("nan"), int(len(x))
    se = x.std(ddof=1) / math.sqrt(len(x))
    return float(x.mean()), float(x.mean() / se) if se else float("nan"), int(len(x))


# ----------------------------------------------------------------------------------------------- E11 exit on a lower price-band hit

def e11(max_signals: int = 400000) -> dict:
    """V02 found that stocks hitting their lower price band keep falling for 20 sessions. As an exit: when a held stock hits its lower band (exchange list,
    known at the close), leave at the next open. Paired against the same policy without it, trade by trade, quarter blocks."""
    f = studies.load_features()
    sets = studies.entry_sets(f, max_signals)
    bars = exitlab.load_bars()
    base_pols = [exitlab.Policy("hold_60d", "hold", 60), exitlab.Policy("atr_trail_4", "atr_trail", 4), exitlab.Policy("sma_close_50", "sma_close", 50)]
    pols = base_pols + [exitlab.Policy(p.name + "+band_low", p.kind, p.n, sig=("band_low",)) for p in base_pols]
    out = {}
    for name, ent in sets.items():
        reg = registry.register(f"E11-{name}", family="exit", title=f"Exit on a lower price-band hit, {name} entries",
                                hypothesis="Leaving at the next open after the stock hits its lower price band raises net return per trade against the same policy without it.",
                                variants=[p.name for p in pols if "+" in p.name], note="band list from the PR zips (2010 on); trades before 2010 have no band data and are left out")
        ent = ent[ent["signal_date"] >= "2010-01-01"]
        tr = exitlab.simulate(ent, bars, f, pols, random_draws=1)
        tr = tr[tr["policy"] != "random_exit"]
        for p in base_pols:
            a = tr[tr["policy"] == p.name][["sid", "signal_date", "net_ret"]]
            b = tr[tr["policy"] == p.name + "+band_low"][["sid", "signal_date", "net_ret", "reason", "hold_days"]]
            m = b.merge(a, on=["sid", "signal_date"], suffixes=("", "_base"))
            m["d"] = m["net_ret"] - m["net_ret_base"]
            st = {}
            for per, mk in (("dev", m["signal_date"].dt.year < SPLIT), ("val", m["signal_date"].dt.year >= SPLIT)):
                d = studies._blk(m[mk], "d")
                se = d.std(ddof=1) / math.sqrt(len(d)) if len(d) > 2 else float("nan")
                st[per] = (float(d.mean()), float(d.mean() / se) if se else float("nan"), int(len(d)))
            fired = float((m["reason"] == "sig_band_low").mean())
            hit = m[m["reason"] == "sig_band_low"]
            line = registry.record(reg, p.name + "+band_low", st["dev"], st["val"], extra={"entry_set": name, "fired_share": fired, "trades": int(len(m)),
                                   "when_fired_mean_diff": float(hit["d"].mean()) if len(hit) else None}, expect=1)
            out.setdefault(name, {})[p.name] = line["verdict"]
            print(f"E11-{name:5s} {p.name+'+band_low':24s} {line['verdict']:12s} dev {st['dev'][0]*100:+.3f}% t {st['dev'][1]:+.1f} | val {st['val'][0]*100:+.3f}% t {st['val'][1]:+.1f} | "
                  f"fired on {fired:.1%} of trades; when fired {hit['d'].mean()*100 if len(hit) else float('nan'):+.2f}% vs holding on", flush=True)
    registry.mirror_to_catalog()
    return out


# ----------------------------------------------------------------------------------------------- P01 indicator-pattern entries

def _indicators() -> pd.DataFrame:
    """RSI(14, Wilder), stochastic %K(14) and a weekly outside-bar flag per stock-day from the adjusted bars; each value uses bars up to that day only."""
    b = pd.read_parquet(paths.gold() / "bars" / "adj_daily.parquet")
    b["date"] = pd.to_datetime(b["date"])
    b = b.sort_values(["sid", "date"])
    d = b.groupby("sid")["c"].diff()
    up, dn = d.clip(lower=0), (-d).clip(lower=0)
    g = b["sid"]
    au = up.groupby(g).transform(lambda x: x.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean())
    ad = dn.groupby(g).transform(lambda x: x.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean())
    b["rsi14"] = 100 - 100 / (1 + au / ad.replace(0, np.nan))
    hh = b.groupby("sid")["h"].transform(lambda x: x.rolling(14, min_periods=14).max())
    ll = b.groupby("sid")["l"].transform(lambda x: x.rolling(14, min_periods=14).min())
    b["stoch14"] = 100 * (b["c"] - ll) / (hh - ll).replace(0, np.nan)
    # weekly outside bar: this week's high/low (5 sessions) engulf the previous 5 sessions' range and the close is in the top quarter
    h5 = b.groupby("sid")["h"].transform(lambda x: x.rolling(5, min_periods=5).max())
    l5 = b.groupby("sid")["l"].transform(lambda x: x.rolling(5, min_periods=5).min())
    ph5, pl5 = h5.groupby(g).shift(5), l5.groupby(g).shift(5)
    b["wk_outside_up"] = ((h5 > ph5) & (l5 < pl5) & (b["c"] >= l5 + 0.75 * (h5 - l5))).astype(float).where(ph5.notna())
    return b[["sid", "date", "rsi14", "stoch14", "wk_outside_up"]]


P01_CONDS = {"rsi_lt30": ("RSI(14) under 30 (oversold)", 1, lambda x: x["rsi14"] < 30), "rsi_gt70": ("RSI(14) over 70 (overbought)", -1, lambda x: x["rsi14"] > 70),
             "stoch_lt20": ("stochastic %K(14) under 20", 1, lambda x: x["stoch14"] < 20), "wk_outside_up": ("weekly outside bar closing in its top quarter", 1, lambda x: x["wk_outside_up"] > 0.5)}


def p01() -> dict:
    ind = _indicators()
    out = {}
    for name in ("BRK", "PULL", "ANY"):
        tr = pd.read_parquet(paths.gold() / "studies" / f"E02-{name}_trades.parquet", columns=["sid", "signal_date", "policy", "net_ret"])
        tr = tr[tr["policy"].isin(POLS) & (tr["signal_date"] >= "2000-01-01")]
        tr = tr.merge(ind, left_on=["sid", "signal_date"], right_on=["sid", "date"], how="left").drop(columns="date")
        reg = registry.register(f"P01-{name}", family="indicator", title=f"Indicator-pattern conditions at entry ({name} entries)",
                                hypothesis="Trades signalled while the indicator condition is on earn a different net return than when it is off (direction per condition), within quarters.",
                                variants=[f"{c}|{p}" for c in P01_CONDS for p in POLS], note="RSI, stochastic and weekly outside bar from adjusted bars; quarter blocks")
        for c, (desc, ex, rule) in P01_CONDS.items():
            src = {"rsi_lt30": "rsi14", "rsi_gt70": "rsi14", "stoch_lt20": "stoch14", "wk_outside_up": "wk_outside_up"}[c]
            tr["cond_" + c] = rule(tr).astype(float).where(tr[src].notna())
            for p in POLS:
                x = tr[tr["policy"] == p]
                dev = _qdiff(x[x["signal_date"].dt.year < SPLIT], "cond_" + c)
                val = _qdiff(x[x["signal_date"].dt.year >= SPLIT], "cond_" + c)
                line = registry.record(reg, f"{c}|{p}", dev[:3], val[:3], extra={"entry_set": name, "dev": dev[3], "val": val[3]}, expect=ex)
                out[f"{name}|{c}|{p}"] = line["verdict"]
                if p in ("hold_20d", "hold_60d"):
                    print(f"P01-{name:5s} {c:14s} {p:9s} {line['verdict']:12s} dev {dev[0]*100:+.2f}% t {dev[1]:+.1f} q{dev[2]} | val {val[0]*100:+.2f}% t {val[1]:+.1f} q{val[2]}", flush=True)
    registry.mirror_to_catalog()
    return out
