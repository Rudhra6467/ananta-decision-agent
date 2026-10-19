"""Weekend special sessions (19 Oct 2026 fix). The downloaders asked NSE only for weekdays, so sessions held on Saturdays and Sundays (Union
Budget Saturdays, Diwali Muhurat sessions, special live-trading Saturdays) were missing from the cash, delivery and F&O files and from the
calendar. The Kite index history has them, which is how they were found.

  python -m india.calendarfix list     writes manifests/special_sessions.json (weekend dates on which the Nifty 50 traded)
  python -m india.calendarfix fetch    downloads cash, delivery and F&O files for those dates (normal manifests, polite rate)
  python -m india.calendarfix build    rebuilds the affected silver years and the calendar
Gold tables (bars, features, universe) pick the sessions up at the next lab rebuild; registered study results are re-run after that and the
change is recorded in the ledger as a data correction.
"""
from __future__ import annotations

import datetime as dt
import json
import sys

import pandas as pd

from india import backfill, paths, sealed


def list_sessions() -> dict:
    d = pd.read_parquet(paths.data_dir() / "silver/kite_index/day/day.parquet", columns=["index_name", "date"])
    r = pd.to_datetime(d.loc[d["index_name"] == "NIFTY 50", "date"])
    s = sealed.read_cols("integrity", "silver/kite_index/day", ["date", "index_name"], "2024-01-01", "index_name = 'NIFTY 50'")
    r = pd.concat([r, pd.to_datetime(s["date"])])
    w = sorted({x.date() for x in r if x.weekday() >= 5})
    out = {"dates": [x.isoformat() for x in w], "source": "Nifty 50 days in the Kite index history falling on a Saturday or Sunday",
           "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    (paths.manifest_dir() / "special_sessions.json").write_text(json.dumps(out, indent=1))
    return {"sessions": len(w), "first": w[0].isoformat() if w else None, "last": w[-1].isoformat() if w else None}


def fetch() -> dict:
    dates = [dt.date.fromisoformat(x) for x in json.loads((paths.manifest_dir() / "special_sessions.json").read_text())["dates"]]
    res = {}
    for ds, first in (("cm_bhavcopy", dt.date(1994, 11, 3)), ("delivery", dt.date(2003, 1, 1)), ("fo_bhavcopy", dt.date(2000, 6, 12))):
        got = 0
        for d in dates:
            if d < first:
                continue
            r = backfill.run(ds, d, d, 1.0, log_every=1000)
            got += r.get("files", 0) if isinstance(r, dict) else 0
        res[ds] = got
    return res


def build() -> dict:
    from india import delivery, fo, silver
    dates = [dt.date.fromisoformat(x) for x in json.loads((paths.manifest_dir() / "special_sessions.json").read_text())["dates"]]
    years = sorted({d.year for d in dates})
    out = {}
    for y in years:
        out[y] = {"cm": silver.build_cm_year(y).get("rows") if y >= 1994 else None}
        if y >= 2003:
            out[y]["delivery"] = delivery.build_year(y).get("rows")
        if y >= 2000:
            out[y]["fo"] = fo.build_year(y).get("rows")
    out["calendar"] = silver.build_calendar()
    return out


if __name__ == "__main__":
    paths.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    print(json.dumps({"list": list_sessions, "fetch": fetch, "build": build}[cmd](), indent=1, default=str))
