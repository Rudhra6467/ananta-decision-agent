"""Independent re-derivation of FILTERED trades (index: breadth + agreement; stocks: breadth, agreement, rvol, VWAP) for 2016 samples."""
import datetime as dt
import json, sys
sys.stdout.reconfigure(line_buffering=True)

import duckdb
import numpy as np
import pandas as pd

D = "/Users/vamsie/ananta_data/india/"
S = "/Users/vamsie/ananta_runs/oc_smoke/"
Y = 2016
con = duckdb.connect()
idx = con.execute(f"""select index_name, date, hour(ts)*60+minute(ts)-555 as m, open, high, low, close from read_parquet('{D}silver/kite_index/minute/year={Y}/part.parquet')
                      where index_name in ('NIFTY 50','NIFTY BANK') order by date, m""").df()
idx["date"] = pd.to_datetime(idx["date"]).dt.date
br = pd.read_parquet(S + "OC1_breadth.parquet").set_index("date")
used = set(pd.read_parquet(S + "OC1_index_days.parquet")["date"])
ours = pd.read_parquet(S + "OC1_index_trades.parquet")


def grid(g):
    g = g.set_index("m").reindex(range(375)).ffill()
    return g


# ---------- index FILTERED k15/k30 E1 X1
bad = n = 0
for k in (15, 30):
    o = ours[(ours.instrument == "NIFTY") & (ours.k == k) & (ours.E == "E1") & (ours.X == "X1") & (ours.version == "FILTERED")].set_index("date")
    for d in sorted(used):
        a = grid(idx[(idx.date == d) & (idx.index_name == "NIFTY 50")])
        b = grid(idx[(idx.date == d) & (idx.index_name == "NIFTY BANK")])
        orh, orl = a.loc[0:k - 1, "high"].max(), a.loc[0:k - 1, "low"].min()
        res = None
        for i in range(k, 60):
            j = (i + 1) // 5 - 1
            B = br.loc[d, f"b{j}"]
            mv, mvo = a.loc[i, "close"] / a.loc[0, "open"] - 1, b.loc[i, "close"] / b.loc[0, "open"] - 1
            c = a.loc[i, "close"]
            if c > orh and B >= 0.6 and mv >= 0.0005 and mvo >= 0.0005:
                res = (1, i); break
            if c < orl and B <= 0.4 and mv <= -0.0005 and mvo <= -0.0005:
                res = (-1, i); break
        if res is None:
            if d in o.index:
                bad += 1; print("extra", k, d)
            continue
        n += 1
        if d not in o.index or o.loc[d, "conf_min"] != res[1] or o.loc[d, "dir"] != res[0]:
            bad += 1; print("index mismatch", k, d, res, o.loc[d, ["dir", "conf_min"]].to_dict() if d in o.index else None)
print({"index_filtered_compared": n, "mismatches": bad})

# ---------- stocks: recompute eligibility pieces for sampled days
st = pd.read_parquet(S + "OC1_stock_trades.parquet")
link = pd.read_parquet(D + "silver/security_master/kite.parquet", columns=["kite_symbol", "entity"]).dropna()
cal = pd.read_parquet(D + "silver/calendar/calendar.parquet")
days = sorted(pd.to_datetime(cal.loc[cal.is_trading_day, "date"]).dt.date)
spec = set(dt.date.fromisoformat(x) for x in json.load(open(D + "manifests/special_sessions.json"))["dates"])
reg = [x for x in days if x not in spec]
uni = pd.read_parquet(D + "gold/universe/u_liq_in.parquet", columns=["date", "sid", "rank"])
uni["date"] = pd.to_datetime(uni["date"]).dt.date
bars = con.execute(f"""select symbol, date, (hour(ts)*60+minute(ts)-555)//5 as j, raw_open o, raw_high h, raw_low l, raw_close c, coalesce(kite_volume,0) v
                       from read_parquet('{D}silver/kite_5m/year={Y}/part.parquet')""").df()
bars["date"] = pd.to_datetime(bars["date"]).dt.date
bars = bars.merge(link, left_on="symbol", right_on="kite_symbol")
valid = bars.groupby(["entity", "date"]).agg(nb=("j", "size"), h0=("j", lambda s: (s == 0).any()), nraw=("c", lambda s: s.isna().sum())).reset_index()
valid = valid[(valid.nb >= 70) & valid.h0 & (valid.nraw == 0)]
vkey = set(zip(valid.entity, valid.date))
cv = bars[bars.j <= 11].groupby(["entity", "date", "j"])["v"].sum().groupby(level=[0, 1]).cumsum().rename("cv").reset_index()
CV = {key: g.set_index("j")["cv"] for key, g in cv.groupby(["entity", "date"])}
rng = np.random.default_rng(3)
sample_days = sorted(rng.choice(sorted(set(st.date)), 25, replace=False))
o = st[(st.k == 15) & (st.E == "E1") & (st.X == "X1")]
bad = n = 0
for d in sample_days:
    i = reg.index(d)
    prev20 = reg[i - 20:i]
    prev_session = days[days.index(d) - 1]
    rk = uni[uni.date == prev_session].set_index("sid")["rank"]
    nifty = grid(idx[(idx.date == d) & (idx.index_name == "NIFTY 50")])
    day = bars[bars.date == d]
    for ent, g in day.groupby("entity"):
        if rk.get(ent, 999) > 100 or (ent, d) not in vkey:
            continue
        base = []
        for p in prev20:
            if (ent, p) in vkey:
                base.append(CV[(ent, p)])
        if len(base) < 15:
            continue
        g = g.sort_values("j").set_index("j").reindex(range(75))
        g["c"] = g["c"].ffill(); g[["o", "h", "l"]] = g[["o", "h", "l"]].apply(lambda s: s.fillna(g["c"])); g["v"] = g["v"].fillna(0)
        orh, orl = g.loc[0:2, "h"].max(), g.loc[0:2, "l"].min()
        cum = g["v"].cumsum(); vw = ((g.h + g.l + g.c) / 3 * g.v).cumsum() / cum
        brk = filt = None
        for j in range(3, 12):
            c = g.loc[j, "c"]
            if g.loc[j, "h"] == g.loc[j, "l"]:
                continue
            up, dn = c > orh, c < orl
            if (up or dn) and brk is None:
                brk = (1 if up else -1, j)
            medj = np.median([b.get(j, np.nan) for b in base if j in b.index])
            rv = cum[j] / medj
            B = br.loc[d, f"b{j}"]
            smv, nmv = c / g.loc[0, "o"] - 1, nifty.loc[5 * j + 4, "close"] / nifty.loc[0, "open"] - 1
            if up and B >= 0.6 and smv >= 0.0005 and nmv >= 0.0005 and rv >= 1.5 and c > vw[j] and filt is None:
                filt = (1, j)
            if dn and B <= 0.4 and smv <= -0.0005 and nmv <= -0.0005 and rv >= 1.5 and c < vw[j] and filt is None:
                filt = (-1, j)
        for ver, r in (("BASELINE", brk), ("FILTERED", filt)):
            x = o[(o.version == ver) & (o.date == d) & (o.entity == ent)]
            if r is None:
                if len(x):
                    bad += 1; print("extra stock", ver, d, ent)
                continue
            n += 1
            if not len(x) or int(x.conf_bar.iloc[0]) != r[1] or int(x.dir.iloc[0]) != r[0]:
                bad += 1; print("stock mismatch", ver, d, ent, r, x[["dir", "conf_bar"]].to_dict("records"))
print({"stock_decisions_compared": n, "mismatches": bad})
