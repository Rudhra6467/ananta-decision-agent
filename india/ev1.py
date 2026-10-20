"""EV1 (big moves, explained), first part: the Nifty 50 drawdown catalogue and a check of Madhav's remembered moves against our own data
(20 Oct 2026). DESCRIPTIVE ONLY: no test is counted, nothing here is a finding or a rule. Silver only (2003-2023); 2024+ stays sealed.

  python -m india.ev1 drawdowns    every Nifty 50 fall of 10% or more from a closing high, 2003-2023: peak, trough, depth, days down, recovery
  python -m india.ev1 seedcheck    Madhav's numbers (from his 20 Oct list, unverified) beside the same quantity measured from the lake
  python -m india.ev1 all          both -> manifests/ev1_drawdowns.json, registrations/ev1_seed_check.md

Numbers from his list are kept only here, labelled as his recollection, for comparison; the event registry never stores reaction numbers
from articles or memory (india/events.py).
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from india import paths

HERE = Path(__file__).parent


def nifty(name: str = "NIFTY 50") -> pd.DataFrame:
    D = paths.data_dir()
    f = next(p for p in (D / "silver/kite_index/day").iterdir() if p.suffix == ".parquet")
    d = pd.read_parquet(f)
    d = d[d["index_name"] == name].copy()
    d["date"] = pd.to_datetime(d["date"]).dt.date
    d = d[d["date"] <= dt.date(2023, 12, 31)].sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
    return d


def drawdowns(min_depth: float = 0.10) -> list[dict]:
    d = nifty()
    c = d["close"].to_numpy(float)
    dates = list(d["date"])
    out, i, n = [], 0, len(c)
    peak_i = 0
    while i < n:
        if c[i] >= c[peak_i]:
            peak_i = i
            i += 1
            continue
        # in a drawdown from peak_i: find where it recovers (close back at or above the peak) or the data ends
        j = i
        trough_i = i
        while j < n and c[j] < c[peak_i]:
            if c[j] < c[trough_i]:
                trough_i = j
            j += 1
        depth = c[trough_i] / c[peak_i] - 1
        if depth <= -min_depth:
            out.append({"peak": str(dates[peak_i]), "peak_close": round(float(c[peak_i]), 2), "trough": str(dates[trough_i]),
                        "trough_close": round(float(c[trough_i]), 2), "depth_pct": round(100 * depth, 1),
                        "sessions_down": trough_i - peak_i, "recovered": str(dates[j]) if j < n else None,
                        "sessions_to_recover": (j - trough_i) if j < n else None})
        peak_i = j if j < n else peak_i
        i = j + 1 if j < n else n
    return out


def _day(d: pd.DataFrame, day: str) -> dict:
    x = d[d["date"] == dt.date.fromisoformat(day)]
    if x.empty:
        return {"date": day, "note": "no session in our data"}
    k = x.index[0]
    prev = d.loc[k - 1, "close"] if k > 0 else np.nan
    r = x.iloc[0]
    return {"date": day, "close": round(float(r["close"]), 2), "prev_close": round(float(prev), 2), "day_pct": round(100 * (r["close"] / prev - 1), 2),
            "low_vs_prev_pct": round(100 * (r["low"] / prev - 1), 2), "high_vs_prev_pct": round(100 * (r["high"] / prev - 1), 2)}


def _dd_between(d: pd.DataFrame, a: str, b: str) -> dict:
    x = d[(d["date"] >= dt.date.fromisoformat(a)) & (d["date"] <= dt.date.fromisoformat(b))]
    if x.empty:
        return {}
    pk = x["close"].cummax()
    dd = x["close"] / pk - 1
    k = dd.idxmin()
    pk_i = x.loc[:k, "close"].idxmax()
    return {"window": [a, b], "peak": str(x.loc[pk_i, "date"]), "peak_close": round(float(x.loc[pk_i, "close"]), 2), "trough": str(x.loc[k, "date"]),
            "trough_close": round(float(x.loc[k, "close"]), 2), "depth_pct": round(100 * float(dd.min()), 1)}


# Madhav's list (20 Oct 2026), the quantities he gave, as he gave them (his recollection / another source; unverified)
SEED = [
    {"event": "2004 election shock", "his": "Sensex ~ -11% on 17 May 2004 (trading halted twice)", "day": "2004-05-17"},
    {"event": "2008 Global Financial Crisis", "his": "Nifty ~ -60% from the Jan 2008 peak to the Oct trough", "window": ["2008-01-01", "2008-12-31"]},
    {"event": "2013 taper tantrum", "his": "~15-18% drawdown", "window": ["2013-05-01", "2013-09-30"]},
    {"event": "2015-16 China slowdown and commodity rout", "his": "~25% drawdown", "window": ["2015-03-01", "2016-03-31"]},
    {"event": "2016 demonetisation + US election", "his": "~6% single-day drop on 9 Nov (also, in the same list: Nifty -1.3% with an intraday low ~-5%)", "day": "2016-11-09"},
    {"event": "2018 IL&FS / NBFC stress", "his": "~15% drawdown Aug-Oct 2018", "window": ["2018-08-01", "2018-10-31"]},
    {"event": "2019 corporate tax cut", "his": "sharp rebound on the tax-cut day (20 Sep 2019)", "day": "2019-09-20"},
    {"event": "2020 COVID crash day", "his": "Nifty -12.98% on 23 Mar 2020 (close 7,610.25 from 8,745.45)", "day": "2020-03-23"},
    {"event": "2020 COVID crash", "his": "~38-40% peak to trough (Jan 2020 high ~12,430 to the March low)", "window": ["2020-01-01", "2020-04-30"]},
    {"event": "2022 Russia-Ukraine + tightening", "his": "~17-18% drawdown", "window": ["2021-10-01", "2022-07-31"]},
    {"event": "2022 invasion day", "his": "(day of the invasion, 24 Feb 2022)", "day": "2022-02-24"},
    {"event": "2023 Adani-Hindenburg", "his": "index impact more limited than market-wide shocks", "window": ["2023-01-20", "2023-03-31"]},
    {"event": "drawdowns since 2006", "his": "~10 episodes of 10% or more since 2006", "count_since": "2006-01-01"},
]
SEALED_NOTE = "2024 election result (4 Jun 2024) and 2025-26: in the sealed holdout; recorded, not measured (they are the out-of-sample test)"


def seedcheck() -> list[dict]:
    d = nifty()
    dds = drawdowns()
    out = []
    for s in SEED:
        row = {"event": s["event"], "madhav_said": s["his"]}
        if "day" in s:
            row["ours"] = _day(d, s["day"])
        if "window" in s:
            row["ours"] = _dd_between(d, *s["window"])
        if "count_since" in s:
            ep = [x for x in dds if x["peak"] >= s["count_since"]]
            row["ours"] = {"episodes_10pct_or_more_2006_2023": len(ep), "list": [(x["peak"], x["trough"], x["depth_pct"]) for x in ep]}
        out.append(row)
    return out


def _fmt(o: dict) -> str:
    if not o:
        return "–"
    if "day_pct" in o:
        return f"{o['date']}: close {o['close']:,} ({o['day_pct']:+.2f}%), intraday low {o['low_vs_prev_pct']:+.2f}% vs the previous close"
    if "depth_pct" in o:
        return f"peak {o['peak']} ({o['peak_close']:,}) to trough {o['trough']} ({o['trough_close']:,}): {o['depth_pct']:+.1f}%"
    if "episodes_10pct_or_more_2006_2023" in o:
        return f"{o['episodes_10pct_or_more_2006_2023']} episodes (2006-2023)"
    return o.get("note", json.dumps(o))


def run_all() -> dict:
    dds = drawdowns()
    chk = seedcheck()
    res = {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "source": "silver/kite_index/day NIFTY 50 closes, 2003-2023",
           "label": "DESCRIPTIVE (EV1); no test counted", "drawdowns_10pct": dds, "seed_check": chk, "sealed": SEALED_NOTE}
    (paths.manifest_dir() / "ev1_drawdowns.json").write_text(json.dumps(res, indent=1, default=str))
    L = ["# EV1: Nifty 50 drawdowns and Madhav's remembered moves (descriptive)", "",
         f"Source: {res['source']}. Generated {res['at']}. No test is counted; this is a catalogue and a data check. {SEALED_NOTE}.", "",
         "## Every fall of 10% or more from a closing high (2003-2023)", "",
         "| Peak | Trough | Depth | Sessions down | Recovered | Sessions to recover |", "|---|---|---|---|---|---|"]
    for x in dds:
        L.append(f"| {x['peak']} ({x['peak_close']:,}) | {x['trough']} ({x['trough_close']:,}) | {x['depth_pct']:+.1f}% | {x['sessions_down']} | "
                 f"{x['recovered'] or 'not by end-2023'} | {x['sessions_to_recover'] if x['sessions_to_recover'] is not None else '–'} |")
    L += ["", "## Madhav's numbers beside ours", "", "| Event | Madhav's list | Measured (Nifty 50) |", "|---|---|---|"]
    for r in chk:
        L.append(f"| {r['event']} | {r['madhav_said']} | {_fmt(r.get('ours') or {})} |")
    (HERE / "registrations" / "ev1_seed_check.md").write_text("\n".join(L) + "\n")
    return {"drawdowns": len(dds), "seed_rows": len(chk)}


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "drawdowns":
        print(json.dumps(drawdowns(), indent=1))
    elif cmd == "seedcheck":
        print(json.dumps(seedcheck(), indent=1, default=str))
    else:
        print(json.dumps(run_all(), indent=1))
