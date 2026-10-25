"""Forward evidence for the teacher stock cards that passed their backtest (india/teachers.py, run of 25 Oct 2026).

Every session from FORWARD_START, each surviving rule is applied to the liquid 500 exactly as in the backtest (same features, same base set, same
on/off split, same outcome), and the outcome is scored once its horizon has passed. Nothing is traded: these are signal logs, the forward half of
the evidence. The statistic is the backtest's own: mean outcome when the rule's condition holds minus when it does not, per session, with the
running count of scored sessions. First read at 20 scored sessions (the staircase convention), never a verdict before.

Data: the paper engine's own lookback (india.paper.load_adjusted: series-EQ rows of the last ~460 days, adjusted for corporate actions), the same
read the stock practice book makes every evening. Only sessions on or after FORWARD_START are scored, so the sealed 2024-2026 years stay closed to
research.

  python -m india.teacher_live run      rebuild the forward log from the lookback -> paper/teachers/live_signals.parquet + live_summary.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from india import costs, paper, paths
from india import teachers_stock as ts

FORWARD_START = "2026-10-26"
FIRST_READ = 20
TOP = 500

# (card, variant, expect, outcome column, horizon in sessions, plain words) — the surviving variants of the 25 Oct run, nothing else
TRACK = [
    ("TWT-H10", "gt8|net20", -1, "net20", 20, "Uptrend stocks more than 8% above their 50-day average earn less over the next 20 sessions than ones within 5% of it"),
    ("TWT-H10", "gt10|net20", -1, "net20", 20, "Same, more than 10% above"),
    ("TWT-H10", "gt15|net20", -1, "net20", 20, "Same, more than 15% above"),
    ("TWT-H10", "gt15|minfwd60", -1, "minfwd60", 60, "Stocks more than 15% above their 50-day average fall deeper over the next 60 sessions"),
    ("TWT-H11", "vol1.5|fail5", -1, "fail5", 5, "Breakouts on 1.5x normal volume fall back under the breakout level within 5 sessions less often"),
    ("TWT-H12", "good|fail5", -1, "fail5", 5, "Breakout days that close near the top of a wide bar fall back less often"),
    ("TWT-H15", "deep|fall40", 1, "fall40", 120, "Stocks 40%+ below their high and under the 200-day average more often fall another 40%"),
    ("TWT-H18", "quiet_hold|newhigh15", 1, "pb3_newhigh15", 15, "After a breakout, quiet pullbacks that hold the level make a new high within 15 sessions more often"),
    ("TWT-H18", "shallow|newhigh15", 1, "pb3_newhigh15", 15, "After a breakout, shallow pullbacks make a new high within 15 sessions more often"),
]


def pdir():
    d = paths.data_dir() / "paper" / "teachers"
    d.mkdir(parents=True, exist_ok=True)
    return d


def panel() -> pd.DataFrame:
    df = paper.load_adjusted()
    df = df[~df["is_fund"]]
    df["turnover"] = df["turnover"].fillna(df["close"] * df["volume"])
    med = df.groupby("sid")["turnover"].transform(lambda x: x.rolling(60, min_periods=20).median())
    df["liq_rank"] = med.groupby(df["date"]).rank(ascending=False, method="first")
    parts = []
    for sid, g0 in df.sort_values(["sid", "date"]).groupby("sid", sort=False):
        if len(g0) < 210:
            continue
        g = pd.DataFrame({"date": g0["date"].values, "o": g0["adj_open"].values, "h": g0["adj_high"].values, "l": g0["adj_low"].values,
                          "c": g0["adj_close"].values, "volume": g0["volume"].values, "symbol": g0["symbol"].values, "liq_rank": g0["liq_rank"].values})
        pc = g["c"].shift(1)
        tr = pd.concat([g["h"] - g["l"], (g["h"] - pc).abs(), (g["l"] - pc).abs()], axis=1).max(axis=1)
        g["atr14"] = tr.rolling(14, min_periods=14).mean()
        g.index = range(len(g))
        f = ts._per_stock(g, pd.Series(1.0, index=pd.DatetimeIndex(g["date"].unique())))
        parts.append(pd.concat([g, f], axis=1).assign(sid=sid))
    p = pd.concat(parts, ignore_index=True)
    p = p[(p["date"] >= FORWARD_START) & (p["liq_rank"] <= TOP)].copy()
    p["rank_b"] = (p["liq_rank"] // 50 * 50 + 25).clip(upper=500)
    cst = {r: costs.round_trip("delivery", 50_000, 50_000, year=int(p["date"].dt.year.max()) if len(p) else 2026, turnover_rank=int(r))["total"] / 50_000
           for r in p["rank_b"].unique()}
    p["cost"] = p["rank_b"].map(cst)
    p["net20"] = p["fwd20"] - p["cost"]
    p["fail5"] = ((1 + p["fwd_minc5"]) * p["c"] < p["hi60_prev"]).astype(float).where(p["fwd_minc5"].notna())
    p["fall40"] = (p["minfwd120"] <= -0.40).astype(float).where(p["minfwd120"].notna())
    return p


def groups(p: pd.DataFrame) -> dict:
    """(base, on) masks per tracked variant, as in india/teachers.py (stock cards). Breakouts: close above the prior 60-session high, one per stock per 10 sessions."""
    brk = ts._cooldown(p, p["c"] > p["hi60_prev"], 10)
    up = (p["dist_sma50"] > 0) & (p["dist_sma200"] > 0)
    near = p["dist_sma50"] <= 0.05
    good = (p["range_vs_max20"] >= 1) & (p["close_pos"] >= 0.75) & (p["upper_wick"] <= 0.15)
    far = p["dist_hi252"] <= -0.40
    out = {}
    for x in (8, 10, 15):
        on = p["dist_sma50"] > x / 100
        out[("TWT-H10", f"gt{x}|net20")] = (up & (on | near), on)
    on = p["dist_sma50"] > 0.15
    out[("TWT-H10", "gt15|minfwd60")] = (up & (on | near), on)
    out[("TWT-H11", "vol1.5|fail5")] = (brk, p["vol50"] > 1.5)
    out[("TWT-H12", "good|fail5")] = (brk, good)
    out[("TWT-H15", "deep|fall40")] = (pd.Series(True, index=p.index), far & (p["dist_sma200"] < 0))
    out[("TWT-H18", "quiet_hold|newhigh15")] = (p["pb3"].astype(bool), p["pb3_good"].astype(bool))
    out[("TWT-H18", "shallow|newhigh15")] = (p["pb3"].astype(bool), p["pb3_shallow"].astype(bool))
    return out


def run() -> dict:
    p = panel()
    rows, summ = [], {"forward_start": FORWARD_START, "first_read_sessions": FIRST_READ, "data_through": str(p["date"].max().date()) if len(p) else None, "rules": []}
    G = groups(p) if len(p) else {}
    for card, var, expect, col, hz, words in TRACK:
        base, on = G.get((card, var), (None, None))
        if base is None:
            summ["rules"].append({"card": card, "variant": var, "words": words, "signals": 0, "scored_sessions": 0, "stage": "no sessions yet"})
            continue
        b = p[base.reindex(p.index, fill_value=False).astype(bool)]
        o = on.reindex(b.index).fillna(False).astype(bool)
        for (d, sym, grp, y) in zip(b["date"], b["symbol"], o, b[col]):
            rows.append({"date": d, "card": card, "variant": var, "symbol": sym, "group": "on" if grp else "off", "outcome": None if y != y else float(y)})
        sc = b.assign(_on=o, _y=b[col]).dropna(subset=["_y"])
        per = sc.groupby(["date", "_on"])["_y"].mean().unstack()
        diffs = (per.get(True) - per.get(False)).dropna() if per is not None and True in per and False in per else pd.Series(dtype=float)
        n = int(len(diffs))
        summ["rules"].append({"card": card, "variant": var, "expect": expect, "words": words, "horizon": hz, "signals": int(o.sum()), "base_rows": int(len(b)),
                              "scored_sessions": n, "mean_on_minus_off": float(diffs.mean()) if n else None,
                              "right_way_sessions": int(((diffs > 0) if expect > 0 else (diffs < 0)).sum()) if n else 0,
                              "stage": "first read due" if n >= FIRST_READ else f"{n} of {FIRST_READ} scored sessions (outcomes need {hz} sessions to mature)"})
    pd.DataFrame(rows).to_parquet(pdir() / "live_signals.parquet", index=False)
    (pdir() / "live_summary.json").write_text(json.dumps(summ, indent=1, default=str))
    print(json.dumps({k: v for k, v in summ.items() if k != "rules"}), flush=True)
    for r in summ["rules"]:
        print(f"{r['card']} {r['variant']:22s} signals {r.get('signals', 0):5d} scored {r['scored_sessions']:3d} · {r['stage']}", flush=True)
    return summ


if __name__ == "__main__":
    if (sys.argv[1] if len(sys.argv) > 1 else "run") == "run":
        run()
