"""Registered studies. Each runs on dev (2000-2017) and validation (2018-2023) only; sealed years are not loadable from here.

  python -m india.studies e02 [max_signals]     exit bake-off on three fixed entry sets, every policy against random exits
  python -m india.studies e01 [max_signals]     stop-distance space (M-06): how far should the first stop sit?

Entry sets are fixed before any exit is looked at: they exist only to give the exit policies something to exit.
  BRK   close breaks the 20-day high on volume above 1.5x its 20-day average, price above its 200-day average
  PULL  uptrend (above 200-day) pulled back 5% or more under its 20-day average
  ANY   a plain draw of liquid stocks on random dates (the null entry: exits matter even when the entry is no good)
Max one signal per stock per 10 sessions; top 250 by liquidity rank; a fixed seeded sample so a rerun gives the same answer.
"""
from __future__ import annotations

import json
import math
import sys
import time

import numpy as np
import pandas as pd

from india import catalog, exitlab, paths, registry

SPLIT_YEAR = 2018


def _blk(g: pd.DataFrame, col: str) -> pd.Series:
    """Quarter means. Holds run up to 60 sessions, so trades signalled on neighbouring days overlap and share their outcome; counting each date as an independent observation
    inflates every t-statistic. Quarter blocks are (almost) non-overlapping for the longest hold, so all t-stats in this file are computed across quarter means."""
    return g.groupby(g["signal_date"].dt.to_period("Q"))[col].mean()


def load_features() -> pd.DataFrame:
    f = pd.read_parquet(paths.gold() / "features" / "daily.parquet")
    f["date"] = pd.to_datetime(f["date"])
    return f[f["date"] < "2024-01-01"]  # belt and braces: the lab tables stop at 2023 already


def entry_sets(f: pd.DataFrame, max_signals: int, seed: int = 11) -> dict[str, pd.DataFrame]:
    liq = f[(f["liq_rank"] <= 250) & f["atr14"].notna() & f["dist_sma200"].notna()]
    sets = {
        "BRK": liq[liq["breakout20"] & (liq["vol_ratio20"] > 1.5) & (liq["dist_sma200"] > 0)],
        "PULL": liq[(liq["dist_sma200"] > 0) & (liq["dist_sma20"] < -0.05)],
        "ANY": liq,
    }
    out = {}
    for k, d in sets.items():
        d = d[d["date"] <= "2023-09-30"].sort_values(["sid", "date"])  # leave 60 sessions of room for the longest exit
        keep, last = [], {}
        for sid, dt_ in zip(d["sid"].values, d["date"].values):
            if sid not in last or (dt_ - last[sid]).astype("timedelta64[D]").astype(int) >= 14:
                keep.append(True)
                last[sid] = dt_
            else:
                keep.append(False)
        d = d[np.array(keep)]
        if len(d) > max_signals:
            d = d.sample(max_signals, random_state=seed)
        out[k] = d[["sid", "date"]].rename(columns={"date": "signal_date"}).reset_index(drop=True)
    return out


def paired_vs_null(trades: pd.DataFrame, pol: str) -> dict:
    """Per period: policy net return minus the time-matched null (same entry, stop and holding time, no exit skill), averaged by date, t on dates."""
    res = {}
    t = trades[trades["policy"] == pol].copy()
    t["period"] = np.where(t["signal_date"].dt.year < SPLIT_YEAR, "dev", "val")
    t["d"] = t["net_ret"] - t["null_net_ret"]
    for per, g in t.groupby("period"):
        d = _blk(g, "d")
        se = d.std(ddof=1) / math.sqrt(len(d)) if len(d) > 2 else float("nan")
        res[per] = (float(d.mean()), float(d.mean() / se) if se else float("nan"), int(len(d)))
    return res


