"""Kite candles into bronze: 5-minute and daily, one gzip jsonl per symbol and interval, one manifest line per window.

  python -m india.kite_backfill nifty50 5minute 2015-01-01
  python -m india.kite_backfill nifty500 5minute 2015-01-01
  python -m india.kite_backfill nifty500 day 2003-01-01
Each window the API allows (90 days of 5-minute candles, 2000 days of daily) is one request; its raw candle rows are
appended as they came, with the symbol, token, interval and window, so bronze is exactly what Kite answered. A window that
is already in the manifest with status ok is skipped unless it is the last one (today's bars are still arriving). The
token dies at 6 am IST; when it does, the job stops with NeedLogin, nudges the phone, and resumes on the next run.
"""
from __future__ import annotations

import csv
import datetime as dt
import gzip
import io
import json
import sys
import time
from pathlib import Path

from india import kite, nse, paths


def _symbols(universe: str) -> list[str]:
    lst = sorted(paths.bronze("indices").glob(f"{universe}_*.csv"))
    if not lst:
        f = nse.Fetcher(rate_s=1.0)
        from india import probe

        probe.index_lists(f)
        lst = sorted(paths.bronze("indices").glob(f"{universe}_*.csv"))
    return [r["Symbol"].strip() for r in csv.DictReader(io.StringIO(lst[-1].read_text(encoding="utf-8", errors="replace")))]


def _tokens(k: kite.Kite) -> dict[str, int]:
    today = dt.date.today()
    p = paths.bronze("kite_instruments") / f"NSE_{today:%Y%m%d}.csv"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(k.instruments("NSE"))
    return {r["tradingsymbol"]: int(r["instrument_token"]) for r in csv.DictReader(io.StringIO(p.read_text()))
            if r.get("segment") == "NSE" and r.get("instrument_type") == "EQ"}


def _manifest(interval: str) -> Path:
    paths.manifest_dir().mkdir(parents=True, exist_ok=True)
    return paths.manifest_dir() / f"kite_{interval}.jsonl"


def _done(interval: str) -> set[tuple[str, str]]:
    p = _manifest(interval)
    out = set()
    if p.exists():
        for line in p.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("status") == "ok":
                    out.add((r["symbol"], r["start"]))
    return out


def run(universe: str, interval: str, start: dt.date, end: dt.date | None = None, rate: float = 3.0, guard=None, symbols: list[str] | None = None) -> dict:
    """rate: requests a second (25 Oct: background fills run at 2 a second so the live jobs keep their share of Kite's 3 a second).
    guard: called before every request; it may sleep (the backfill driver keeps out of the live jobs' Kite windows) and returns False to stop.
    symbols: an explicit list instead of the universe file (in its order)."""
    paths.ensure()
    end = end or dt.date.today()
    k = kite.Kite(rate_per_s=rate)
    tokens = _tokens(k)
    done = _done(interval)
    ds = "kite_5m" if interval == "5minute" else f"kite_{interval}"
    step = dt.timedelta(days=kite.DAYS_PER_REQUEST[interval] - 1)
    n = rows = skipped = 0
    t0 = time.time()
    syms = symbols if symbols is not None else _symbols(universe)
    for sym in syms:
        tok = tokens.get(sym)
        if not tok:
            with _manifest(interval).open("a") as fh:
                fh.write(json.dumps({"symbol": sym, "interval": interval, "status": "no_token"}) + "\n")
            continue
        out = paths.bronze(ds) / f"{sym}.jsonl.gz"
        out.parent.mkdir(parents=True, exist_ok=True)
        a = start
        while a <= end:
            b = min(a + step, end)
            last = b >= end
            if (sym, a.isoformat()) in done and not last:
                skipped += 1
                a = b + dt.timedelta(days=1)
                continue
            if guard is not None and guard() is False:
                print("stopped by the guard", flush=True)
                return {"stopped": "guard", "windows": n, "rows": rows}
            try:
                candles = k.historical(tok, interval, a, b)
            except kite.NeedLogin as exc:
                print("stopped:", exc, flush=True)
                return {"stopped": str(exc), "windows": n, "rows": rows}
            rec = {"symbol": sym, "token": tok, "interval": interval, "start": a.isoformat(), "end": b.isoformat(),
                   "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "n": len(candles), "status": "ok"}
            with gzip.open(out, "at") as gz:
                gz.write(json.dumps({**rec, "candles": candles}) + "\n")
            with _manifest(interval).open("a") as fh:
                fh.write(json.dumps(rec) + "\n")
            n += 1
            rows += len(candles)
            a = b + dt.timedelta(days=1)
        print(f"{sym:14} windows={n} rows={rows} skipped={skipped} calls={k.calls} {round(time.time() - t0)}s", flush=True)
    res = {"universe": universe, "interval": interval, "symbols": len(syms), "windows": n, "rows": rows, "skipped": skipped,
           "calls": k.calls, "seconds": round(time.time() - t0)}
    print(res, flush=True)
    return res


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], dt.date.fromisoformat(sys.argv[3]))
