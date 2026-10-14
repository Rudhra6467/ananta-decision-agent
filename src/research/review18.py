"""Review #18: H14 structural vs tight stops on H07; a 25% disaster stop on T3-B (docs/research/REVIEW_18.md).

Run: python -m src.research.review18   (lake data; writes ~/ananta_lake/reports/review18_results.json)
"""
from __future__ import annotations

import json
import statistics
import sys
import time

import pandas as pd

from src.research import portfolio_trend as P
from src.research import reads as R
from src.research import t3_turnover as TT
from src.research import teachers2 as T2
from src.research import zones as Z

TIGHT = 0.03
STRUCT_DAYS = 10
DISASTER = 0.25


def h07_trade_stop(S, A, rsi10, k0: int, cost: float, stop: float | None) -> tuple[float, bool] | None:
    """H07's exit (RSI(10) over 40 -> next open, else the open 10 days after entry) with an optional stop on the daily lows."""
    n = len(S.t)
    if k0 + 11 >= n:
        return None
    entry = A.o[k0]
    for k in range(k0, k0 + 10):
        if stop is not None:
            if A.o[k] <= stop:
                return float(A.o[k] / entry * (1 - cost) ** 2 - 1), True
            if A.l[k] <= stop:
                return float(stop / entry * (1 - cost) ** 2 - 1), True
        if rsi10[k] is not None and rsi10[k] > 40:
            return float(A.o[k + 1] / entry * (1 - cost) ** 2 - 1), False
    return float(A.o[k0 + 10] / entry * (1 - cost) ** 2 - 1), False


def part_a(D: dict) -> dict:
    evs, base = [], {}
    for c, bars in D.items():
        S = R.Series(bars)
        A = Z.Arr(S)
        rsi10 = R.rsi(S.c, 10)
        cost = R.cost(c)
        last = None
        for i in range(400, len(S.t) - 12):
            if S.t[i] >= R.CONF_END or S.sma200[i] is None or not A.c[i] > S.sma200[i]:
                continue
            sp = "DISCOVERY" if S.t[i] < R.DISC_END else "CONFIRM"
            r0 = T2.h07_trade(S, A, rsi10, i + 1, cost)
            if r0 is None:
                continue
            base.setdefault(sp, []).append(r0)
            if not (rsi10[i] is not None and rsi10[i] < 30) or (last is not None and S.t[i] - last <= 5 * T2.DAY):
                continue
            last = S.t[i]
            entry = A.o[i + 1]
            atr = S.atr[i] or 0.0
            stops = {"H07": None, "H07-S1": min(A.l[i - STRUCT_DAYS + 1: i + 1]) - atr, "H07-S2": entry * (1 - TIGHT)}
            for v, st in stops.items():
                if st is not None and st >= entry:
                    st = None if v == "H07-S1" else st                  # structure above the entry price: no structural stop
                rr = h07_trade_stop(S, A, rsi10, i + 1, cost, st)
                if rr is None:
                    continue
                evs.append({"coin": c, "t": S.t[i], "variant": v, "split": sp, "r": rr[0], "stopped": rr[1],
                            "stop_dist_pct": None if st is None else round(100 * (1 - st / entry), 2)})
        print(c, len(evs), file=sys.stderr)
    mb = {sp: statistics.mean(v) for sp, v in base.items()}
    out = {}
    for v in ("H07", "H07-S1", "H07-S2"):
        res = {}
        for sp in ("DISCOVERY", "CONFIRM"):
            rr = [e for e in evs if e["variant"] == v and e["split"] == sp]
            for e in rr:
                e["x"] = e["r"] - mb[sp]
            mk = T2._mk(rr)
            xs = [statistics.mean(x["x"] for x in m) for m in mk]
            sd = statistics.stdev(xs) if len(xs) > 2 else None
            dist = [e["stop_dist_pct"] for e in rr if e["stop_dist_pct"] is not None]
            res[sp] = {"trades": len(rr), "market_events": len(mk), "mean_net_pct": round(100 * statistics.mean(e["r"] for e in rr), 2) if rr else None,
                       "win": round(sum(e["r"] > 0 for e in rr) / len(rr), 3) if rr else None,
                       "stopped_pct": round(100 * sum(e["stopped"] for e in rr) / len(rr), 1) if rr else None,
                       "median_stop_dist_pct": round(statistics.median(dist), 2) if dist else None,
                       "worst_trade_pct": round(100 * min(e["r"] for e in rr), 1) if rr else None,
                       "mean_excess_pct": round(100 * statistics.mean(xs), 2) if xs else None,
                       "z": round(statistics.mean(xs) / (sd / len(xs) ** 0.5), 2) if sd else None}
        d, cf = res["DISCOVERY"], res["CONFIRM"]
        ok_d = d["market_events"] >= 30 and (d["mean_excess_pct"] or -1) > 0 and (d["z"] or 0) >= 2.5
        res["status"] = "PASS" if ok_d and (cf["mean_excess_pct"] or -1) > 0 else "NOT_CONFIRMED" if ok_d else (
            "INSUFFICIENT" if d["market_events"] < 30 else "FAIL")
        out[v] = res
    sp2 = ("DISCOVERY", "CONFIRM")
    ex = lambda v, sp: out[v][sp]["mean_excess_pct"] if out[v][sp]["mean_excess_pct"] is not None else -99   # noqa: E731
    out["H14_SUPPORTED"] = all(ex("H07-S1", sp) > ex("H07-S2", sp) for sp in sp2)
    for v in ("H07-S1", "H07-S2"):
        out[v]["worth_adding"] = out[v]["status"] == "PASS" and all(ex(v, sp) > ex("H07", sp) for sp in sp2)
    return out


