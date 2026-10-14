"""Review #17: relative strength vs BTC (H08) and breadth (H16) as filters on T3-B and H07 (docs/research/REVIEW_17.md).

Run: python -m src.research.review17   (lake data; writes ~/ananta_lake/reports/review17_results.json)
"""
from __future__ import annotations

import json
import statistics
import sys
import time

import numpy as np
import pandas as pd

from src.research import portfolio_trend as P
from src.research import reads as R
from src.research import t3_turnover as TT
from src.research import teachers2 as T2
from src.research import zones as Z

MIN_BREADTH_COINS = 8


# ----------------------------------------------------------------------------- shared definitions (daily, earlier bars only)
def breadth_by_day(D: dict) -> dict[int, bool | None]:
    """t -> True (strong) / False (weak) / None (fewer than 8 coins with 200 days of history)."""
    rows: dict[int, list[tuple[bool, bool]]] = {}
    for c, bars in D.items():
        S = R.Series(bars)
        e50 = R.ema(S.c, 50)
        for i, t in enumerate(S.t):
            if S.sma200[i] is None or e50[i] is None:
                continue
            rows.setdefault(t, []).append((S.c[i] > e50[i], S.c[i] > S.sma200[i]))
    out = {}
    for t, xs in rows.items():
        n = len(xs)
        out[t] = None if n < MIN_BREADTH_COINS else (sum(a for a, _ in xs) >= 0.7 * n and sum(b for _, b in xs) >= 0.5 * n)
    return out


def rs_by_day(D: dict) -> dict[str, dict[int, bool]]:
    """coin -> {t: RS on}. RS on = coin/BTC ratio above its 50-day EMA. BTC is always on."""
    B = R.Series(D["BTC"])
    out = {"BTC": {t: True for t in B.t}}
    for c, bars in D.items():
        if c == "BTC":
            continue
        ts, ratio = [], []
        for b in bars:
            bi = B.at(b[0])
            if bi is not None and B.c[bi] > 0:
                ts.append(b[0])
                ratio.append(b[4] / B.c[bi])
        e = R.ema(ratio, 50)
        out[c] = {t: (e[k] is not None and k >= 50 and ratio[k] > e[k]) for k, t in enumerate(ts)}
    return out


# ----------------------------------------------------------------------------- T3-B with filters
def t3_variants(D: dict, rs: dict, br: dict) -> dict:
    data, days = TT.frames(D)
    sig = P.signals(data, days)
    t3 = sig["T3"]
    idx = [int(d.timestamp()) for d in days]
    RS = pd.DataFrame({c: [rs.get(c, {}).get(t, False) for t in idx] for c in t3.columns}, index=days)
    BR = pd.Series([br.get(t) for t in idx], index=days)
    br_ok = BR.map(lambda x: True if x is None else bool(x))
    on = {"T3-B": t3, "T3B-RS": t3 & RS, "T3B-BR": t3.mul(br_ok, axis=0).astype(bool)}
    res = {"BH": TT.split(TT.simulate(data, days, sig["BH"], sig["_avail"], "T3"))}
    for k, m in on.items():
        res[k] = TT.split(TT.simulate(data, days, m, sig["_avail"], "T3-B"))
    for k in ("T3B-RS", "T3B-BR"):
        ok = TT.t3_rules_pass(res, k) and all((res[k][sp]["mar"] or -9) > (res["T3-B"][sp]["mar"] or -9) for sp in ("DISCOVERY", "CONFIRM"))
        res[k]["PASS"] = ok
    res["T3-B"]["passes_t3_rules"] = TT.t3_rules_pass(res, "T3-B")
    res["breadth_strong_share_pct"] = round(100 * float((BR == True).sum()) / max(1, int(BR.notna().sum())), 1)  # noqa: E712
    return res


