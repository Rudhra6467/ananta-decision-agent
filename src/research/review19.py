"""Review #19: buying pressure (U03), funding (U01) and open interest (U02) as filters on T3-B and H07 (docs/research/REVIEW_19.md).

Run: python -m src.research.review19   (writes ~/ananta_lake/reports/review19_results.json)
"""
from __future__ import annotations

import bisect
import json
import statistics
import sys
import time

import pandas as pd

from src.lake import futures as F
from src.research import portfolio_trend as P
from src.research import reads as R
from src.research import t3_turnover as TT
from src.research import teachers2 as T2
from src.research import zones as Z

DAY = 86400


def taker_high(sym: str) -> dict[int, bool | None]:
    """t -> 7-day taker buy share above the median of the previous 180 days (None: not enough history)."""
    import duckdb

    from src.lake import research as L

    p = L.clean_dir("1d") / f"symbol={sym}" / "**" / "*.parquet"
    rows = duckdb.sql(f"SELECT t, v, tbv FROM read_parquet('{p}', hive_partitioning=true) WHERE share >= {L.MIN_SHARE} ORDER BY t").fetchall()
    sh = [(int(t), tb / v) for t, v, tb in rows if v and tb is not None]
    out = {}
    for i, (t, _) in enumerate(sh):
        if i < 187:
            out[t] = None
            continue
        s7 = statistics.mean(x for _, x in sh[i - 6: i + 1])
        base = statistics.median(x for _, x in sh[i - 186: i - 6])
        out[t] = s7 > base
    return out


def funding_crowded(coin: str) -> dict[int, bool | None]:
    df = F.load("funding_daily", coin)
    if df is None or not len(df):
        return {}
    df = df.sort_values("t")
    t, f = [int(x) for x in df["t"]], list(df["funding"].astype(float))
    out = {}
    for i in range(len(t)):
        if i < 7 + 90:
            out[t[i]] = None
            continue
        f7 = statistics.mean(f[i - 6: i + 1])
        hist = f[max(0, i - 6 - 365): i - 6]
        out[t[i]] = f7 > sorted(hist)[int(0.8 * (len(hist) - 1))]
    return out


def oi_flushed(coin: str) -> dict[int, bool | None]:
    df = F.load("metrics_daily", coin)
    if df is None or not len(df):
        return {}
    df = df.sort_values("t")
    t, v = [int(x) for x in df["t"]], list(df["oi_value"].astype(float))
    return {t[i]: (None if i < 5 or not v[i - 5] else v[i] < v[i - 5]) for i in range(len(t))}


