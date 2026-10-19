"""Independent bar-by-bar re-derivation of OC trades for one year (no vectorisation), compared with ocstudy's output."""
import datetime as dt
import sys

import duckdb
import numpy as np
import pandas as pd

D = "/Users/vamsie/ananta_data/india/"
Y = 2016
t = pd.read_parquet("/Users/vamsie/ananta_runs/oc_smoke/OC1_index_trades.parquet") if False else None
con = duckdb.connect()
m = con.execute(f"""select index_name, date, hour(ts)*60+minute(ts)-555 as m, open, high, low, close from read_parquet('{D}silver/kite_index/minute/year={Y}/part.parquet')
                    where index_name in ('NIFTY 50') order by date, m""").df()
m["date"] = pd.to_datetime(m["date"]).dt.date


def naive(day: pd.DataFrame, k: int, E: str):
    g = day.set_index("m")
    if 0 not in g.index or len(g) < 360:
        return None
    g = g.reindex(range(375)).ffill()
    orh = g.loc[0:k - 1, "high"].max()
    orl = g.loc[0:k - 1, "low"].min()
    for i in range(k, 60):
        c = g.loc[i, "close"]
        if c > orh or c < orl:
            d = 1 if c > orh else -1
            edge = orh if d > 0 else orl
            if E == "E1":
                e, stop = i + 1, (orl if d > 0 else orh)
            else:
                band = 0.001
                up, dn = edge * (1 + band), edge * (1 - band)
                e = None
                run = np.inf if d > 0 else -np.inf
                for tt in range(i + 1, i + 31):
                    if tt + 2 >= 375:
                        break
                    lo, hi = g.loc[tt, "low"], g.loc[tt, "high"]
                    run = min(run, lo) if d > 0 else max(run, hi)
                    if (d > 0 and lo < dn) or (d < 0 and hi > up):
                        return ("failed", d, i)
                    touch = lo <= up if d > 0 else hi >= dn
                    nxt = g.loc[tt + 1]
                    conf = (nxt.close > up and nxt.low >= dn) if d > 0 else (nxt.close < dn and nxt.high <= up)
                    if touch and conf:
                        e = tt + 2
                        stop = min(run, nxt.low) if d > 0 else max(run, nxt.high)
                        break
                if e is None:
                    return ("no_retest", d, i)
            entry = g.loc[e, "open"]
            for tt in range(e, 360):
                b = g.loc[tt]
                if (d > 0 and b.low <= stop) or (d < 0 and b.high >= stop):
                    px = min(b.open, stop) if d > 0 else max(b.open, stop)
                    return ("trade", d, i, e, entry, stop, tt, px)
            return ("trade", d, i, e, entry, stop, 360, g.loc[360, "open"])
    return None


ours = pd.read_parquet("/Users/vamsie/ananta_runs/oc_smoke/OC1_index_trades.parquet")
bad = 0
n = 0
for (k, E), _ in [((15, "E1"), 0), ((30, "E1"), 0), ((15, "E2"), 0), ((30, "E2"), 0)]:
    o = ours[(ours.instrument == "NIFTY") & (ours.k == k) & (ours.E == E) & (ours.X == "X1") & (ours.version == "BASELINE")].set_index("date")
    used = set(pd.read_parquet("/Users/vamsie/ananta_runs/oc_smoke/OC1_index_days.parquet").query("instrument=='NIFTY'")["date"])
    for d, day in m.groupby("date"):
        if d not in used:
            continue
        r = naive(day, k, E)
        if r is None or r[0] != "trade":
            if d in o.index:
                bad += 1
                print("extra trade in ocstudy", k, E, d)
            continue
        n += 1
        if d not in o.index:
            bad += 1
            print("missing trade", k, E, d, r)
            continue
        x = o.loc[d]
        _, dd, i, e, entry, stop, tt, px = r
        if not (x.dir == dd and x.conf_min == i and x.entry_min == e and abs(x.entry - entry) < 1e-6 and x.exit_min == tt and abs(x.exit - px) < 1e-6
                and abs((x.entry - x.inv_dist * x.dir) - stop) < 1e-6):
            bad += 1
            print("mismatch", k, E, d, r, x[["dir", "conf_min", "entry_min", "entry", "inv_dist", "exit_min", "exit"]].to_dict())
print({"compared_trades": n, "mismatches": bad})
