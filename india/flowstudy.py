"""C06 (derivatives-positioning version): does who is long or short Nifty futures say anything about the next sessions? (dev 2012-2017, validation 2018-2023)

  python -m india.flowstudy

From the participant-wise open interest (india/flows.py): for FII and for Client (retail), the share of index-futures long contracts in their long+short,
and its 5-session change. The file of day t is known after its close; the outcome is the Nifty 50 close of t+6 over the close of t+1 (a trade the session after).
Registered conditions (thresholds fixed in advance): FII long share above 60% / below 40%, FII long share up more than 5 points in 5 sessions,
Client long share above 60% (the crowd as a contrarian sign: expect lower), each against the other days of the same quarter.
"""
from __future__ import annotations

import math
import sys

import numpy as np
import pandas as pd

from india import paths, registry

SPLIT = 2018


def _stat(x):
    x = x.dropna()
    if len(x) < 3:
        return float("nan"), float("nan"), int(len(x))
    se = x.std(ddof=1) / math.sqrt(len(x))
    return float(x.mean()), float(x.mean() / se) if se else float("nan"), int(len(x))


def run() -> dict:
    p = pd.read_parquet(paths.data_dir() / "silver/flows/participant_oi.parquet")
    p["date"] = pd.to_datetime(p["date"])
    lc, sc = [c for c in p.columns if c.startswith("future_index_long")][0], [c for c in p.columns if c.startswith("future_index_short")][0]
    p[lc], p[sc] = pd.to_numeric(p[lc], errors="coerce"), pd.to_numeric(p[sc], errors="coerce")
    p["long_share"] = p[lc] / (p[lc] + p[sc])
    w = p.pivot_table(index="date", columns="client_type", values="long_share").sort_index()
    ix = pd.read_parquet(paths.data_dir() / "silver/kite_index/day/day.parquet")
    n = ix[ix["index_name"] == "NIFTY 50"].assign(date=lambda d: pd.to_datetime(d["date"])).set_index("date")["close"].sort_index()
    fwd = (n.shift(-6) / n.shift(-1) - 1).rename("fwd5")
    d = w.join(fwd, how="inner").dropna(subset=["fwd5"])
    d["fii_chg5"] = d["FII"] - d["FII"].shift(5)
    conds = {"fii_long_gt60": (d["FII"] > 0.6, 1), "fii_long_lt40": (d["FII"] < 0.4, -1), "fii_rising5": (d["fii_chg5"] > 0.05, 1), "client_long_gt60": (d["Client"] > 0.6, -1)}
    reg = registry.register("C06", family="flows", title="Participant positioning in Nifty futures (FII, Client) and the next 5 sessions",
                            hypothesis="FII net long (or rising) is followed by higher 5-session Nifty returns, FII net short by lower; a crowded Client long by lower.",
                            variants=list(conds), note="participant-wise OI from 2012; outcome close t+6 / close t+1; on minus off within quarters")
    out = {}
    d["y"] = d.index.year
    for name, (mask, ex) in conds.items():
        x = d.assign(on=mask)
        st = {}
        for per, m in (("dev", x["y"] < SPLIT), ("val", x["y"] >= SPLIT)):
            z = x[m]
            qm = z.groupby([z.index.to_period("Q"), "on"])["fwd5"].mean().unstack()
            st[per] = _stat(qm[True] - qm[False]) if True in qm.columns and False in qm.columns else (float("nan"), float("nan"), 0)
        line = registry.record(reg, name, st["dev"], st["val"], extra={"share_on": float(mask.mean()), "days": int(len(d))}, expect=ex)
        out[name] = line["verdict"]
        print(f"C06 {name:17s} {line['verdict']:12s} dev {st['dev'][0]*100:+.2f}% t {st['dev'][1]:+.1f} q{st['dev'][2]} | val {st['val'][0]*100:+.2f}% t {st['val'][1]:+.1f} q{st['val'][2]} | days on {mask.mean():.0%}", flush=True)
    registry.mirror_to_catalog()
    return out


if __name__ == "__main__":
    paths.ensure()
    run()
