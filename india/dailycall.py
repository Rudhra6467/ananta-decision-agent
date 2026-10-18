"""K02 / M-11: a daily written call on Nifty 50, made before the next open, scored at 1, 5 and 20 sessions. FORWARD RECORD from 19 Oct 2026.

  python -m india.dailycall run       write today's call (if not written) and score every call whose horizon has passed

Call rule v0 (mechanical, from the historical findings, fixed before any live score): BULLISH when Nifty is below its 50-day average or fell more than
1.5% on the day (E08/C01: entries in weak markets earned more over 20-60 sessions); BEARISH when Nifty is more than 5% above its 50-day average
(E04 saturation, read at the index level); NEUTRAL otherwise. A coin-flip call with a fixed seed is written beside it as the null.
Scoring: a BULLISH call scores +1 if the index is higher after the horizon, -1 if lower; BEARISH the reverse; NEUTRAL scores 0 and is counted apart.
Files: paper/calls.jsonl (one line per call, never rewritten; scores are appended as separate lines).
"""
from __future__ import annotations

import datetime as dt
import json
import random
import sys

import numpy as np
import pandas as pd

from india import paths, sealed

RULE = "call-v0-2026-10-18"
HORIZONS = (1, 5, 20)


def _nifty() -> pd.Series:
    since = (dt.date.today() - dt.timedelta(days=420)).isoformat()
    ix = sealed.read_index("paper_context", since, ["NIFTY 50"])
    ix["date"] = pd.to_datetime(ix["date"])
    return ix.set_index("date")["close"].sort_index()


def _file():
    p = paths.data_dir() / "paper" / "calls.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _rows() -> list[dict]:
    p = _file()
    return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []


def run() -> dict:
    n = _nifty()
    last = n.index[-1]
    rows = _rows()
    made = {r["data_through"] for r in rows if r["kind"] == "call"}
    out = {"data_through": str(last.date())}
    if str(last.date()) not in made:
        c = n.values
        vs50 = c[-1] / c[-50:].mean() - 1
        r1 = c[-1] / c[-2] - 1
        call = "BULLISH" if (vs50 < 0 or r1 < -0.015) else ("BEARISH" if vs50 > 0.05 else "NEUTRAL")
        null = random.Random(int(last.strftime("%Y%m%d"))).choice(["BULLISH", "BEARISH"])
        rec = {"kind": "call", "rule": RULE, "data_through": str(last.date()), "written_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "close": float(c[-1]), "nifty_vs_sma50": float(vs50), "nifty_ret1": float(r1), "call": call, "null_call": null}
        with _file().open("a") as fh:
            fh.write(json.dumps(rec) + "\n")
        out["call"] = rec
    # score
    scored = {(r["data_through"], r["horizon"]) for r in rows if r["kind"] == "score"}
    new = 0
    idx = list(n.index)
    for r in [x for x in rows if x["kind"] == "call"]:
        d0 = pd.Timestamp(r["data_through"])
        if d0 not in n.index:
            continue
        i0 = idx.index(d0)
        for h in HORIZONS:
            if (r["data_through"], h) in scored or i0 + h >= len(idx):
                continue
            move = n.iloc[i0 + h] / n.iloc[i0] - 1
            sc = lambda call: 0 if call == "NEUTRAL" else (1 if (move > 0) == (call == "BULLISH") else -1)
            with _file().open("a") as fh:
                fh.write(json.dumps({"kind": "score", "data_through": r["data_through"], "horizon": h, "move": float(move), "score": sc(r["call"]),
                                     "null_score": sc(r["null_call"]), "scored_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}) + "\n")
            new += 1
    out["new_scores"] = new
    sc = pd.DataFrame([x for x in _rows() if x["kind"] == "score"])
    if len(sc):
        out["record"] = {h: {"calls": int((g["score"] != 0).sum()), "hit": float((g.loc[g["score"] != 0, "score"] > 0).mean()) if (g["score"] != 0).any() else None,
                             "null_hit": float((g["null_score"] > 0).mean())} for h, g in sc.groupby("horizon")}
    return out


if __name__ == "__main__":
    paths.ensure()
    print(json.dumps(run(), indent=1, default=str))