def e02(max_signals: int = 4000) -> dict:
    t0 = time.time()
    f = load_features()
    sets = entry_sets(f, max_signals)
    bars = exitlab.load_bars()
    pols = exitlab.DEFAULT_POLICIES
    reg_cache = {}
    summary = {}
    for name, ent in sets.items():
        study = f"E02-{name}"
        reg_cache[name] = registry.register(
            study, family="exit", title=f"Exit bake-off on {name} entries",
            hypothesis="An exit policy earns more than the time-matched null (same entry, same stop, held as long, no exit rule), net of Indian costs, in both the dev and validation years.",
            variants=[p.name for p in pols], note=f"signals {len(ent)}; stop {exitlab.STOP_ATR} ATR; horizon {exitlab.HORIZON}; split {SPLIT_YEAR}")
        tr = exitlab.simulate(ent, bars, f, pols)
        (paths.gold() / "studies").mkdir(parents=True, exist_ok=True)
        tr.to_parquet(paths.gold() / "studies" / f"{study}_trades.parquet")
        summ = exitlab.summarise(tr, SPLIT_YEAR)
        summ.to_csv(paths.gold() / "studies" / f"{study}_summary.csv", index=False)
        rows = []
        for p in pols:
            pr = paired_vs_null(tr, p.name)
            if "dev" not in pr or "val" not in pr:
                continue
            line = registry.record(reg_cache[name], p.name, pr["dev"], pr["val"], extra={"entry_set": name}, expect=1)
            s = summ[summ["policy"] == p.name].set_index("period")
            rows.append({"policy": p.name, "verdict": line["verdict"], "dev_vs_null": round(pr["dev"][0] * 100, 2), "dev_t": round(pr["dev"][1], 2),
                         "val_vs_null": round(pr["val"][0] * 100, 2), "val_t": round(pr["val"][1], 2),
                         "val_capture": round(float(s.loc["val", "capture_median"]), 2) if "val" in s.index else None,
                         "val_giveback_R": round(float(s.loc["val", "giveback_R_median"]), 2) if "val" in s.index else None,
                         "val_p5": round(float(s.loc["val", "p5_net_ret"]) * 100, 1) if "val" in s.index else None})
        summary[name] = {"signals": int(len(ent)), "rows": rows}
        print(name, "signals", len(ent), "trades", len(tr), "skipped(halt/jump)", tr.attrs.get("skipped_data_hygiene"), f"{time.time()-t0:.0f}s", flush=True)
        print(pd.DataFrame(rows).to_string(index=False), flush=True)
    registry.mirror_to_catalog()
    catalog.heartbeat("studies.e02", True, f"{max_signals}")
    (paths.gold() / "studies" / "E02_latest.json").write_text(json.dumps(summary, default=str, indent=1))
    return summary


def e01(max_signals: int = 4000) -> dict:
    """Stop distance (M-06): same entries, 20-session hold with the stop at k ATR below entry. Each k is judged against the 2-ATR stop, paired by date."""
    f = load_features()
    sets = entry_sets(f, max_signals)
    bars = exitlab.load_bars()
    grid = (1.0, 1.5, 3.0, 4.0, 6.0)
    out = {}
    for name, ent in sets.items():
        study = f"E01-{name}"
        reg = registry.register(study, family="stop", title=f"Stop distance on {name} entries",
                                hypothesis="A different initial stop distance than 2 ATR changes net return per trade over a 20-session hold.",
                                variants=[f"stop_{k}atr" for k in grid], note="metric: net return, paired by date against the 2-ATR stop; R and stopped-out share reported")
        pol = [exitlab.Policy("hold_20d", "hold", 20)]
        res = {}
        for k in (2.0,) + grid:
            exitlab.STOP_ATR = k
            tr = exitlab.simulate(ent, bars, f, pol, random_draws=1)
            res[k] = tr[tr["policy"] == "hold_20d"].copy()
        exitlab.STOP_ATR = 2.0
        base = res[2.0]
        out[name] = {}
        for k in grid:
            tr = res[k]
            m = tr.merge(base[["sid", "signal_date", "net_ret"]], on=["sid", "signal_date"], suffixes=("", "_base"))
            m["diff"] = m["net_ret"] - m["net_ret_base"]
            stats = {}
            for per, mask in (("dev", m["signal_date"].dt.year < SPLIT_YEAR), ("val", m["signal_date"].dt.year >= SPLIT_YEAR)):
                g = m[mask]
                d = _blk(g, "diff")
                se = d.std(ddof=1) / math.sqrt(len(d)) if len(d) > 2 else float("nan")
                stats[per] = (float(d.mean()), float(d.mean() / se) if se else float("nan"), int(len(d)))
                stats[per + "_extra"] = {"net_ret": float(g["net_ret"].mean()), "R_net": float(g["r_net"].mean()), "stopped": float((g["reason"] == "stop").mean()), "p5": float(g["net_ret"].quantile(0.05))}
            line = registry.record(reg, f"stop_{k}atr", stats["dev"], stats["val"], extra={"entry_set": name, "dev": stats["dev_extra"], "val": stats["val_extra"]})
            out[name][k] = {"dev": stats["dev"], "val": stats["val"], "verdict": line["verdict"], "val_extra": stats["val_extra"]}
            print(name, f"stop {k} ATR", "dev diff %.3f%% t %.2f" % (stats["dev"][0] * 100, stats["dev"][1]), "val diff %.3f%% t %.2f" % (stats["val"][0] * 100, stats["val"][1]),
                  "stopped(val) %.0f%%" % (stats["val_extra"]["stopped"] * 100), "R_net(val) %.2f" % stats["val_extra"]["R_net"], line["verdict"], flush=True)
    registry.mirror_to_catalog()
    catalog.heartbeat("studies.e01", True, f"{max_signals}")
    return out


