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


def paired_vs_random(trades: pd.DataFrame, pol: str) -> dict:
    """Per period: mean of (policy net return - random-exit net return) over date-means, with a t-stat on dates."""
    res = {}
    t = trades.copy()
    t["period"] = np.where(t["signal_date"].dt.year < SPLIT_YEAR, "dev", "val")
    for per, g in t.groupby("period"):
        a = g[g["policy"] == pol].groupby("signal_date")["net_ret"].mean()
        b = g[g["policy"] == "random_exit"].groupby("signal_date")["net_ret"].mean()
        d = (a - b).dropna()
        se = d.std(ddof=1) / math.sqrt(len(d)) if len(d) > 2 else float("nan")
        res[per] = (float(d.mean()) if len(d) else float("nan"), float(d.mean() / se) if se else float("nan"), int(len(d)))
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
            hypothesis="Some exit policy keeps more of the move and gives back less than exiting on a random day, net of Indian costs, in both the dev and validation years.",
            variants=[p.name for p in pols], note=f"signals {len(ent)}; stop {exitlab.STOP_ATR} ATR; horizon {exitlab.HORIZON}; split {SPLIT_YEAR}")
        tr = exitlab.simulate(ent, bars, f, pols)
        (paths.gold() / "studies").mkdir(parents=True, exist_ok=True)
        tr.to_parquet(paths.gold() / "studies" / f"{study}_trades.parquet")
        summ = exitlab.summarise(tr, SPLIT_YEAR)
        summ.to_csv(paths.gold() / "studies" / f"{study}_summary.csv", index=False)
        rows = []
        for p in pols:
            pr = paired_vs_random(tr, p.name)
            if "dev" not in pr or "val" not in pr:
                continue
            line = registry.record(reg_cache[name], p.name, pr["dev"], pr["val"], extra={"entry_set": name})
            s = summ[summ["policy"] == p.name].set_index("period")
            rows.append({"policy": p.name, "verdict": line["verdict"], "dev_excess": round(pr["dev"][0] * 100, 2), "dev_t": round(pr["dev"][1], 2),
                         "val_excess": round(pr["val"][0] * 100, 2), "val_t": round(pr["val"][1], 2),
                         "val_capture": round(float(s.loc["val", "capture_median"]), 2) if "val" in s.index else None,
                         "val_giveback_R": round(float(s.loc["val", "giveback_R_median"]), 2) if "val" in s.index else None,
                         "val_p5": round(float(s.loc["val", "p5_net_ret"]) * 100, 1) if "val" in s.index else None})
        summary[name] = {"signals": int(len(ent)), "rows": rows}
        print(name, "signals", len(ent), "trades", len(tr), f"{time.time()-t0:.0f}s", flush=True)
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
                d = g.groupby("signal_date")["diff"].mean()
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


if __name__ == "__main__":
    paths.ensure()
    which = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
    {"e02": e02, "e01": e01}[which](n)