# ----------------------------------------------------------------------------- H07 with filters (review #14's code path)
def h07_variants(D: dict, rs: dict, br: dict) -> dict:
    B = R.Series(D["BTC"])
    evs, base = [], {}
    for c, bars in D.items():
        S = B if c == "BTC" else R.Series(bars)
        A = Z.Arr(S)
        rsi10 = R.rsi(S.c, 10)
        cost = R.cost(c)
        last: dict = {}
        sig = []
        for i in range(400, len(S.t) - 12):
            if S.t[i] >= R.CONF_END or S.sma200[i] is None or not A.c[i] > S.sma200[i]:
                continue
            sp = "DISCOVERY" if S.t[i] < R.DISC_END else "CONFIRM"
            r = T2.h07_trade(S, A, rsi10, i + 1, cost)
            if r is None:
                continue
            base.setdefault(sp, []).append(r)                        # one baseline for every variant: plain H07's
            if rsi10[i] is not None and rsi10[i] < 30:
                b = br.get(S.t[i])
                variants = ["H07"]
                if rs.get(c, {}).get(S.t[i], False):
                    variants.append("H07-RS")
                if b is None or b:
                    variants.append("H07-BR")
                for v in variants:
                    if v in last and S.t[i] - last[v] <= 5 * T2.DAY:
                        continue
                    last[v] = S.t[i]
                    sig.append({"coin": c, "t": S.t[i], "variant": v, "split": sp, "r": r})
        evs += sig
        print(c, len(evs), file=sys.stderr)
    mb = {sp: statistics.mean(v) for sp, v in base.items()}
    for e in evs:
        e["x"] = e["r"] - mb[e["split"]]
    out = {}
    for v in ("H07", "H07-RS", "H07-BR"):
        res = {}
        for sp in ("DISCOVERY", "CONFIRM"):
            rr = [e for e in evs if e["variant"] == v and e["split"] == sp]
            mk = T2._mk(rr)
            xs = [statistics.mean(x["x"] for x in m) for m in mk]
            sd = statistics.stdev(xs) if len(xs) > 2 else None
            res[sp] = {"trades": len(rr), "market_events": len(mk), "mean_net_pct": round(100 * statistics.mean(e["r"] for e in rr), 2) if rr else None,
                       "win": round(sum(e["r"] > 0 for e in rr) / len(rr), 3) if rr else None, "baseline_mean_pct": round(100 * mb[sp], 2),
                       "mean_excess_pct": round(100 * statistics.mean(xs), 2) if xs else None,
                       "z": round(statistics.mean(xs) / (sd / len(xs) ** 0.5), 2) if sd else None}
        d, cf = res["DISCOVERY"], res["CONFIRM"]
        ok_d = d["market_events"] >= 30 and (d["mean_excess_pct"] or -1) > 0 and (d["z"] or 0) >= 2.5
        res["status"] = "PASS" if ok_d and (cf["mean_excess_pct"] or -1) > 0 else "NOT_CONFIRMED" if ok_d else (
            "INSUFFICIENT" if d["market_events"] < 30 else "FAIL")
        out[v] = res
    for v in ("H07-RS", "H07-BR"):
        better = all((out[v][sp]["mean_excess_pct"] or -99) > (out["H07"][sp]["mean_excess_pct"] or -99) for sp in ("DISCOVERY", "CONFIRM"))
        out[v]["beats_H07"] = better
        out[v]["PASS"] = out[v]["status"] == "PASS" and better
    return out


def main() -> None:
    from src.lake import research as L
    from src.lake import root

    t0 = time.time()
    u = json.loads((root() / "reports" / "universe_v1.json").read_text())
    D_all = L.load(u["chosen"])
    base = [L.base(s) for s in u["chosen"]]
    tiers = {"TOP30": [c for c in base[:30] if c in D_all], "LAB10": [c for c in L.LAB10 if c in D_all], "ALL": [c for c in base if c in D_all]}
    rep = {"version": "review17.v1", "pre_registration": "docs/research/REVIEW_17.md", "judged_on": "TOP30", "tiers": {}}
    for name, coins in tiers.items():
        D = {c: D_all[c] for c in coins}
        rs, br = rs_by_day(D), breadth_by_day(D)
        rep["tiers"][name] = {"coins": sorted(D), "T3": t3_variants(D, rs, br), "H07": h07_variants(D, rs, br)}
    rep["seconds"] = round(time.time() - t0)
    (root() / "reports" / "review17_results.json").write_text(json.dumps(rep, indent=1, default=str))
    for name, t in rep["tiers"].items():
        print("==", name, len(t["coins"]), "coins | breadth strong on", t["T3"]["breadth_strong_share_pct"], "% of days")
        for k in ("T3-B", "T3B-RS", "T3B-BR"):
            r = t["T3"][k]
            print(f"  {k:7s}", {sp: (r[sp]["total_return_pct"], r[sp]["max_dd_pct"], r[sp]["mar"]) for sp in ("DISCOVERY", "CONFIRM")}, "PASS" if r.get("PASS") else "")
        for k in ("H07", "H07-RS", "H07-BR"):
            h = t["H07"][k]
            print(f"  {k:7s}", h["status"], {sp: (h[sp]["market_events"], h[sp]["mean_excess_pct"], h[sp]["z"]) for sp in ("DISCOVERY", "CONFIRM")},
                  "beats H07" if h.get("beats_H07") else "", "PASS" if h.get("PASS") else "")


if __name__ == "__main__":
    main()