def e03(max_signals: int = 8000) -> dict:
    """E03 turn warnings and E07 level-break exits: the loose 4-ATR trail alone against the same trail plus one extra exit signal, paired trade by trade.
    A signal helps if it lifts net return and cuts giveback without throwing away the big winners (capture and the 95th percentile are reported)."""
    f = load_features()
    sets = entry_sets(f, max_signals)
    bars = exitlab.load_bars()
    pols = exitlab.TURN_POLICIES
    level_break = {"prev_low", "low20", "hold60+low20", "hold60+prev_low"}
    out = {}
    for name, ent in sets.items():
        tr = exitlab.simulate(ent, bars, f, pols, random_draws=1)
        tr = tr[tr["policy"] != "random_exit"]
        (paths.gold() / "studies").mkdir(parents=True, exist_ok=True)
        tr.to_parquet(paths.gold() / "studies" / f"E03-{name}_trades.parquet")
        base = tr[tr["policy"] == "trail4"][["sid", "signal_date", "net_ret", "giveback_r", "capture", "hold_days"]].rename(columns={"net_ret": "b_net", "giveback_r": "b_gb", "capture": "b_cap", "hold_days": "b_days"})
        regs = {}
        for p in pols:
            if p.name == "trail4":
                continue
            study = f"{'E07' if any(x in level_break for x in (p.name, p.name.split('+')[-1])) else 'E03'}-{name}"
            if study not in regs:
                sig_names = [q.name for q in pols if q.name != "trail4" and (('E07' if q.name in level_break or q.name.split('+')[-1] in level_break else 'E03') == study.split('-')[0])]
                regs[study] = registry.register(study, family="exit", title=f"Extra exit signals on {name} entries ({study.split('-')[0]})",
                                                hypothesis="Adding this signal as an extra exit to a loose 4-ATR trail (or a 60-day hold) raises net return per trade, paired by trade, in both dev and validation.",
                                                variants=sig_names, note=f"signals {len(ent)}; baseline trail4; split {SPLIT_YEAR}")
            g = tr[tr["policy"] == p.name].merge(base, on=["sid", "signal_date"])
            ref = g if not p.name.startswith("hold60") else g  # hold60 variants are compared with the same trail4 baseline: it is the policy under test elsewhere
            g["d"] = g["net_ret"] - g["b_net"]
            stats = {}
            for per, mask in (("dev", g["signal_date"].dt.year < SPLIT_YEAR), ("val", g["signal_date"].dt.year >= SPLIT_YEAR)):
                x = g[mask]
                d = _blk(x, "d")
                se = d.std(ddof=1) / math.sqrt(len(d)) if len(d) > 2 else float("nan")
                stats[per] = (float(d.mean()), float(d.mean() / se) if se else float("nan"), int(len(d)))
                stats[per + "_x"] = {"net": float(x["net_ret"].mean()), "giveback_med": float(x["giveback_r"].median()), "capture_med": float(x["capture"].median()), "days": float(x["hold_days"].mean()),
                                     "p95": float(x["net_ret"].quantile(0.95)), "base_net": float(x["b_net"].mean()), "base_giveback_med": float(x["b_gb"].median()), "base_days": float(x["b_days"].mean())}
            reg = regs[study]
            line = registry.record(reg, p.name, stats["dev"], stats["val"], extra={"entry_set": name, "dev": stats["dev_x"], "val": stats["val_x"]}, expect=1)
            v = stats["val_x"]
            print(f"{study:10s} {p.name:22s} {line['verdict']:12s} dev {stats['dev'][0]*100:+.2f}% t {stats['dev'][1]:+.1f} | val {stats['val'][0]*100:+.2f}% t {stats['val'][1]:+.1f} | days {v['days']:.1f} vs {v['base_days']:.1f} | "
                  f"giveback {v['giveback_med']:.2f} vs {v['base_giveback_med']:.2f} | p95 {v['p95']*100:.1f}%", flush=True)
            out.setdefault(name, {})[p.name] = {"dev": stats["dev"], "val": stats["val"], "verdict": line["verdict"]}
    registry.mirror_to_catalog()
    catalog.heartbeat("studies.e03", True, str(max_signals))
    return out


