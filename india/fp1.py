"""FP1 (29 Oct 2026, Phase 3.3 of the reverse-engineering plan): monthly factor portfolios for the long-term money.

Spec india/registrations/fp1_v1.json, written before any outcome was read. 12-month momentum, low volatility and the two combined; top decile
of the 500 most traded names, equal weight, rebalanced at each month-end; against the equal-weight universe and the Nifty 500; after delivery
costs and the half-spread on the weight that turns over. A random decile is the negative control.

  python -m india.fp1 check          month counts per period only (no means, no t, no verdicts)
  python -m india.fp1 run            register with the spec's frozen k, compute, record; manifests/lab5_fp1.json and registrations/fp1_results_v1.md
  python -m india.fp1 table          rewrite the results page from the manifest

Research rows only (2000-2023); nothing from 2024 on, no sealed folder.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from india import costs, paths, registry
from india.lab3 import _clean, _f

REG_DIR = Path(__file__).resolve().parent / "registrations"
SPLIT = 2018
START, END = "2000-01-01", "2023-12-31"
DECILE = 0.10
SEED = 20261029
JUMP = 0.40


def spec() -> dict:
    return json.loads((REG_DIR / "fp1_v1.json").read_text())


def _stat(x: pd.Series) -> tuple[float, float, int]:
    x = pd.Series(x).dropna()
    if len(x) < 3:
        return (float("nan"), float("nan"), int(len(x)))
    se = x.std(ddof=1) / math.sqrt(len(x))
    return (float(x.mean()), float(x.mean() / se) if se else float("nan"), int(len(x)))


def month_table() -> pd.DataFrame:
    """One row per (month_end, sid): close, next month-end close, 12-1 momentum, 252-session volatility, rank, a jump flag."""
    D = paths.data_dir()
    con = duckdb.connect()
    con.execute(f"create table b as select sid, date, c from read_parquet('{D / 'gold/bars/adj_daily.parquet'}') where c > 0 and date >= DATE '1998-01-01' and date <= DATE '{END}'")
    con.execute(f"create table u as select sid, date, rank from read_parquet('{D / 'gold/universe/u_liq_in.parquet'}') where top500")
    con.execute("""create table d0 as
        select sid, date, c, c / lag(c) over w - 1 as r1, row_number() over w as n, date_trunc('month', date) as m
        from b window w as (partition by sid order by date)""")
    con.execute("""create table d as
        select sid, date, c, r1, n, m,
               stddev_samp(r1) over (partition by sid order by date rows between 251 preceding and current row) as vol252,
               max(abs(r1)) over (partition by sid order by date rows between 251 preceding and current row) as maxjump252
        from d0""")
    con.execute("""create table me as
        select sid, m, max(date) as date from d group by sid, m""")
    con.execute("""create table mt as
        select me.sid, me.m, me.date, d.c, d.vol252, d.maxjump252, d.n,
               lag(d.c, 1) over (partition by me.sid order by me.m) as c_prev1,
               lag(d.c, 12) over (partition by me.sid order by me.m) as c_prev12,
               lead(d.c, 1) over (partition by me.sid order by me.m) as c_next,
               lead(me.m, 1) over (partition by me.sid order by me.m) as m_next
        from me join d on d.sid = me.sid and d.date = me.date""")
    # the month-end session's universe rank; a stock's month-ends are consecutive calendar months only when it traded both (guard on m_next)
    df = con.execute(f"""select mt.*, u.rank from mt join u on u.sid = mt.sid and u.date = mt.date
                         where mt.date >= DATE '{START}' and mt.date <= DATE '{END}'""").df()
    con.close()
    df["m"] = pd.to_datetime(df["m"])
    df["m_next"] = pd.to_datetime(df["m_next"])
    consecutive = (df["m_next"].dt.year * 12 + df["m_next"].dt.month) - (df["m"].dt.year * 12 + df["m"].dt.month) == 1
    df["ret_next"] = np.where(consecutive, df["c_next"] / df["c"] - 1, np.nan)   # no next month-end close: closed at the last close (0 after exit)
    df.loc[~consecutive & df["c_next"].isna(), "ret_next"] = 0.0
    df["mom"] = df["c_prev1"] / df["c_prev12"] - 1
    df["eligible"] = (df["c"] >= 10) & (df["n"] >= 252) & df["mom"].notna() & df["vol252"].notna() & (df["maxjump252"] <= JUMP) & df["ret_next"].notna()
    return df


def _index_monthly() -> pd.Series:
    ix = pd.read_parquet(paths.data_dir() / "silver/kite_index/day/day.parquet", columns=["index_name", "date", "close"])
    ix = ix[(ix["index_name"] == "NIFTY 500") & (ix["close"] > 0)]
    ix["date"] = pd.to_datetime(ix["date"])
    ix = ix[ix["date"] <= END].sort_values("date")
    me = ix.groupby(ix["date"].dt.to_period("M")).last()
    r = me["close"].pct_change()
    r.index = r.index.to_timestamp()
    return r


PORTFOLIO_INR = 1_000_000   # the costs are charged on a Rs 10 lakh portfolio: the flat DP charge (Rs 15.34 a sale) matters at small sizes


def _cost_frac(sids_in: set, sids_out: set, weight: float, ranks: dict, when: dt.date) -> float:
    """Cost of the rebalance as a fraction of the portfolio: each name in is bought, each name out is sold, at its weight of a Rs 10 lakh book."""
    v = PORTFOLIO_INR * weight
    total = 0.0
    for s in sids_in:
        total += costs.half_spread_bps(ranks.get(s)) / 1e4 * v + costs.cost("delivery", "buy", v, when.year, when=when)
    for s in sids_out:
        total += costs.half_spread_bps(ranks.get(s)) / 1e4 * v + costs.cost("delivery", "sell", v, when.year, when=when)
    return total / PORTFOLIO_INR


def portfolios(df: pd.DataFrame) -> pd.DataFrame:
    """Monthly net returns of each portfolio and benchmark."""
    rng = np.random.default_rng(SEED)
    rows = []
    held: dict[str, set] = {}
    for m, g in df[df["eligible"]].groupby("m"):
        g = g.copy()
        n = len(g)
        if n < 100:
            continue
        k = max(int(round(n * DECILE)), 10)
        g["r_mom"] = g["mom"].rank(pct=True)
        g["r_vol"] = (-g["vol252"]).rank(pct=True)
        g["r_combo"] = (g["r_mom"] + g["r_vol"]) / 2
        picks = {
            "MOM": set(g.nlargest(k, "mom")["sid"]),
            "LOWVOL": set(g.nsmallest(k, "vol252")["sid"]),
            "COMBO": set(g.nlargest(k, "r_combo")["sid"]),
            "MOM_bottom": set(g.nsmallest(k, "mom")["sid"]),
            "RANDOM": set(rng.choice(g["sid"].values, size=k, replace=False)),
        }
        ret = dict(zip(g["sid"], g["ret_next"]))
        ranks = dict(zip(g["sid"], g["rank"]))
        when = g["date"].iloc[0].date() if hasattr(g["date"].iloc[0], "date") else pd.Timestamp(g["date"].iloc[0]).date()
        rec = {"m": m, "n_eligible": n, "k": k, "EW": float(g["ret_next"].mean())}
        for name, s in picks.items():
            gross = float(np.mean([ret[x] for x in s]))
            prev = held.get(name, set())
            sids_in, sids_out = (s - prev) if prev else s, (prev - s) if prev else set()
            c = _cost_frac(sids_in, sids_out, 1.0 / k, ranks, when)
            rec[f"{name}_gross"] = gross
            rec[f"{name}_cost"] = c
            rec[name] = gross - c
            rec[f"{name}_turnover"] = (len(sids_in) + len(sids_out)) / (2 * k)
            held[name] = s
        rows.append(rec)
    P = pd.DataFrame(rows).set_index("m").sort_index()
    n500 = _index_monthly()
    # the index return for the month AFTER m (held from m's end to the next month-end)
    P["N500"] = [n500.get(m + pd.offsets.MonthBegin(1), np.nan) for m in P.index]
    return P


def _summary(x: pd.Series) -> dict:
    x = x.dropna()
    if not len(x):
        return {}
    eq = (1 + x).cumprod()
    dd = (eq / eq.cummax() - 1).min()
    yrs = len(x) / 12
    return {"months": int(len(x)), "ann_return": float(eq.iloc[-1] ** (1 / yrs) - 1) if yrs > 0 else None, "ann_vol": float(x.std() * math.sqrt(12)),
            "max_drawdown": float(dd), "worst_3_months": [float(v) for v in x.nsmallest(3)], "best_month": float(x.max())}


def results(counts_only: bool = False) -> dict:
    df = month_table()
    P = portfolios(df)
    out = {}
    s = spec()
    for var in s["variants"]:
        name, bench = var.split("|vs_")
        ex = (P[name] - P[bench]).dropna()
        if counts_only:
            out[var] = {"events_dev": int((ex.index.year < SPLIT).sum()), "events_val": int((ex.index.year >= SPLIT).sum())}
            continue
        q = ex.groupby(ex.index.to_period("Q")).mean()
        dev, val = q[[p.year < SPLIT for p in q.index]], q[[p.year >= SPLIT for p in q.index]]
        extra = {"months": int(len(ex)), "events_dev": int((ex.index.year < SPLIT).sum()), "events_val": int((ex.index.year >= SPLIT).sum()),
                 "mean_excess_monthly": float(ex.mean()), "share_months_ahead": float((ex > 0).mean()),
                 "portfolio": {"dev": _summary(P[name][P.index.year < SPLIT]), "val": _summary(P[name][P.index.year >= SPLIT])},
                 "benchmark": {"dev": _summary(P[bench][P.index.year < SPLIT]), "val": _summary(P[bench][P.index.year >= SPLIT])},
                 "cost_drag_ann": float(P[f"{name}_cost"].mean() * 12), "turnover_monthly": float(P[f"{name}_turnover"].mean()),
                 "gross_ann_return": _summary(P[f"{name}_gross"]).get("ann_return")}
        out[var] = {"dev": _stat(dev), "val": _stat(val), "extra": extra}
    if not counts_only:
        p = paths.gold() / "studies"
        p.mkdir(parents=True, exist_ok=True)
        P.reset_index().to_parquet(p / "FP1_monthly.parquet", index=False)
    return out


def run(rerun_reason: str | None = None) -> dict:
    s = spec()
    k = int(s["bar"]["union_k"])
    if abs(registry.threshold(k) - float(s["bar"]["z"])) > 0.01:
        raise ValueError(f"FP1: the spec's z {s['bar']['z']} does not match k {k}")
    reg = registry.register("FP1", family=s["family"], title=s["title"], hypothesis=s["hypothesis"], variants=list(s["variants"]),
                            note="spec india/registrations/fp1_v1.json (written before the run)", bar_families=s["bar"].get("bar_families"), union_k=k,
                            rerun_reason=rerun_reason)
    res = results()
    rows = []
    for var, expect in s["variants"].items():
        r = res.get(var)
        if r is None:
            line = registry.record(reg, var, (float("nan"), float("nan"), 0), (float("nan"), float("nan"), 0), extra={"missing": True}, expect=expect)
        else:
            line = registry.record(reg, var, tuple(r["dev"]), tuple(r["val"]), extra=_clean(r.get("extra", {})), expect=expect)
        rows.append({"variant": var, "expect": expect, "verdict": line["verdict"], "z": line["z"], "dev": _clean(list(line["dev"])), "val": _clean(list(line["val"])),
                     "extra": _clean(line["extra"])})
    out = {"study": "FP1", "registered_at": reg["at"], "k": k, "rows": rows}
    (paths.manifest_dir() / "lab5_fp1.json").write_text(json.dumps(out, indent=1, default=str))
    registry.mirror_to_catalog()
    table(out)
    return out


TAKEAWAY: list[str] = []   # written after the run, from the table


def table(out: dict | None = None) -> Path:
    if out is None:
        out = json.loads((paths.manifest_dir() / "lab5_fp1.json").read_text())
    s = spec()
    L = [f"# FP1 results: {s['title']}", "", f"Registered {out['registered_at']} (spec `fp1_v1.json`, written before the run); family {s['family']}, "
         f"k = {out['k']}, z = {registry.threshold(out['k']):.2f}. Development 2000-2017, validation 2018-2023; nothing from 2024 on. HISTORICAL BACKTEST, paper only.", "",
         "Monthly excess return of the portfolio over the benchmark, quarter means, t across quarters. Costs: delivery charges of the day and the half-spread "
         "by turnover rank on the weight that changes hands each month. The Nifty 500 is the price index (dividends of about 1.2-1.5% a year are not in it, "
         "which flatters the portfolio by that much against N500 but not against EW).", ""]
    if TAKEAWAY:
        L += ["## In plain words", ""] + TAKEAWAY + [""]
    L += ["## The rows", "", "| variant | expected | verdict | dev mean/mo | dev t | dev q | val mean/mo | val t | val q | months ahead | turnover/mo | cost drag/yr |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in out["rows"]:
        e = r["extra"] or {}
        d, v = r["dev"], r["val"]
        L.append(f"| {r['variant']} | {'+' if r['expect'] > 0 else ('-' if r['expect'] < 0 else '0')} | {r['verdict']} | {_f(d[0])} | {_f(d[1], False)} | {d[2]} | {_f(v[0])} | {_f(v[1], False)} | {v[2]} | "
                 f"{_f(e.get('share_months_ahead')) if e.get('share_months_ahead') is not None else 'n/a'} | {_f(e.get('turnover_monthly')) if e.get('turnover_monthly') is not None else 'n/a'} | "
                 f"{_f(e.get('cost_drag_ann')) if e.get('cost_drag_ann') is not None else 'n/a'} |")
    L += ["", "## Portfolios and benchmarks by period (annualised return, volatility, max drawdown)", "", "| portfolio | period | ann return | ann vol | max drawdown | months |", "|---|---|---|---|---|---|"]
    seen = set()
    for r in out["rows"]:
        e = r["extra"] or {}
        name, bench = r["variant"].split("|vs_")
        for lab, blk in ((name, e.get("portfolio") or {}), (bench, e.get("benchmark") or {})):
            if lab in seen:
                continue
            seen.add(lab)
            for per in ("dev", "val"):
                b = blk.get(per) or {}
                if b:
                    L.append(f"| {lab} | {per} | {_f(b.get('ann_return'))} | {_f(b.get('ann_vol'))} | {_f(b.get('max_drawdown'))} | {b.get('months')} |")
    p = REG_DIR / "fp1_results_v1.md"
    p.write_text("\n".join(L) + "\n")
    return p


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        print(json.dumps(results(counts_only=True), indent=1))
    elif cmd == "run":
        out = run(rerun_reason=(sys.argv[2] if len(sys.argv) > 2 else None))
        for r in out["rows"]:
            print(r["variant"], r["verdict"], "dev", [round(x, 4) if isinstance(x, float) else x for x in r["dev"]], "val", [round(x, 4) if isinstance(x, float) else x for x in r["val"]])
    elif cmd == "table":
        print(table())
