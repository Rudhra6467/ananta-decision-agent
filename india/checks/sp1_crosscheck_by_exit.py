"""Independent bar-by-bar re-derivation of SP1 outcomes for a random sample (own ATR, own trail, own Black-76). Compares with SP1_outcomes."""
import datetime as dt, json, math, os, random, sys
import duckdb, numpy as np, pandas as pd
sys.path.insert(0, "/Users/vamsie/code/ananta-records")
from india import costs

D = "/Users/vamsie/ananta_data/india/"
NAMES = {"NIFTY": "NIFTY 50", "BANKNIFTY": "NIFTY BANK"}
ENTRY = {"D0": 1, "D1": 15, "D2": 30, "D3": 60}
ACT = [(x, d) for x in ("T1130", "T1515", "ORSTOP", "ATRSTOP", "TRAIL", "NEXTOPEN") for d in (1, -1)]
out = pd.read_parquet(D + "gold/studies/SP1_outcomes.parquet")
cal = pd.read_parquet(D + "silver/calendar/calendar.parquet")
tdays = sorted(pd.to_datetime(cal.loc[cal.is_trading_day, "date"]).dt.date)
nxt = {tdays[i]: tdays[i + 1] for i in range(len(tdays) - 1)}
prv = {tdays[i]: tdays[i - 1] for i in range(1, len(tdays))}
con = duckdb.connect()
day = pd.read_parquet(D + "silver/kite_index/day/" + [f for f in os.listdir(D + "silver/kite_index/day") if f.endswith(".parquet")][0])
day["date"] = pd.to_datetime(day["date"]).dt.date


def minutes(name, d):
    m = con.execute(f"select hour(ts)*60+minute(ts)-555 m, open o, high h, low l, close c from read_parquet('{D}silver/kite_index/minute/year={d.year}/part.parquet') where index_name=? and date=? order by m", [name, d]).df()
    m = m[(m.m >= 0) & (m.m < 375)].set_index("m").reindex(range(375))
    m["c"] = m["c"].ffill()
    for f in ("o", "h", "l"):
        m[f] = m[f].fillna(m["c"])
    return m


def atr_daily(name, d):
    x = day[(day.index_name == name) & (day.date < d)].sort_values("date").tail(15)
    pc = x["close"].shift(1)
    tr = np.maximum(x["high"], pc) - np.minimum(x["low"], pc)
    return float(tr.iloc[1:].mean())


def atr5(name, d, e):
    bars = []
    for dd in (prv[d], d):
        m = minutes(name, dd)
        n = 75 if dd != d else e // 5
        prev_c = None
        for j in range(75):
            seg = m.iloc[5 * j:5 * j + 5]
            h, l, c = seg.h.max(), seg.l.min(), seg.c.iloc[-1]
            tr = (h - l) if prev_c is None else max(h, prev_c) - min(l, prev_c)
            prev_c = c
            if j < n:
                bars.append(tr)
    return float(np.mean(bars[-14:]))


def walk(m, e, d, stop_fn, X, nxt_open=None):
    entry = m.o[e]
    best = entry
    for t in range(e, X):
        lvl = stop_fn(best)
        if lvl is not None and ((d > 0 and m.l[t] <= lvl) or (d < 0 and m.h[t] >= lvl)):
            return (min(m.o[t], lvl) if d > 0 else max(m.o[t], lvl)), t, True
        best = max(best, m.h[t]) if d > 0 else min(best, m.l[t])
    if X == 375:
        return nxt_open, 375, False
    return m.o[X], X, False


def bs(F, K, T, s, call, r=0.065):
    N = lambda x: 0.5 * (1 + math.erf(x / math.sqrt(2)))
    d1 = (math.log(F / K) + 0.5 * s * s * T) / (s * math.sqrt(T)); d2 = d1 - s * math.sqrt(T)
    return math.exp(-r * T) * (F * N(d1) - K * N(d2) if call else K * N(-d2) - F * N(-d1))


