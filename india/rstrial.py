"""The RS paper trial (Madhav, 2 Nov 2026 19:20 Toronto: "Yes , let's continue"): RS1 found that liquid stocks in the top tenth by 6-month
strength against the Nifty 500, not already stretched (no more than 8% above their 50-day average), beat the average liquid stock by +1.57%
(2000-17) and +2.09% (2018-23) over 20 sessions after costs, just under the strict bar (t 3.54 / 3.11 against 3.60): INCONCLUSIVE. This records
it forward on live sessions before anything may use it.

Nothing trades and no rule changes. Each evening it reads the paper engine's universe files (paper/decisions/<day>.universe.json, written at
decision time before the next open, which carry rs_ret126 and dist_sma50 from 2 Nov). On every session T it picks the stocks in that state (the
"cohort") and a random cohort of the same size (fixed seed per day), holds each cohort for the next 20 sessions, and every day scores the RS
book's return and the random book's return against the average of all 250 liquid stocks (adjusted close to close, the universe files' ret_1).
A delivery round trip (india.costs, 50,000 a pick) is charged over each cohort's 20 days. After 20 scored sessions the summary says whether the
live sessions agree with the history; only then may Madhav decide anything.

  python -m india.rstrial run       rebuild paper/rs_trial.json from every universe file since the start day
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

from india import costs, paths

START = "2026-11-02"          # the first universe file written with rs_ret126
NEED = 20
HOLD = 20
TOP = 0.90
CHASE = 0.08
HISTORY = {"dev_2000_2017": 0.0157, "val_2018_2023": 0.0209, "verdict": "INCONCLUSIVE (t 3.54 / 3.11, bar 3.60)", "study": "RS1"}


def _dir() -> Path:
    return paths.data_dir() / "paper" / "decisions"


def _load(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def cohort(rows: list[dict]) -> list[dict]:
    """RS1's 'top10|rs126_nochase': top tenth by rs_ret126 among the rows that have it, and no more than 8% above the 50-day average."""
    known = sorted((r for r in rows if r.get("rs_ret126") is not None), key=lambda r: r["rs_ret126"])
    n = len(known)
    if n < 50:
        return []
    out = []
    for i, r in enumerate(known):
        pct = (i + 1) / n                       # pandas rank(pct=True) for distinct values
        if pct >= TOP and r.get("dist_sma50") is not None and r["dist_sma50"] <= CHASE:
            out.append(r)
    return out


def run() -> dict:
    days = sorted(p.name[:10] for p in _dir().glob("????-??-??.universe.json") if p.name[:10] >= START)
    uni = {d: _load(_dir() / f"{d}.universe.json").get("rows") or [] for d in days}
    rt = costs.round_trip("delivery", 50000, 50000, turnover_rank=125)["total"] / 50000      # a round trip as a share of the pick
    cohorts = {}
    for d in days:
        c = cohort(uni[d])
        rng = random.Random(f"rs-trial-{d}")
        pool = [r for r in uni[d] if r.get("ret_1") is not None]
        ctl = rng.sample(pool, min(len(c), len(pool))) if c else []
        cohorts[d] = {"rs": [r["sid"] for r in c], "ctl": [r["sid"] for r in ctl], "symbols": [r["symbol"] for r in c]}
    sessions = []
    for j, d in enumerate(days):
        if j == 0:
            continue
        ret = {r["sid"]: r["ret_1"] for r in uni[d] if r.get("ret_1") is not None}
        if not ret:
            continue
        avg = sum(ret.values()) / len(ret)
        live = [days[i] for i in range(max(0, j - HOLD), j)]      # cohorts formed on the 20 sessions before d are held on d
        books = {}
        for side in ("rs", "ctl"):
            means = []
            for t in live:
                xs = [ret[s] for s in cohorts[t][side] if s in ret]
                if xs:
                    means.append(sum(xs) / len(xs) - rt / HOLD)
            books[side] = sum(means) / len(means) if means else None
        sessions.append({"day": d, "cohorts_held": len(live), "avg_liquid": avg, "rs_book": books["rs"], "random_book": books["ctl"],
                         "rs_vs_avg": (books["rs"] - avg) if books["rs"] is not None else None,
                         "random_vs_avg": (books["ctl"] - avg) if books["ctl"] is not None else None,
                         "picks_formed": cohorts[days[j - 1]]["symbols"][:25]})
    d = [s["rs_vs_avg"] for s in sessions if s["rs_vs_avg"] is not None]
    dc = [s["random_vs_avg"] for s in sessions if s["random_vs_avg"] is not None]
    cum = sum(d) if d else None
    cum_c = sum(dc) if dc else None
    mean = sum(d) / len(d) if d else None
    sd = math.sqrt(sum((x - mean) ** 2 for x in d) / (len(d) - 1)) if len(d) > 2 else None
    t = mean / (sd / math.sqrt(len(d))) if sd else None
    done = len(d) >= NEED
    today = cohorts[days[-1]]["symbols"] if days else []
    words = (f"The relative-strength paper trial (top tenth by 6-month strength against the Nifty, not stretched) has {len(d)} of {NEED} scored sessions"
             + (f": so far the RS picks did {cum:+.2%} against the average liquid stock after costs, random picks {cum_c:+.2%}"
                f" (history over 20 sessions: +1.57% in 2000-17, +2.09% in 2018-23)" if d else "")
             + (". Complete: Madhav decides whether anything uses it." if done else "; too early to judge. Nothing trades from it.")
             + (f" Latest picks: {', '.join(today[:8])}." if today else ""))
    out = {"what": "RS paper trial: liquid stocks in the top tenth by 6-month strength against the Nifty 500 and no more than 8% above the 50-day average, "
                   "each day's picks held 20 sessions, against the average liquid stock and a random book of the same size, after delivery costs",
           "start": START, "need": NEED, "scored": len(d), "complete": done, "cum_rs_vs_avg": cum, "cum_random_vs_avg": cum_c, "mean_daily": mean,
           "t_across_sessions": t, "round_trip_share": rt, "history": HISTORY, "latest_picks": today, "words": words, "sessions": sessions}
    (paths.data_dir() / "paper" / "rs_trial.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    if (sys.argv[1] if len(sys.argv) > 1 else "run") == "run":
        print(run()["words"])
