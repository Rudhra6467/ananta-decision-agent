"""Bronze backfill of one NSE daily dataset over a date range, resumable, one manifest line per day.

  python -m india.backfill cm_bhavcopy 1994-11-03 2026-10-16 [rate_s]
  python -m india.backfill fo_bhavcopy 2000-06-12 2026-10-16
  python -m india.backfill delivery    2003-01-01 2026-10-16
Days already in the manifest with status 200 (file) or 404 (no file: holiday) are skipped, so a stopped run resumes.
Days that came back 204 (NSE answered with a page, not a file) or 403/429/5xx are retried on the next run.
"""
from __future__ import annotations

import datetime as dt
import sys
import time

from india import nse, paths


def run(dataset: str, start: dt.date, end: dt.date, rate_s: float = 1.0, log_every: int = 50) -> dict:
    paths.ensure()
    done = nse.manifest_rows(dataset)
    f = nse.Fetcher(rate_s=rate_s)
    n = ok = miss = bad = 0
    t0 = time.time()
    for d in nse.weekdays(start, end):
        prev = done.get(d.isoformat())
        if prev and prev.get("status") in (200, 404):
            continue
        row = nse.fetch_day(f, dataset, d)
        n += 1
        if row["status"] == 200:
            ok += 1
        elif row["status"] == 404:
            miss += 1
        else:
            bad += 1
        if n % log_every == 0:
            print(f"{dataset} {d} fetched={n} files={ok} nofile={miss} bad={bad} refusals={f.refusals} {round(time.time() - t0)}s", flush=True)
        if bad >= 20 and ok == 0:
            print("stopping: NSE is refusing every request; try again later or with a slower rate", flush=True)
            break
    out = {"dataset": dataset, "start": start.isoformat(), "end": end.isoformat(), "fetched": n, "files": ok, "nofile": miss, "bad": bad,
           "refusals": f.refusals, "seconds": round(time.time() - t0)}
    print(out, flush=True)
    return out


if __name__ == "__main__":
    ds, a, b = sys.argv[1], dt.date.fromisoformat(sys.argv[2]), dt.date.fromisoformat(sys.argv[3])
    run(ds, a, b, float(sys.argv[4]) if len(sys.argv) > 4 else 1.0)