smp = out.groupby("exit", group_keys=False).apply(lambda g: g.sample(30, random_state=5))
bad = 0; nopt = 0
for r in smp.itertuples():
    name = NAMES[r.index]; d = r.date; e = ENTRY[r.point]; X, dirc = ACT[r.action]
    m = minutes(name, d); atr = atr_daily(name, d); entry = m.o[e]
    if X in ("T1130", "T1515"):
        px, tx, st = walk(m, e, dirc, lambda b: None, 135 if X == "T1130" else 360)
    elif X == "ORSTOP":
        s = m.l[:15].min() if dirc > 0 else m.h[:15].max()
        px, tx, st = walk(m, e, dirc, lambda b: s, 360)
    elif X == "ATRSTOP":
        px, tx, st = walk(m, e, dirc, lambda b: entry - dirc * 0.5 * atr, 360)
    elif X == "TRAIL":
        k = 3 * atr5(name, d, e)
        px, tx, st = walk(m, e, dirc, lambda b: b - dirc * k, 360)
    else:
        no = minutes(name, nxt[d]).o[1]
        px, tx, st = walk(m, e, dirc, lambda b: entry - dirc * atr, 375, no)
    g = dirc * (px - entry) / entry * 1e4
    ok = abs(r.entry - entry) < 1e-6 and abs(r.exit_px - px) < 1e-6 and r.exit_min == tx and r.stopped == st and abs(r.gross_bps - g) < 1e-6
    lt = r.lot; ticks = 2 + (2 if r.point == "D0" else 0) + (2 if (X == "NEXTOPEN" and not st) else 0)
    bv, sv = (entry * lt, px * lt) if dirc > 0 else (px * lt, entry * lt)
    cb = ((costs.cost("futures", "buy", bv, d.year, when=d) + costs.cost("futures", "sell", sv, d.year, when=d)) / lt + ticks * 0.05) / entry * 1e4
    ok &= abs(r.cost_bps - cb) < 1e-6
    if r.opt_ret == r.opt_ret:
        p = prv[d]
        ch = con.execute(f"select strike, opt_type, fwd, iv, coalesce(volume,0) v from read_parquet('{D}silver/fo_greeks/year={p.year}/part.parquet') where symbol=? and date=? and expiry=?", [r.index, p, r.opt_expiry]).df()
        spot_prev = float(minutes(name, p).c[374])
        car = float(ch.fwd.dropna().median()) / spot_prev
        typ = "CE" if dirc > 0 else "PE"
        listed = np.sort(ch.strike.unique())
        K = float(listed[np.abs(listed - entry).argmin()])
        tr_ = ch[(ch.opt_type == typ) & (ch.v > 0) & ch.iv.notna() & (ch.iv > 0)].reset_index(drop=True)
        iv = float(tr_.iv[tr_.strike == K].iloc[0]) if (tr_.strike == K).any() else float(tr_.iv.iloc[np.abs(tr_.strike - K).argmin()])
        ex_end = dt.datetime.combine(r.opt_expiry, dt.time(15, 30))
        T = lambda dd, mm: max((ex_end - (dt.datetime.combine(dd, dt.time(9, 15)) + dt.timedelta(minutes=int(mm)))).total_seconds() / 60, 1) / (365 * 24 * 60)
        dout, mout = (nxt[d], 1) if (X == "NEXTOPEN" and not st) else (d, tx)
        pin = max(bs(entry * car, K, T(d, e), iv, typ == "CE"), 0.05); pout = max(bs(px * car, K, T(dout, mout), iv, typ == "CE"), 0.05)
        h = {"NIFTY": 0.5, "BANKNIFTY": 1.0}[r.index]
        hin, hout = max(h, 0.0025 * pin), max(h, 0.0025 * pout) * (2 if st else 1)
        buy, sell = pin + hin, max(pout - hout, 0)
        net = (sell - buy) * lt - costs.cost("options", "buy", buy * lt, d.year, when=d) - costs.cost("options", "sell", sell * lt, dout.year, when=dout)
        ok &= abs(r.opt_K - K) < 1e-9 and abs(r.opt_iv - iv) < 1e-9 and abs(r.opt_net_rs - net) < 1e-3
        nopt += 1
    if not ok:
        bad += 1
        print("MISMATCH", r.index, d, r.point, X, dirc, {"entry": (r.entry, entry), "exit": (r.exit_px, px), "tx": (r.exit_min, tx), "st": (r.stopped, st), "cost": (r.cost_bps, cb)}, flush=True)
print(json.dumps({"sampled": len(smp), "with_option_leg": nopt, "mismatches": bad}), flush=True)
