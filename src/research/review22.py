"""Review #22: T3-B and H07 on the point-in-time top 30 (docs/research/REVIEW_22.md).

  python -m src.research.review22 fetch   download + build + check every PIT30 coin the lake does not hold
  python -m src.research.review22         run the two tests -> ~/ananta_lake/reports/review22_results.json
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from datetime import datetime, timezone

import pandas as pd

from src.research import portfolio_trend as P
from src.research import reads as R
from src.research import t3_turnover as TT
from src.research import teachers2 as T2
from src.research import zones as Z


def _pit():
    from src.lake import root

    return json.loads((root() / "reports" / "pit_top30.json").read_text())


def fetch() -> None:
    from src.lake import cli
    from src.lake import root

    held = set(json.loads((root() / "reports" / "universe_v1.json").read_text())["chosen"])
    missing = [s for s in _pit()["ever"] if s not in held]
    print("downloading", len(missing), missing, flush=True)
    cli.main(["all"] + missing)


def _month(t: int) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m")


def main() -> None:
    from src.lake import research as L
    from src.lake import root

    t0 = time.time()
    pit = _pit()
    members = {m: {L.base(s) for s in v} for m, v in pit["months"].items()}
    syms = pit["ever"]
    D = L.load(syms)                                   # refuses a coin with an uncut token swap
    print("coins loaded", len(D), "of", len(syms), file=sys.stderr)
    if "BTC" not in D:
        raise SystemExit("BTC missing")
    inm = lambda c, t: c in members.get(_month(t), set())   # noqa: E731

    # T3-B on PIT30
    data, days = TT.frames(D)
    sig = P.signals(data, days)
    mem = pd.DataFrame({c: [inm(c, int(d.timestamp())) for d in days] for c in sig["T3"].columns}, index=days)
    avail = sig["_avail"] & mem
    res = {"BH": TT.split(TT.simulate(data, days, avail, avail, "T3")),
           "T3-B": TT.split(TT.simulate(data, days, sig["T3"] & mem, avail, "T3-B"))}
    res["T3-B"]["PASS"] = TT.t3_rules_pass(res, "T3-B")
    res["members_per_day_avg"] = round(float(mem.sum(axis=1).mean()), 1)

    # H07 on PIT30 (signals and the baseline only on member days)
    B = R.Series(D["BTC"])
    evs, base = [], {}
    for c, bars in D.items():
        S = B if c == "BTC" else R.Series(bars)
        A = Z.Arr(S)
        rsi10 = R.rsi(S.c, 10)
        cost = R.cost(c)
        last = None
        for i in range(400, len(S.t) - 12):
            t = S.t[i]
            if t >= R.CONF_END or not inm(c, t) or S.sma200[i] is None or not A.c[i] > S.sma200[i]:
                continue
            sp = "DISCOVERY" if t < R.DISC_END else "CONFIRM"
            r = T2.h07_trade(S, A, rsi10, i + 1, cost)
            if r is None:
                continue
            base.setdefault(sp, []).append(r)
            if rsi10[i] is not None and rsi10[i] < 30 and (last is None or t - last > 5 * T2.DAY):
                last = t
                evs.append({"coin": c, "t": t, "split": sp, "r": r})
    mb = {sp: statistics.mean(v) for sp, v in base.items()}
    h = {}
    for sp in ("DISCOVERY", "CONFIRM"):
        rr = [e for e in evs if e["split"] == sp]
        mk = T2._mk(rr)
        xs = [statistics.mean(x["r"] - mb[sp] for x in m) for m in mk]
        sd = statistics.stdev(xs) if len(xs) > 2 else None
        h[sp] = {"trades": len(rr), "market_events": len(mk), "mean_net_pct": round(100 * statistics.mean(e["r"] for e in rr), 2) if rr else None,
                 "baseline_mean_pct": round(100 * mb[sp], 2), "mean_excess_pct": round(100 * statistics.mean(xs), 2) if xs else None,
                 "z": round(statistics.mean(xs) / (sd / len(xs) ** 0.5), 2) if sd else None,
                 "coins": sorted({e["coin"] for e in rr})}
    d, cf = h["DISCOVERY"], h["CONFIRM"]
    ok_d = d["market_events"] >= 30 and (d["mean_excess_pct"] or -1) > 0 and (d["z"] or 0) >= 2.5
    h["status"] = "PASS" if ok_d and (cf["mean_excess_pct"] or -1) > 0 else "NOT_CONFIRMED" if ok_d else (
        "INSUFFICIENT" if d["market_events"] < 30 else "FAIL")

    today = set(L.base(s) for s in json.loads((root() / "reports" / "universe_v1.json").read_text())["chosen"][:30])
    rep = {"version": "review22.v1", "pre_registration": "docs/research/REVIEW_22.md", "coins_ever_in_pit30": len(syms),
           "coins_loaded": len(D), "not_in_todays_top30": sorted(set(D) - today), "T3": res, "H07": h, "seconds": round(time.time() - t0)}
    (root() / "reports" / "review22_results.json").write_text(json.dumps(rep, indent=1, default=str))
    print("coins ever in PIT30", len(syms), "loaded", len(D), "| not in today's top 30:", rep["not_in_todays_top30"])
    for k in ("BH", "T3-B"):
        r = res[k]
        print(" ", k, {sp: (r[sp]["total_return_pct"], r[sp]["max_dd_pct"], r[sp]["mar"]) for sp in ("DISCOVERY", "CONFIRM")}, r.get("PASS", ""))
    print("  members/day", res["members_per_day_avg"])
    print("  H07", h["status"], {sp: (h[sp]["market_events"], h[sp]["mean_excess_pct"], h[sp]["z"]) for sp in ("DISCOVERY", "CONFIRM")})


if __name__ == "__main__":
    fetch() if sys.argv[1:2] == ["fetch"] else main()
