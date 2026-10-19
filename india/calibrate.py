"""Calibration reads: the only research-side module allowed to read sealed (2024+) rows, and only under the logged purpose "calibration".
Each function measures how far a stand-in is from the real market (synthetic option prices, settlement prices); none scores a rule, computes
a rule's return, or feeds a verdict. india.leakcheck checks that every sealed call here names purpose "calibration".

  python -m india.calibrate r01       R01: synthetic O-04 prices against the recorder's real option minutes, on recorded expiry days
  python -m india.calibrate settle    settlement price against what actually traded in the last 30 minutes, on recorded live contracts
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from india import o4hist, optpaper, paths, sealed


def r01() -> dict:
    """R01: how wrong are the synthetic O-04 prices? For every expiry day the recorder has, rebuild the at-the-money call and put from the index path and the
    previous session's settlement IV (exactly as the historical reconstruction does) and compare minute by minute with the recorded option candles, then
    compare the O-04 outcome on synthetic and on real prices. CURRENT-MARKET OBSERVATION; written to gold/studies/R01_calibration.parquet."""
    days = []
    p = paths.data_dir() / "paper" / "options_trades.jsonl"
    if p.exists():
        for line in p.read_text().splitlines():
            r = json.loads(line)
            if r.get("strategy") == "O-04" and r.get("kind") != "skip":
                days.append((r["index"], r["day"]))
    days = sorted(set(days))
    if not days:
        print("R01: no recorded O-04 days yet")
        return {"days": 0}
    g = sealed.read_cols("calibration", "silver/fo_greeks", ["date", "symbol", "expiry", "strike", "opt_type", "iv", "flag"], min(d for _, d in days)[:8] + "01")
    g["date"], g["expiry"] = pd.to_datetime(g["date"]), pd.to_datetime(g["expiry"])
    ins = optpaper.instruments()
    rows, outcome = [], []
    for name, day in days:
        d = pd.Timestamp(day)
        spot = optpaper.minutes("index", o4hist.INDEX[name])
        spot = spot[spot.index.normalize() == d]
        s1329 = spot[(spot.index >= d + pd.Timedelta(hours=13, minutes=29)) & (spot.index < d + pd.Timedelta(hours=13, minutes=30))]
        if s1329.empty:
            continue
        K = round(float(s1329["close"].iloc[0]) / o4hist.STEP[name]) * o4hist.STEP[name]
        iv = o4hist._iv_prev(name, d, K, g.assign(flag=g["flag"].fillna("ok")))
        sub = ins[(ins["name"] == name) & (ins["expiry"] == day)]
        ce_s, pe_s = sub[(sub["strike"] == K) & (sub["instrument_type"] == "CE")], sub[(sub["strike"] == K) & (sub["instrument_type"] == "PE")]
        if iv is None or ce_s.empty or pe_s.empty:
            continue
        ce_r, pe_r = optpaper.minutes("option", ce_s["tradingsymbol"].iloc[0], day), optpaper.minutes("option", pe_s["tradingsymbol"].iloc[0], day)
        sp = spot[spot.index >= d + pd.Timedelta(hours=12)]
        ce_m, pe_m = o4hist._frame(sp, d, K, iv, True), o4hist._frame(sp, d, K, iv, False)
        for leg, real, model in (("CE", ce_r, ce_m), ("PE", pe_r, pe_m)):
            j = model.join(real[["close"]].rename(columns={"close": "real"}), how="inner")
            j = j[j.index >= d + pd.Timedelta(hours=13)]
            for t, r in j.iterrows():
                rows.append({"index": name, "day": day, "leg": leg, "ts": t, "model": r["close"], "real": r["real"]})
        lot = int(ce_s["lot_size"].iloc[0])
        for v in optpaper.VARIANTS_O4:
            a = optpaper.sim_o4(name, day, v, ce_m, pe_m, sp, lot)
            b = optpaper.sim_o4(name, day, v, ce_r, pe_r, spot, lot)
            if a and b:
                outcome.append({"index": name, "day": day, "variant": a["variant"], "synthetic_net": a["net_inr"], "real_net": b["net_inr"], "iv_prev": iv})
    df = pd.DataFrame(rows)
    if df.empty:
        return {"days": len(days), "matched": 0}
    df["err_pct"] = df["model"] / df["real"] - 1
    df.to_parquet(paths.gold() / "studies" / "R01_calibration.parquet")
    oc = pd.DataFrame(outcome)
    out = {"days": len(days), "minutes": len(df), "median_err_pct": float(df["err_pct"].median()), "mae_pct": float(df["err_pct"].abs().median()),
           "at_1330_err_pct": float(df[df["ts"].dt.strftime("%H:%M") == "13:30"]["err_pct"].median()) if len(df) else None,
           "o4_synthetic_minus_real_inr": float((oc["synthetic_net"] - oc["real_net"]).mean()) if len(oc) else None}
    print(json.dumps(out, indent=1), flush=True)
    return out


def settle_vs_tradable() -> dict:
    """Were NSE settlement prices tradable? For every recorded live contract-day (the recorder's real Kite minutes), compare the bhavcopy settle
    (sealed 2026 rows, purpose calibration: a data check, no rule is scored) with what actually traded: the last 30 minutes' volume-weighted price,
    whether the contract traded at all in that window, and how stale its last trade was. Grouped by premium size, the axis that separates F01's
    at-the-money legs from F02's cheap hedges."""
    import csv
    import glob
    import gzip

    inst = {}
    for f in sorted(glob.glob(str(paths.bronze("kite_instruments") / "NFO_*.csv"))):
        for r in csv.DictReader(open(f)):
            if r["segment"] == "NFO-OPT":
                inst[r["tradingsymbol"]] = (r["name"], r["expiry"], float(r["strike"]), r["instrument_type"])
    rows = []
    for f in glob.glob(str(paths.bronze("kite_1m_fo") / "*" / "*.jsonl.gz")):
        sym = f.rsplit("/", 1)[1].replace(".jsonl.gz", "")
        if sym not in inst:
            continue
        candles = {}
        with gzip.open(f, "rt") as fh:
            for line in fh:
                for c in json.loads(line).get("candles") or []:
                    candles[c[0]] = c  # later fetches overwrite earlier ones (the last window is still growing)
        if not candles:
            continue
        c = pd.DataFrame(list(candles.values()), columns=["ts", "o", "h", "l", "c", "v"])
        c["ts"] = pd.to_datetime(c["ts"])
        c["date"] = c["ts"].dt.tz_localize(None).dt.normalize()
        c["mins_to_close"] = (c["date"] + pd.Timedelta(hours=15, minutes=30) - c["ts"].dt.tz_localize(None)).dt.total_seconds() / 60
        c = c[c["mins_to_close"] >= 0]  # Kite serves a few candles after 15:30; the session ends at 15:30
        for d, x in c.groupby("date"):
            last30 = x[(x["mins_to_close"] <= 30) & (x["v"] > 0)]
            traded = x[x["v"] > 0]
            vwap = float((last30["c"] * last30["v"]).sum() / last30["v"].sum()) if len(last30) else None
            rows.append({"tradingsymbol": sym, "date": d, "name": inst[sym][0], "expiry": pd.Timestamp(inst[sym][1]), "strike": inst[sym][2], "opt_type": inst[sym][3],
                         "vwap30": vwap, "last_close": float(x["c"].iloc[-1]), "vol_day": float(x["v"].sum()), "vol_last30": float(last30["v"].sum()),
                         "mins_since_last_trade": float(traded["mins_to_close"].min()) if len(traded) else None})
    m = pd.DataFrame(rows)
    if m.empty:
        return {"rows": 0}
    since = str(m["date"].min().date())
    b = sealed.read_cols("calibration", "silver/fo_bhavcopy", ["date", "symbol", "expiry", "strike", "opt_type", "close", "settle", "volume"], since,
                         "instrument = 'OPTIDX' and symbol in ('NIFTY', 'BANKNIFTY')")
    b["date"], b["expiry"] = pd.to_datetime(b["date"]), pd.to_datetime(b["expiry"])
    j = m.merge(b.rename(columns={"symbol": "name", "volume": "nse_volume"}), on=["name", "date", "expiry", "strike", "opt_type"], how="inner")
    j = j[j["settle"] > 0]
    j["gap_vs_vwap30"] = j["settle"] / j["vwap30"] - 1
    j["no_trade_last30"] = j["vwap30"].isna()
    j["premium"] = pd.cut(j["settle"], [0, 2, 5, 20, 50, 150, 1e9], labels=["<2", "2-5", "5-20", "20-50", "50-150", "150+"])
    j["dte"] = (j["expiry"] - j["date"]).dt.days
    j["eve_or_expiry"] = j["dte"] <= 1
    g = j.groupby(["name", "eve_or_expiry", "premium"], observed=True).agg(contract_days=("settle", "size"), no_trade_last30=("no_trade_last30", "mean"),
                                                         median_signed_gap=("gap_vs_vwap30", "median"),
                                                         median_abs_gap=("gap_vs_vwap30", lambda x: x.abs().median()),
                                                         p90_abs_gap=("gap_vs_vwap30", lambda x: x.abs().quantile(0.9)),
                                                         median_mins_since_trade=("mins_since_last_trade", "median")).reset_index()
    j.to_parquet(paths.gold() / "studies" / "settle_vs_tradable.parquet")
    out = {"contract_days": int(len(j)), "days": int(j["date"].nunique()), "window": f"{j['date'].min().date()}..{j['date'].max().date()}",
           "table": g.round(4).to_dict(orient="records")}
    (paths.manifest_dir() / "settle_vs_tradable.json").write_text(json.dumps(out, indent=1, default=str))
    print(g.round(4).to_string(index=False), flush=True)
    return out


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "settle"
    r = {"r01": r01, "settle": settle_vs_tradable}[cmd]()
    print(json.dumps({k: v for k, v in r.items() if k != "table"}, default=str), flush=True)
