"""Filters judged against the unfiltered baseline, on live paper records. CURRENT-MARKET OBSERVATION, not a backtest: the rows are paper trades on real
prices from 19 Oct 2026 on, and the numbers mean little until each side has dozens of closed trades.

  python -m india.filters          every condition in india/conditions.py, on and off, per campaign and exit policy, from paper/baseline.parquet
Writes catalog table paper_filter_slices and paper/filter_slices.csv. The historical verdict for the same condition (from the registry) is printed beside it,
so a filter is only adopted when history and the live record point the same way and Madhav approves it.
"""
from __future__ import annotations

import json
import sys

import pandas as pd

from india import catalog, conditions, paths

MAP_CTX = {"breadth200": "breadth200", "nifty_vs_sma50": "nifty_vs_sma50", "nifty_vs_sma200": "nifty_vs_sma200", "vix_close": "vix", "vix_vs_sma50": "vix_vs_sma50",
           "small_ratio_vs_sma50": "small_ratio_vs_sma50"}


def _contexts() -> pd.DataFrame:
    rows = []
    for p in sorted((paths.data_dir() / "paper" / "decisions").glob("????-??-??.json")):
        body = json.loads(p.read_text())
        ctx = body.get("context")
        if ctx is None:
            jp = p.with_name(p.stem + ".journal.json")
            ctx = json.loads(jp.read_text()).get("context", {}) if jp.exists() else {}
        rows.append({"signal_date": p.stem, **{v: ctx.get(k) for k, v in MAP_CTX.items()}})
    return pd.DataFrame(rows)


def _verdicts() -> dict:
    lp = paths.manifest_dir() / "test_ledger.jsonl"
    out = {}
    if lp.exists():
        for line in lp.read_text().splitlines():
            r = json.loads(line)
            if r.get("kind") == "result" and "|" in r.get("variant", ""):
                out[(r["study"].split("-")[1] if "-" in r["study"] else "", r["variant"])] = r["verdict"]
    return out


def run() -> pd.DataFrame:
    bp = paths.data_dir() / "paper" / "baseline.parquet"
    if not bp.exists():
        print("no baseline book yet: the first fill is the session after the first decision")
        return pd.DataFrame()
    b = pd.read_parquet(bp)
    b = b[b["status"] == "closed"].copy()
    if b.empty:
        print("baseline book has no closed trades yet")
        return pd.DataFrame()
    for c in [c for c in b.columns if c.startswith("f_")]:
        b[c[2:]] = b[c]
    ctx = _contexts()
    b = b.merge(ctx, on="signal_date", how="left")
    sc = conditions.apply_stock(b)
    mc = conditions.apply_market(b[[v for v in MAP_CTX.values() if v in b.columns]].assign(
        **{k: float("nan") for k in ("usdinr_vs_sma50", "brent_vs_sma50", "nasdaq_vs_sma200", "us10y_chg60")}))
    flags = pd.concat([sc, mc], axis=1)
    hist = _verdicts()
    rows = []
    for c in flags.columns:
        name = c[5:]
        for (camp, pol), g in b.groupby(["campaign", "policy"]):
            f = flags.loc[g.index, c]
            on, off = g[f > 0.5], g[f < 0.5]
            rows.append({"condition": name, "campaign": camp, "policy": pol, "n_on": len(on), "n_off": len(off), "n_missing": int(f.isna().sum()),
                         "mean_on": on["net_ret"].mean() if len(on) else None, "mean_off": off["net_ret"].mean() if len(off) else None,
                         "historical": hist.get(({"CTL": "ANY"}.get(camp, camp), f"{name}|{pol}"), "")})
    out = pd.DataFrame(rows)
    out.to_csv(paths.data_dir() / "paper" / "filter_slices.csv", index=False)
    con = catalog.connect()
    con.register("x", out)
    con.execute("create or replace table paper_filter_slices as select * from x")
    con.close()
    print(out.to_string(index=False))
    return out


if __name__ == "__main__":
    paths.ensure()
    run()
