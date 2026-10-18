"""Kite candles for the indices and India VIX into bronze/kite_index/<interval>/<NAME>.jsonl.gz.

  python -m india.kite_index          minute and 5-minute from 2015-02-02, daily from 2003-01-01
Indices: NIFTY 50, NIFTY BANK, NIFTY FIN SERVICE, NIFTY MIDCAP SELECT, NIFTY NEXT 50, NIFTY MIDCAP 100, NIFTY SMLCAP 100, INDIA VIX.
Windows already fetched (manifest status ok) are skipped except the last one. Stops with NeedLogin when the token dies.
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import io
import json
import time

from india import kite, paths

NAMES = ["NIFTY 50", "NIFTY BANK", "NIFTY FIN SERVICE", "NIFTY MIDCAP SELECT", "NIFTY NEXT 50", "NIFTY MIDCAP 100", "NIFTY SMLCAP 100", "INDIA VIX"]
PLAN = [("day", dt.date(2003, 1, 1)), ("5minute", dt.date(2015, 1, 1)), ("minute", dt.date(2015, 1, 1))]


def run() -> dict:
    paths.ensure()
    k = kite.Kite()
    p = paths.bronze("kite_instruments") / f"NSE_{dt.date.today():%Y%m%d}.csv"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(k.instruments("NSE"))
    idx = {r["tradingsymbol"]: int(r["instrument_token"]) for r in csv.DictReader(io.StringIO(p.read_text())) if r.get("segment") == "INDICES"}
    man = paths.manifest_dir() / "kite_index.jsonl"
    done = set()
    if man.exists():
        for line in man.read_text().splitlines():
            r = json.loads(line)
            if r.get("status") == "ok":
                done.add((r["symbol"], r["interval"], r["start"]))
    today = dt.date.today()
    n = rows = 0
    t0 = time.time()
    for interval, start in PLAN:
        step = dt.timedelta(days=kite.DAYS_PER_REQUEST[interval] - 1)
        for name in NAMES:
            tok = idx.get(name)
            if not tok:
                print("no token for", name, flush=True)
                continue
            out = paths.bronze("kite_index") / interval / f"{name}.jsonl.gz"
            out.parent.mkdir(parents=True, exist_ok=True)
            a = start
            while a <= today:
                b = min(a + step, today)
                if (name, interval, a.isoformat()) in done and b < today:
                    a = b + dt.timedelta(days=1)
                    continue
                try:
                    candles = k.historical(tok, interval, a, b)
                except kite.NeedLogin as exc:
                    print("stopped:", exc, flush=True)
                    return {"stopped": str(exc), "windows": n, "rows": rows}
                rec = {"symbol": name, "token": tok, "interval": interval, "start": a.isoformat(), "end": b.isoformat(),
                       "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "n": len(candles), "status": "ok"}
                if candles:
                    with gzip.open(out, "at") as gz:
                        gz.write(json.dumps({**rec, "candles": candles}) + "\n")
                with man.open("a") as fh:
                    fh.write(json.dumps(rec) + "\n")
                n += 1
                rows += len(candles)
                a = b + dt.timedelta(days=1)
            print(f"{interval:8} {name:22} windows={n} rows={rows} calls={k.calls} {round(time.time() - t0)}s", flush=True)
    return {"windows": n, "rows": rows, "calls": k.calls, "seconds": round(time.time() - t0)}


if __name__ == "__main__":
    print(run())
