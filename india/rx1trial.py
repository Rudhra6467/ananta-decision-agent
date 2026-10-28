"""The RX1 paper trial (Madhav, 28 Oct 2026 17:15 Toronto: "Set the remaining things to complete as well"): RX1 found one situation with an edge
known at the close: a liquid stock falling 2% or more while already below its 200-day average did worse than the average liquid stock the next
session (CONDITIONAL: -0.18% / -0.12%, open to close). This records it forward on live sessions for 20 scored sessions before anything may use it.

Nothing trades and no rule changes: each evening it reads the paper engine's universe files (paper/decisions/<day>.universe.json, written before
the next open, so the state is known in advance), lists the stocks in the state on day T, and scores them on day T+1's open-to-close move against
all 250 liquid stocks that day. It also notes which practice-book picks for T+1 were in the state (the ones the filter would have avoided) and how
they moved. After 20 scored sessions the summary says whether the live sessions agree with the history; only then may Madhav decide on a filter.

  python -m india.rx1trial run       rebuild paper/rx1_trial.json from every universe file since the start day
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from india import paths

START = "2026-10-28"
NEED = 20


def _dir() -> Path:
    return paths.data_dir() / "paper" / "decisions"


def _load(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def in_state(r: dict) -> bool:
    d200, r1 = r.get("dist_sma200"), r.get("ret_1")
    return (d200 is not None and r1 is not None and d200 < 0 and r1 <= -0.02 and not r.get("breakdown20") and not r.get("new_low_250"))


def run() -> dict:
    days = sorted(p.name[:10] for p in _dir().glob("????-??-??.universe.json") if p.name[:10] >= START)
    sessions = []
    for t, t1 in zip(days, days[1:]):
        u0, u1 = _load(_dir() / f"{t}.universe.json"), _load(_dir() / f"{t1}.universe.json")
        nxt = {r["sid"]: r for r in u1.get("rows") or [] if r.get("oc") is not None}
        state = [r for r in u0.get("rows") or [] if in_state(r)]
        if not nxt:
            continue
        all_oc = [r["oc"] for r in nxt.values()]
        sig = [(r["symbol"], nxt[r["sid"]]["oc"]) for r in state if r["sid"] in nxt]
        dec = _load(_dir() / f"{t}.json")
        picks = {x.get("sid"): x for x in dec.get("journal") or [] if x.get("status") == "chosen" and x.get("campaign") != "CTL"}
        avoided = [{"symbol": nxt[s]["symbol"] if s in nxt else picks[s].get("symbol"), "campaign": picks[s].get("campaign"), "next_oc": nxt[s]["oc"] if s in nxt else None}
                   for s in picks if s in {r["sid"] for r in state}]
        row = {"day": t, "scored_on": t1, "n_state": len(sig), "mean_state": sum(x for _, x in sig) / len(sig) if sig else None,
               "mean_all": sum(all_oc) / len(all_oc), "symbols": [s for s, _ in sig][:20], "picks_in_state": avoided}
        row["diff"] = row["mean_state"] - row["mean_all"] if row["mean_state"] is not None else None
        sessions.append(row)
    d = [s["diff"] for s in sessions if s["diff"] is not None]
    mean = sum(d) / len(d) if d else None
    sd = math.sqrt(sum((x - mean) ** 2 for x in d) / (len(d) - 1)) if len(d) > 2 else None
    t = mean / (sd / math.sqrt(len(d))) if sd else None
    done = len(d) >= NEED
    words = (f"The paper trial of 'falling 2%+ under the 200-day' has {len(d)} of {NEED} scored sessions"
             + (f": so far those stocks did {mean:+.2%} against the average liquid stock the next session (history: -0.18% / -0.12%)" if d else "")
             + (". Complete: Madhav decides whether it becomes a filter." if done else "; too early to judge."))
    out = {"what": "RX1 paper trial: liquid stocks falling 2%+ while below the 200-day, next session open to close against all 250 liquid stocks",
           "start": START, "need": NEED, "scored": len(d), "complete": done, "mean_diff": mean, "t_across_sessions": t,
           "history": {"dev_2000_2017": -0.0018, "val_2018_2023": -0.0012, "verdict": "CONDITIONAL"}, "words": words, "sessions": sessions}
    (paths.data_dir() / "paper" / "rx1_trial.json").write_text(json.dumps(out, indent=1))
    return out


if __name__ == "__main__":
    if (sys.argv[1] if len(sys.argv) > 1 else "run") == "run":
        o = run()
        print(o["words"])