def _get(m: dict, t: int):
    return m.get(t // DAY * DAY)


def t3_part(D: dict, TB: dict, FU: dict) -> dict:
    data, days = TT.frames(D)
    sig = P.signals(data, days)
    idx = [int(d.timestamp()) for d in days]
    res = {"BH": TT.split(TT.simulate(data, days, sig["BH"], sig["_avail"], "T3")),
           "T3-B": TT.split(TT.simulate(data, days, sig["T3"], sig["_avail"], "T3-B"))}
    tb = pd.DataFrame({c: [(lambda x: True if x is None else x)(_get(TB.get(c, {}), t)) for t in idx] for c in sig["T3"].columns}, index=days)
    fu = pd.DataFrame({c: [(lambda x: True if x is None else not x)(_get(FU.get(c, {}), t)) for t in idx] for c in sig["T3"].columns}, index=days)
    for k, m in (("T3B-TB", tb), ("T3B-F", fu)):
        res[k] = TT.split(TT.simulate(data, days, sig["T3"] & m, sig["_avail"], "T3-B"))
        res[k]["share_of_coin_days_allowed_pct"] = round(100 * float(m.values.mean()), 1)
        res[k]["PASS"] = TT.t3_rules_pass(res, k) and all((res[k][sp]["mar"] or -9) > (res["T3-B"][sp]["mar"] or -9) for sp in ("DISCOVERY", "CONFIRM"))
    return res


def h07_part(D: dict, TB: dict, FU: dict, OI: dict) -> dict:
    B = R.Series(D["BTC"])
    evs, base = [], {}
    for c, bars in D.items():
        S = B if c == "BTC" else R.Series(bars)
        A = Z.Arr(S)
        rsi10 = R.rsi(S.c, 10)
        cost = R.cost(c)
        last: dict = {}
        for i in range(400, len(S.t) - 12):
            t = S.t[i]
            if t >= R.CONF_END or S.sma200[i] is None or not A.c[i] > S.sma200[i]:
                continue
            sp = "DISCOVERY" if t < R.DISC_END else "CONFIRM"
            r = T2.h07_trade(S, A, rsi10, i + 1, cost)
            if r is None:
                continue
            base.setdefault(sp, []).append(r)
            if rsi10[i] is not None and rsi10[i] < 30:
                tb, fu, oi = _get(TB.get(c, {}), t), _get(FU.get(c, {}), t), _get(OI.get(c, {}), t)
                vs = ["H07"] + (["H07-TB"] if tb is None or tb else []) + (["H07-F"] if fu is None or not fu else []) + (["H07-OI"] if oi is None or oi else [])
                for v in vs:
                    if v in last and t - last[v] <= 5 * DAY:
                        continue
                    last[v] = t
                    evs.append({"coin": c, "t": t, "variant": v, "split": sp, "r": r, "defined": {"TB": tb is not None, "F": fu is not None, "OI": oi is not None}})
        print(c, len(evs), file=sys.stderr)
    mb = {sp: statistics.mean(v) for sp, v in base.items()}
    out = {}
    for v in ("H07", "H07-TB", "H07-F", "H07-OI"):
        res = {}
        for sp in ("DISCOVERY", "CONFIRM"):
            rr = [e for e in evs if e["variant"] == v and e["split"] == sp]
            mk = T2._mk(rr)
            xs = [statistics.mean(x["r"] - mb[sp] for x in m) for m in mk]
            sd = statistics.stdev(xs) if len(xs) > 2 else None
            key = {"H07-TB": "TB", "H07-F": "F", "H07-OI": "OI"}.get(v)
            res[sp] = {"trades": len(rr), "market_events": len(mk), "mean_excess_pct": round(100 * statistics.mean(xs), 2) if xs else None,
                       "z": round(statistics.mean(xs) / (sd / len(xs) ** 0.5), 2) if sd else None,
                       "trades_with_data": sum(e["defined"][key] for e in rr) if key else None}
        d, cf = res["DISCOVERY"], res["CONFIRM"]
        ok_d = d["market_events"] >= 30 and (d["mean_excess_pct"] or -1) > 0 and (d["z"] or 0) >= 2.5
        res["status"] = "PASS" if ok_d and (cf["mean_excess_pct"] or -1) > 0 else "NOT_CONFIRMED" if ok_d else (
            "INSUFFICIENT" if d["market_events"] < 30 else "FAIL")
        out[v] = res
    for v in ("H07-TB", "H07-F", "H07-OI"):
        out[v]["PASS"] = out[v]["status"] == "PASS" and all((out[v][sp]["mean_excess_pct"] or -99) > (out["H07"][sp]["mean_excess_pct"] or -99)
                                                              for sp in ("DISCOVERY", "CONFIRM"))
    return out


def main() -> None:
    from src.lake import research as L
    from src.lake import root

    t0 = time.time()
    u = json.loads((root() / "reports" / "universe_v1.json").read_text())
    D_all = L.load(u["chosen"])
    sym = {L.base(s): s for s in u["chosen"]}
    base = [L.base(s) for s in u["chosen"]]
    TB = {c: taker_high(sym[c]) for c in D_all}
    FU = {c: funding_crowded(c) for c in D_all}
    OI = {c: oi_flushed(c) for c in D_all}
    tiers = {"TOP30": [c for c in base[:30] if c in D_all], "LAB10": [c for c in L.LAB10 if c in D_all], "ALL": [c for c in base if c in D_all]}
    rep = {"version": "review19.v1", "pre_registration": "docs/research/REVIEW_19.md", "judged_on": "TOP30",
           "data_from": {c: {"funding": min((t for t, x in FU[c].items() if x is not None), default=None),
                             "open_interest": min((t for t, x in OI[c].items() if x is not None), default=None)} for c in base[:30] if c in D_all},
           "tiers": {}}
    for name, cs in tiers.items():
        D = {c: D_all[c] for c in cs}
        rep["tiers"][name] = {"coins": sorted(D), "T3": t3_part(D, TB, FU), "H07": h07_part(D, TB, FU, OI)}
    rep["seconds"] = round(time.time() - t0)
    (root() / "reports" / "review19_results.json").write_text(json.dumps(rep, indent=1, default=str))
    for name, t in rep["tiers"].items():
        print("==", name)
        for k in ("T3-B", "T3B-TB", "T3B-F"):
            r = t["T3"][k]
            print(f"  {k:7s}", {sp: (r[sp]["total_return_pct"], r[sp]["max_dd_pct"], r[sp]["mar"]) for sp in ("DISCOVERY", "CONFIRM")},
                  r.get("share_of_coin_days_allowed_pct", ""), "PASS" if r.get("PASS") else "")
        for k in ("H07", "H07-TB", "H07-F", "H07-OI"):
            h = t["H07"][k]
            print(f"  {k:7s}", h["status"], {sp: (h[sp]["market_events"], h[sp]["mean_excess_pct"], h[sp]["z"], h[sp]["trades_with_data"]) for sp in ("DISCOVERY", "CONFIRM")},
                  "PASS" if h.get("PASS") else "")


if __name__ == "__main__":
    main()
