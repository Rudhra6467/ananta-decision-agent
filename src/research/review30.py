"""Review #30: T3-B on the point-in-time top 10 (docs/research/REVIEW_30.md). Same code path as review #22's T3-B test.

  python -m src.research.review30         one test -> ~/ananta_lake/reports/review30_results.json
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone

import pandas as pd

from src.research import portfolio_trend as P
from src.research import t3_turnover as TT


def _month(t: int) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m")


def _short(r: dict) -> dict:
    return {sp: {k: r[sp][k] for k in ("total_return_pct", "max_dd_pct", "mar")} for sp in ("DISCOVERY", "CONFIRM")}


def main() -> None:
    from src.lake import pit, root
    from src.lake import research as L

    t0 = time.time()
    pt = pit.membership(10)                                   # reports/pit_top10.json: earlier months only, as in review #22
    members = {m: {L.base(s) for s in v} for m, v in pt["months"].items()}
    syms = pt["ever"]
    D = L.load(syms)                                         # refuses a coin with an uncut token swap; LUNA cut at ENDS
    print("coins loaded", len(D), "of", len(syms), file=sys.stderr)
    if "BTC" not in D:
        raise SystemExit("BTC missing")
    inm = lambda c, t: c in members.get(_month(t), set())   # noqa: E731

    data, days = TT.frames(D)
    sig = P.signals(data, days)
    mem = pd.DataFrame({c: [inm(c, int(d.timestamp())) for d in days] for c in sig["T3"].columns}, index=days)
    avail = sig["_avail"] & mem
    res = {"BH": TT.split(TT.simulate(data, days, avail, avail, "T3")),
           "T3-B": TT.split(TT.simulate(data, days, sig["T3"] & mem, avail, "T3-B"))}
    res["T3-B"]["PASS"] = TT.t3_rules_pass(res, "T3-B")
    res["members_per_day_avg"] = round(float(mem.sum(axis=1).mean()), 1)

    lab = [L.base(c) for c in L.LAB10]
    r20 = json.loads((root() / "reports" / "review20_results.json").read_text())["tiers"]["LAB10"]["results"]
    rep = {"version": "review30.v1", "pre_registration": "docs/research/REVIEW_30.md", "coins_ever_in_pit10": len(syms),
           "coins_loaded": len(D), "not_in_todays_10": sorted(set(D) - set(lab)), "T3": res,
           "beside_not_tested": {"T3-B_on_todays_lab10_review20": _short(r20["T3-B"]), "BH_on_todays_lab10_review20": _short(r20["BH"])},
           "seconds": round(time.time() - t0)}
    (root() / "reports" / "review30_results.json").write_text(json.dumps(rep, indent=1, default=str))
    print("coins ever in PIT10", len(syms), "loaded", len(D), "| not in today's 10:", rep["not_in_todays_10"])
    for k in ("BH", "T3-B"):
        r = res[k]
        print(" ", k, {sp: (r[sp]["total_return_pct"], r[sp]["max_dd_pct"], r[sp]["mar"]) for sp in ("DISCOVERY", "CONFIRM")}, r.get("PASS", ""))
    print("  members/day", res["members_per_day_avg"], "| T3-B on today's 10 (review #20):", rep["beside_not_tested"]["T3-B_on_todays_lab10_review20"])


if __name__ == "__main__":
    main()
