"""Review #23: Nasdaq, US dollar, VIX and crypto Fear & Greed as filters on T3-B and H07 (docs/research/REVIEW_23.md).

Run: python -m src.research.review23   (writes ~/ananta_lake/reports/review23_results.json)
"""
from __future__ import annotations

import bisect
import json
import statistics
import sys
import time

import pandas as pd

from src.lake import macro as M
from src.research import portfolio_trend as P
from src.research import reads as R
from src.research import t3_turnover as TT
from src.research import teachers2 as T2
from src.research import zones as Z

DAY = 86400


class AsOf:
    """Last value (and its trailing average) dated on or before a UTC day; None before the series starts."""

    def __init__(self, sid: str, avg: int | None = None):
        df = M.load(sid).sort_values("t")
        self.t = [int(x) // DAY * DAY for x in df["t"]]
        self.v = list(df["value"].astype(float))
        self.a = list(df["value"].rolling(avg).mean()) if avg else None

    def at(self, t: int):
        i = bisect.bisect_right(self.t, t) - 1
        if i < 0:
            return None, None
        a = None if self.a is None or pd.isna(self.a[i]) else self.a[i]
        return self.v[i], a


def day_rules() -> dict:
    nq, usd, vix, fg = AsOf("NASDAQCOM", 200), AsOf("DTWEXBGS", 50), AsOf("VIXCLS"), AsOf("FNG")

    def ok(fn):
        def f(t):
            r = fn(t)
            return True if r is None else r                   # undefined: the filter does not block
        return f

    return {"T3B-NQ": ok(lambda t: (lambda v, a: None if a is None else v > a)(*nq.at(t))),
            "T3B-USD": ok(lambda t: (lambda v, a: None if a is None else v < a)(*usd.at(t))),
            "T3B-VIX": ok(lambda t: (lambda v, _: None if v is None else v < 25)(*vix.at(t))),
            "T3B-FG": ok(lambda t: (lambda v, _: None if v is None else v < 80)(*fg.at(t))),
            "H07-FG": ok(lambda t: (lambda v, _: None if v is None else v <= 30)(*fg.at(t)))}


def t3_part(D: dict, rules: dict) -> dict:
    data, days = TT.frames(D)
    sig = P.signals(data, days)
    idx = [int(d.timestamp()) for d in days]
    res = {"BH": TT.split(TT.simulate(data, days, sig["BH"], sig["_avail"], "T3")),
           "T3-B": TT.split(TT.simulate(data, days, sig["T3"], sig["_avail"], "T3-B"))}
    for k in ("T3B-NQ", "T3B-USD", "T3B-VIX", "T3B-FG"):
        m = pd.Series([rules[k](t) for t in idx], index=days)
        on = sig["T3"].mul(m, axis=0).astype(bool)
        res[k] = TT.split(TT.simulate(data, days, on, sig["_avail"], "T3-B"))
        res[k]["share_of_days_allowed_pct"] = round(100 * float(m.mean()), 1)
        res[k]["PASS"] = TT.t3_rules_pass(res, k) and all((res[k][sp]["mar"] or -9) > (res["T3-B"][sp]["mar"] or -9) for sp in ("DISCOVERY", "CONFIRM"))
    return res


def h07_part(D: dict, rules: dict) -> dict:
    B = R.Series(D["BTC"])
    evs, base = [], {}
    for c, bars in D.items():
        S = B if c == "BTC" else R.Series(bars)
        A = Z.Arr(S)
        rsi10 = R.rsi(S.c, 10)
        cost = R.cost(c)
        last: dict = {}
        for i in range(400, len(S.t) - 12):
            if S.t[i] >= R.CONF_END or S.sma200[i] is None or not A.c[i] > S.sma200[i]:
                continue
            sp = "DISCOVERY" if S.t[i] < R.DISC_END else "CONFIRM"
            r = T2.h07_trade(S, A, rsi10, i + 1, cost)
            if r is None:
                continue
            base.setdefault(sp, []).append(r)
            if rsi10[i] is not None and rsi10[i] < 30:
                for v in ["H07"] + (["H07-FG"] if rules["H07-FG"](S.t[i]) else []):
                    if v in last and S.t[i] - last[v] <= 5 * DAY:
                        continue
                    last[v] = S.t[i]
                    evs.append({"coin": c, "t": S.t[i], "variant": v, "split": sp, "r": r})
        print(c, len(evs), file=sys.stderr)
    mb = {sp: statistics.mean(v) for sp, v in base.items()}
    out = {}
    for v in ("H07", "H07-FG"):
        res = {}
        for sp in ("DISCOVERY", "CONFIRM"):
            rr = [e for e in evs if e["variant"] == v and e["split"] == sp]
            mk = T2._mk(rr)
            xs = [statistics.mean(x["r"] - mb[sp] for x in m) for m in mk]
            sd = statistics.stdev(xs) if len(xs) > 2 else None
            res[sp] = {"trades": len(rr), "market_events": len(mk), "mean_excess_pct": round(100 * statistics.mean(xs), 2) if xs else None,
                       "z": round(statistics.mean(xs) / (sd / len(xs) ** 0.5), 2) if sd else None}
        d, cf = res["DISCOVERY"], res["CONFIRM"]
        ok_d = d["market_events"] >= 30 and (d["mean_excess_pct"] or -1) > 0 and (d["z"] or 0) >= 2.5
        res["status"] = "PASS" if ok_d and (cf["mean_excess_pct"] or -1) > 0 else "NOT_CONFIRMED" if ok_d else (
            "INSUFFICIENT" if d["market_events"] < 30 else "FAIL")
        out[v] = res
    out["H07-FG"]["PASS"] = out["H07-FG"]["status"] == "PASS" and all(
        (out["H07-FG"][sp]["mean_excess_pct"] or -99) > (out["H07"][sp]["mean_excess_pct"] or -99) for sp in ("DISCOVERY", "CONFIRM"))
    return out


def main() -> None:
    from src.lake import research as L
    from src.lake import root

    t0 = time.time()
    u = json.loads((root() / "reports" / "universe_v1.json").read_text())
    D_all = L.load(u["chosen"])
    base = [L.base(s) for s in u["chosen"]]
    rules = day_rules()
    tiers = {"TOP30": [c for c in base[:30] if c in D_all], "LAB10": [c for c in L.LAB10 if c in D_all], "ALL": [c for c in base if c in D_all]}
    rep = {"version": "review23.v1", "pre_registration": "docs/research/REVIEW_23.md", "judged_on": "TOP30", "tiers": {}}
    for name, cs in tiers.items():
        D = {c: D_all[c] for c in cs}
        rep["tiers"][name] = {"coins": sorted(D), "T3": t3_part(D, rules), "H07": h07_part(D, rules)}
    rep["seconds"] = round(time.time() - t0)
    (root() / "reports" / "review23_results.json").write_text(json.dumps(rep, indent=1, default=str))
    for name, t in rep["tiers"].items():
        print("==", name)
        for k in ("T3-B", "T3B-NQ", "T3B-USD", "T3B-VIX", "T3B-FG"):
            r = t["T3"][k]
            print(f"  {k:8s}", {sp: (r[sp]["total_return_pct"], r[sp]["max_dd_pct"], r[sp]["mar"]) for sp in ("DISCOVERY", "CONFIRM")},
                  r.get("share_of_days_allowed_pct", ""), "PASS" if r.get("PASS") else "")
        for k in ("H07", "H07-FG"):
            h = t["H07"][k]
            print(f"  {k:8s}", h["status"], {sp: (h[sp]["market_events"], h[sp]["mean_excess_pct"], h[sp]["z"]) for sp in ("DISCOVERY", "CONFIRM")}, "PASS" if h.get("PASS") else "")


if __name__ == "__main__":
    main()
