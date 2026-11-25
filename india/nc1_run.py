"""NC1's run (india/nc1.py has the method; registrations/nc1_v1.json the frozen design): the 72 registered rows into the ledger, and the
descriptive tables (how often each kind of news moves a stock; which kinds sit behind the day's biggest gainers and losers; the move over the
next five sessions). Writes registrations/nc1_results_v1.json and the tables of registrations/nc1_results_v1.md. Research years only.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from india import nc1, newskinds, registry


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _f(x, pct: bool = True, nd: int = 2):
    if x is None or (isinstance(x, float) and x != x):
        return "-"
    return f"{x * 100:+.{nd}f}%" if pct else f"{x:,.0f}"


def responsiveness(d: pd.DataFrame, ev: pd.DataFrame, base: pd.DataFrame) -> dict:
    out = {}
    tot = d.dropna(subset=["gap"])
    nonews = tot[tot["day_news"] == 0]
    cn = nonews[nonews["gap"].abs() >= nc1.GAP_MIN]
    out["A|no_news"] = {"stock_days": int(len(nonews)), "share_confirmed": float((nonews["gap"].abs() >= nc1.GAP_MIN).mean()),
                        "median_abs_gap": float(nonews["gap"].abs().median()), "confirmed": int(len(cn)), "cont_mean": float(cn["cont"].mean()),
                        "cont5_mean": float(cn["cont5"].mean())}
    ex = tot[["date", "sid", "kinds"]].explode("kinds").dropna(subset=["kinds"])
    for g in nc1.GROUPS:
        if g == "all_news":
            sel = tot[tot["n_news"] > 0]
        else:
            keys = ex[ex["kinds"] == g][["date", "sid"]]
            sel = tot.merge(keys, on=["date", "sid"], how="inner")
        conf = sel[sel["gap"].abs() >= nc1.GAP_MIN]
        out[f"A|{g}"] = {"stock_days": int(len(sel)), "share_confirmed": float((sel["gap"].abs() >= nc1.GAP_MIN).mean()) if len(sel) else None,
                         "median_abs_gap": float(sel["gap"].abs().median()) if len(sel) else None, "confirmed": int(len(conf)),
                         "up_share": float((conf["gap"] > 0).mean()) if len(conf) else None,
                         "cont_mean": float(conf["cont"].mean()) if len(conf) else None, "cont5_mean": float(conf["cont5"].mean()) if len(conf) else None}
    evv = ev.dropna(subset=["move15"])
    total = base.attrs.get("grid_moves_total") or 0
    out["B|no_news"] = {"moves": int(total), "share_confirmed": (len(base) / total) if total else None, "confirmed": int(len(base)),
                        "cont_mean": float(base["cont"].mean())}
    exb = evv[["symbol", "date", "kinds"]].explode("kinds").dropna(subset=["kinds"])
    for g in nc1.GROUPS:
        if g == "all_news":
            sel = evv
        else:
            keys = exb[exb["kinds"] == g][["symbol", "date"]].drop_duplicates()
            sel = evv.merge(keys, on=["symbol", "date"], how="inner")
        conf = sel[sel["move15"].abs() >= nc1.MOVE15_MIN]
        out[f"B|{g}"] = {"events": int(len(sel)), "share_confirmed": float((sel["move15"].abs() >= nc1.MOVE15_MIN).mean()) if len(sel) else None,
                         "median_abs_move15": float(sel["move15"].abs().median()) if len(sel) else None, "confirmed": int(len(conf)),
                         "up_share": float((conf["move15"] > 0).mean()) if len(conf) else None,
                         "cont_mean": float(conf["cont"].mean()) if len(conf) else None}
    return out


def movers_map(d: pd.DataFrame, top: int = 25) -> dict:
    """Of each session's 25 biggest gainers and 25 biggest losers (top-500 stocks, day move beyond the Nifty), the share with news of each kind
    that day, against the share of all top-500 stock-days with that kind (the lift). Counts only: this says what comes with big moves."""
    x = d.dropna(subset=["day_ret"])[["date", "sid", "day_ret", "day_news", "day_kinds"]].copy()
    x["r_up"] = x.groupby("date")["day_ret"].rank(ascending=False, method="first")
    x["r_dn"] = x.groupby("date")["day_ret"].rank(ascending=True, method="first")
    up, dn = x[x["r_up"] <= top], x[x["r_dn"] <= top]
    ex = x[["date", "sid", "day_kinds"]].explode("day_kinds").dropna(subset=["day_kinds"])
    out = {"sessions": int(x["date"].nunique()), "stock_days": int(len(x)),
           "any_news": {"all": float((x["day_news"] > 0).mean()), "gainers": float((up["day_news"] > 0).mean()), "losers": float((dn["day_news"] > 0).mean())},
           "kinds": {}}
    upk = set(map(tuple, up[["date", "sid"]].values))
    dnk = set(map(tuple, dn[["date", "sid"]].values))
    for g in newskinds.KINDS:
        keys = ex[ex["day_kinds"] == g][["date", "sid"]].drop_duplicates()
        kk = set(map(tuple, keys.values))
        base = len(kk) / len(x) if len(x) else 0.0
        gu, gd = len(kk & upk) / max(1, len(up)), len(kk & dnk) / max(1, len(dn))
        out["kinds"][g] = {"all": base, "gainers": gu, "losers": gd, "lift_gainers": (gu / base) if base else None, "lift_losers": (gd / base) if base else None,
                           "stock_days": len(kk)}
    return out


def run() -> dict:
    spec = json.loads(nc1.SPEC.read_text())
    sha = _sha(Path(newskinds.__file__))
    if sha != spec["dictionary"]["sha256"]:
        raise RuntimeError(f"india/newskinds.py changed since the freeze ({sha[:12]} against {spec['dictionary']['sha256'][:12]}): the design is void")
    t0 = dt.datetime.now(dt.timezone.utc)
    a = nc1.announcements()
    print(f"NC1: {len(a):,} announcements read", flush=True)
    d = nc1.part_a(a)
    print(f"NC1: part A, {len(d):,} top-500 stock-days", flush=True)
    ev, base = nc1.part_b(a)
    print(f"NC1: part B, {len(ev):,} in-session news events, {len(base):,} no-news confirmed moves", flush=True)
    series = {**nc1._rows_a(d), **nc1._rows_b(ev, base)}
    reg = registry.register("NC1", family=spec["bar"]["family"], title=spec["title"], hypothesis=spec["hypothesis"], variants=nc1.variants(),
                            note="registrations/nc1_v1.json", bar_families=spec["bar"]["bar_families"], union_k=spec["bar"]["union_k"])
    resp = responsiveness(d, ev, base)
    rows = {}
    for var in nc1.variants():
        part, group, _m = var.split("|")
        split = nc1.SPLIT_A if part == "A" else nc1.SPLIT_B
        s = series[var].copy()
        if len(s):
            s.index = pd.PeriodIndex(s.index, freq="Q")
        dev = nc1._stat(s[[p.year < split for p in s.index]]) if len(s) else (float("nan"), float("nan"), 0)
        val = nc1._stat(s[[p.year >= split for p in s.index]]) if len(s) else (float("nan"), float("nan"), 0)
        n = (resp.get(f"{part}|{group}") or {}).get("confirmed", 0)
        line = registry.record(reg, var, dev, val, expect=1, extra={"confirmed_events": int(n)})
        rows[var] = {"verdict": line["verdict"], "z": line["z"], "dev": dev, "val": val, "confirmed_events": int(n)}
        print(f"NC1 {var:34s} {line['verdict']:12s} dev {dev[0]*100:+.3f}% t {dev[1]:+.2f} q{dev[2]} | val {val[0]*100:+.3f}% t {val[1]:+.2f} q{val[2]} | n {n}",
              flush=True)
    registry.mirror_to_catalog()
    out = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "started_at": t0.isoformat(timespec="seconds"),
           "spec": "registrations/nc1_v1.json", "dictionary_sha256": sha, "rows": rows, "responsiveness": resp, "movers": movers_map(d),
           "z": rows[nc1.variants()[0]]["z"]}
    nc1.RESULTS_JSON.write_text(json.dumps(out, indent=1, default=str))
    write_tables(out)
    return out


def write_tables(out: dict) -> None:
    r, resp, mv = out["rows"], out["responsiveness"], out["movers"]
    L = ["# NC1 results: after news, does a confirmed move continue or fade? (research years, before costs)", "",
         f"Frozen design: `nc1_v1.json`. Code: `india/newskinds.py`, `india/nc1.py`, `india/nc1_run.py`. Ledger study NC1, family news_confirm, "
         f"bar z {out['z']}. Generated {out['generated_at']}.", "", "## In plain words", "", "(written after the run, from the tables below)", "",
         "## 1. How often each kind of news moves a stock", "",
         "Part A: overnight news (made public after the 15:30 close or before 09:00), top-500 stocks 2010-2023. A confirmed move is an open "
         "at least 2% from the previous close, beyond the Nifty's own gap.", "",
         "| kind | stock-days | confirmed share | median gap | confirmed | of them up | then to the close | then 5 sessions |", "|---|---|---|---|---|---|---|---|"]
    for key in ["A|no_news"] + [f"A|{g}" for g in nc1.GROUPS]:
        v = resp[key]
        name = "no news that day" if key == "A|no_news" else key[2:]
        L.append(f"| {name} | {v.get('stock_days', 0):,} | {_f(v.get('share_confirmed'), nd=1)} | {_f(v.get('median_abs_gap'))} | {v.get('confirmed', 0):,} | "
                 f"{_f(v.get('up_share'), nd=0) if 'up_share' in v else '-'} | {_f(v.get('cont_mean'))} | {_f(v.get('cont5_mean'))} |")
    L += ["", "Part B: news in session (09:20-15:00), stocks with 5-minute bars 2015-2023. A confirmed move is at least 1% beyond the Nifty in the "
          "15 minutes after the news. 'Then to the close' is the further move in the same direction (a minus means it faded).", "",
          "| kind | events | confirmed share | median 15-minute move | confirmed | of them up | then to the close |", "|---|---|---|---|---|---|---|"]
    v = resp["B|no_news"]
    L.append(f"| no news that day (every 15 minutes) | {v['moves']:,} | {_f(v['share_confirmed'], nd=1)} | - | {v['confirmed']:,} | - | {_f(v['cont_mean'])} |")
    for g in nc1.GROUPS:
        v = resp[f"B|{g}"]
        L.append(f"| {g} | {v['events']:,} | {_f(v['share_confirmed'], nd=1)} | {_f(v['median_abs_move15'])} | {v['confirmed']:,} | "
                 f"{_f(v['up_share'], nd=0)} | {_f(v['cont_mean'])} |")
    L += ["", "## 2. What comes with the day's biggest gainers and losers", "",
          f"Each session's 25 biggest gainers and 25 biggest losers among the top 500 ({mv['sessions']:,} sessions). Any news that day: "
          f"{_f(mv['any_news']['gainers'], nd=0)} of gainers and {_f(mv['any_news']['losers'], nd=0)} of losers, against "
          f"{_f(mv['any_news']['all'], nd=0)} of all stock-days. Lift = how many times more often the kind comes with a big mover than with an average stock-day.", "",
          "| kind | all stock-days | gainers | losers | lift, gainers | lift, losers |", "|---|---|---|---|---|---|"]
    for g, v in sorted(mv["kinds"].items(), key=lambda kv: -(kv[1]["lift_gainers"] or 0)):
        L.append(f"| {g} | {_f(v['all'], nd=2)} | {_f(v['gainers'], nd=2)} | {_f(v['losers'], nd=2)} | "
                 f"{(v['lift_gainers'] or 0):.1f}x | {(v['lift_losers'] or 0):.1f}x |")
    L += ["", "## 3. The registered rows (72): continue (cont) and better than a no-news move (edge)", "",
          "cont = the move from the confirmation to the close, in the confirmed direction, beyond the Nifty (quarter means). edge = cont minus the "
          "no-news move of the same direction (A: same quarter; B: same quarter and time of day). Expect +1 for both. Verdicts by the registry's standard rule.", "",
          "| row | dev mean | dev t | dev quarters | val mean | val t | val quarters | confirmed events | verdict |", "|---|---|---|---|---|---|---|---|---|"]
    for var, v in r.items():
        dv, vv = v["dev"], v["val"]
        L.append(f"| {var} | {_f(dv[0], nd=3)} | {dv[1]:+.2f} | {dv[2]} | {_f(vv[0], nd=3)} | {vv[1]:+.2f} | {vv[2]} | {v['confirmed_events']:,} | {v['verdict']} |")
    nc1.RESULTS_MD.write_text("\n".join(L) + "\n")