def part_b(D: dict) -> dict:
    data, days = TT.frames(D)
    sig = P.signals(data, days)
    sims = {"BH": TT.simulate(data, days, sig["BH"], sig["_avail"], "T3"),
            "T3-B": TT.simulate(data, days, sig["T3"], sig["_avail"], "T3-B"),
            "T3B-D25": TT.simulate(data, days, sig["T3"], sig["_avail"], "T3-B", disaster=DISASTER)}
    res = {k: TT.split(v) for k, v in sims.items()}
    res["T3B-D25"]["disaster_stops"] = sims["T3B-D25"]["disaster_stops"]
    crises = {}
    for name, (a, b) in P.CRISES.items():
        row = {}
        for k, s in sims.items():
            eq = s["equity"]
            x, y = eq[eq.index >= pd.Timestamp(a)], eq[eq.index <= pd.Timestamp(b)]
            row[k] = round(100 * (y.iloc[-1] / x.iloc[0] - 1), 1) if len(x) and len(y) else None
        crises[name] = row
    res["crises_pct"] = crises
    ok = all(res["T3B-D25"][sp]["max_dd_pct"] < res["T3-B"][sp]["max_dd_pct"] and
             (res["T3B-D25"][sp]["mar"] or -9) >= (0.9 * res["T3-B"][sp]["mar"] if (res["T3-B"][sp]["mar"] or 0) > 0 else (res["T3-B"][sp]["mar"] or -9))
             for sp in ("DISCOVERY", "CONFIRM"))
    res["T3B-D25"]["PASS"] = ok
    return res


def main() -> None:
    from src.lake import research as L
    from src.lake import root

    t0 = time.time()
    u = json.loads((root() / "reports" / "universe_v1.json").read_text())
    D_all = L.load(u["chosen"])
    base = [L.base(s) for s in u["chosen"]]
    tiers = {"TOP30": [c for c in base[:30] if c in D_all], "LAB10": [c for c in L.LAB10 if c in D_all], "ALL": [c for c in base if c in D_all]}
    rep = {"version": "review18.v1", "pre_registration": "docs/research/REVIEW_18.md", "tiers": {}}
    for name, coins in tiers.items():
        D = {c: D_all[c] for c in coins}
        rep["tiers"][name] = {"coins": sorted(D), "A_stops_on_H07": part_a(D), "B_disaster_on_T3B": part_b(D)}
    rep["seconds"] = round(time.time() - t0)
    (root() / "reports" / "review18_results.json").write_text(json.dumps(rep, indent=1, default=str))
    for name, t in rep["tiers"].items():
        a, b = t["A_stops_on_H07"], t["B_disaster_on_T3B"]
        print("==", name, len(t["coins"]), "| H14 supported:", a["H14_SUPPORTED"])
        for v in ("H07", "H07-S1", "H07-S2"):
            print(f"  {v:7s} {a[v]['status']:12s}", {sp: (a[v][sp]["market_events"], a[v][sp]["mean_excess_pct"], a[v][sp]["z"], a[v][sp]["stopped_pct"],
                  a[v][sp]["median_stop_dist_pct"], a[v][sp]["worst_trade_pct"]) for sp in ("DISCOVERY", "CONFIRM")}, "worth adding" if a[v].get("worth_adding") else "")
        for k in ("BH", "T3-B", "T3B-D25"):
            r = b[k]
            print(f"  {k:8s}", {sp: (r[sp]["total_return_pct"], r[sp]["max_dd_pct"], r[sp]["mar"]) for sp in ("DISCOVERY", "CONFIRM")},
                  ("stops %d" % r.get("disaster_stops", 0)) if k == "T3B-D25" else "", "PASS" if r.get("PASS") else "")
        print("  crises", b["crises_pct"])


if __name__ == "__main__":
    main()