def market_gates(f: pd.DataFrame) -> pd.DataFrame:
    """Date-level gates, each known at that day's close. breadth200 = share of the 500 most liquid stocks above their own 200-day average (from the lab features);
    nifty50 = Nifty 50 above its own 50-day average, when the index silver exists."""
    g = f.groupby("date")["dist_sma200"].apply(lambda x: float((x > 0).mean())).rename("breadth200").to_frame()
    g["breadth_gt50"] = g["breadth200"] > 0.5
    g["breadth_gt60"] = g["breadth200"] > 0.6
    p = paths.data_dir() / "silver/kite_index/day/day.parquet"
    if p.exists():
        ix = pd.read_parquet(p)
        ix = ix[ix["index_name"] == "NIFTY 50"].sort_values("ts")
        ix["date"] = pd.to_datetime(ix["ts"].dt.date)
        ix = ix.set_index("date")["close"]
        n50 = (ix > ix.rolling(50).mean()).rename("nifty_gt50d")
        n200 = (ix > ix.rolling(200).mean()).rename("nifty_gt200d")
        g = g.join(n50).join(n200)
    g.index = pd.to_datetime(g.index)
    return g


def e08(max_signals: int = 8000) -> dict:
    """E08 market gate on entries: do trades signalled while the gate is on earn more than those signalled while it is off? Uses the E02 trade files, so the entries and exits are
    the ones already registered. Within each quarter that has both, on-mean minus off-mean; t across quarters. A gate is only interesting if it helps in both dev and validation."""
    f = load_features()
    gates = market_gates(f)
    pols = ["hold_20d", "hold_60d", "atr_trail_4", "sma_close_50", "swing_low_20"]
    out = {}
    for name in ("BRK", "PULL", "ANY"):
        tp = paths.gold() / "studies" / f"E02-{name}_trades.parquet"
        tr = pd.read_parquet(tp)
        tr = tr[tr["policy"].isin(pols)].merge(gates.reset_index().rename(columns={"index": "date"}), left_on="signal_date", right_on="date", how="left")
        reg = registry.register(f"E08-{name}", family="gate", title=f"Market gates on {name} entries", hypothesis="Trades signalled while the gate is on earn more net than trades signalled while it is off, in dev and validation.",
                                variants=[f"{g}|{p}" for g in gates.columns if g.endswith(("gt50", "gt60", "gt50d", "gt200d")) for p in pols], note="quarter blocks: on-mean minus off-mean within quarters having both; t across quarters")
        for gname in [c for c in gates.columns if c.endswith(("gt50", "gt60", "gt50d", "gt200d"))]:
            for p in pols:
                x = tr[(tr["policy"] == p) & tr[gname].notna()]
                stats = {}
                for per, mask in (("dev", x["signal_date"].dt.year < SPLIT_YEAR), ("val", x["signal_date"].dt.year >= SPLIT_YEAR)):
                    y = x[mask]
                    qm = y.assign(q=y["signal_date"].dt.to_period("Q"), on=y[gname].astype(bool)).groupby(["q", "on"])["net_ret"].mean().unstack().dropna()
                    if len(qm) < 3 or True not in qm.columns or False not in qm.columns:
                        stats[per] = (float("nan"), float("nan"), int(len(qm)))
                        continue
                    diff = qm[True] - qm[False]
                    se = diff.std(ddof=1) / math.sqrt(len(diff))
                    stats[per] = (float(diff.mean()), float(diff.mean() / se) if se else float("nan"), int(len(diff)))
                line = registry.record(reg, f"{gname}|{p}", stats["dev"], stats["val"], extra={"entry_set": name, "share_on_val": float(x[x["signal_date"].dt.year >= SPLIT_YEAR][gname].astype(float).mean())}, expect=1)
                out.setdefault(name, {})[f"{gname}|{p}"] = (stats, line["verdict"])
                print(f"E08-{name:5s} {gname:13s} {p:13s} {line['verdict']:12s} dev on-off {stats['dev'][0]*100:+.2f}% t {stats['dev'][1]:+.1f} | val {stats['val'][0]*100:+.2f}% t {stats['val'][1]:+.1f}", flush=True)
    registry.mirror_to_catalog()
    return out


if __name__ == "__main__":
    paths.ensure()
    which = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
    {"e02": e02, "e01": e01, "e03": e03, "e08": e08}[which](n)
