"""The I-0 probe: what NSE lets a script download, and how deep Kite's intraday history goes per Nifty 50 stock.

  python -m india.probe nse      sample files across 1994-2026 for cash, F&O and delivery; rate and first clean date
  python -m india.probe kite     first 5-minute and first daily candle for every Nifty 50 name (needs the Kite login)
Reports land in manifests/probe_<what>_<date>.json and print as a table. Nothing here is research: no returns, no rules.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import time

from india import nse, paths

NSE_DATES = ["1994-11-03", "1996-01-02", "2000-01-03", "2005-01-03", "2010-01-04", "2016-01-04", "2020-01-01",
             "2024-07-05", "2024-07-08", "2026-10-15"]
FO_DATES = ["2001-07-02", "2010-01-04", "2024-07-05", "2024-07-08", "2026-10-15"]
DEL_DATES = ["2016-01-04", "2020-01-01", "2024-07-08", "2026-10-15"]
LISTS = {"nifty50": "ind_nifty50list.csv", "nifty100": "ind_nifty100list.csv", "nifty500": "ind_nifty500list.csv"}


def _report(name: str, body: dict) -> None:
    paths.manifest_dir().mkdir(parents=True, exist_ok=True)
    p = paths.manifest_dir() / f"probe_{name}_{dt.date.today():%Y%m%d}.json"
    p.write_text(json.dumps(body, indent=1))
    print("report", p)


def index_lists(f: nse.Fetcher) -> dict[str, list[dict]]:
    """Current constituent lists from NSE (labels for research, never the universe rule)."""
    out: dict[str, list[dict]] = {}
    import csv
    import io

    for key, fn in LISTS.items():
        status, body, _ = f.get(f"{nse.ARCH}/content/indices/{fn}")
        if status == 200 and body:
            p = paths.bronze("indices") / f"{key}_{dt.date.today():%Y%m%d}.csv"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(body)
            rows = list(csv.DictReader(io.StringIO(body.decode("utf-8", "replace"))))
            out[key] = [{"symbol": r.get("Symbol", "").strip(), "name": r.get("Company Name", "").strip(),
                         "industry": r.get("Industry", "").strip(), "isin": r.get("ISIN Code", "").strip()} for r in rows]
        else:
            out[key] = []
        print(key, status, len(out[key]))
    return out


def nse_probe(rate_s: float = 1.0) -> dict:
    f = nse.Fetcher(rate_s=rate_s)
    rows = []
    t0 = time.time()
    for ds, dates in (("cm_bhavcopy", NSE_DATES), ("fo_bhavcopy", FO_DATES), ("delivery", DEL_DATES)):
        for s in dates:
            d = dt.date.fromisoformat(s)
            row = nse.fetch_day(f, ds, d)
            rows.append(row)
            print(f"{ds:12} {s} {row['status']} {row['bytes']:>9} B {row['seconds']:>5}s  {row['url'].split('/')[-1]}")
    lists = index_lists(f)
    out = {"when": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "rate_s": rate_s, "calls": f.calls,
           "refusals": f.refusals, "seconds": round(time.time() - t0, 1), "rows": rows,
           "lists": {k: len(v) for k, v in lists.items()}}
    ok = [r for r in rows if r["status"] == 200]
    out["first_ok"] = {ds: min((r["date"] for r in ok if r["dataset"] == ds), default=None) for ds in ("cm_bhavcopy", "fo_bhavcopy", "delivery")}
    out["files_per_hour_at_this_rate"] = round(3600 / max(rate_s, out["seconds"] / max(f.calls, 1)))
    _report("nse", out)
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, indent=1))
    return out


def kite_probe(universe: str = "nifty50") -> dict:
    """First 5-minute and first daily candle per symbol: years 2008..now in 90-day windows until the first non-empty answer."""
    import csv
    import io

    from india import kite

    k = kite.Kite()
    inst = k.instruments("NSE")
    p = paths.bronze("kite_instruments") / f"NSE_{dt.date.today():%Y%m%d}.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(inst)
    tokens = {r["tradingsymbol"]: int(r["instrument_token"]) for r in csv.DictReader(io.StringIO(inst))
              if r.get("segment") == "NSE" and r.get("instrument_type") == "EQ"}
    lst = sorted(paths.bronze("indices").glob(f"{universe}_*.csv"))
    if not lst:
        raise SystemExit("run `python -m india.probe nse` first (it saves the index lists)")
    syms = [r["Symbol"].strip() for r in csv.DictReader(io.StringIO(lst[-1].read_text(encoding="utf-8", errors="replace")))]
    today = dt.date.today()
    rows = []
    for sym in syms:
        tok = tokens.get(sym)
        row = {"symbol": sym, "instrument_token": tok, "first_5m": None, "first_day": None}
        if tok:
            for y in range(2008, today.year + 1):
                c = k.historical(tok, "5minute", dt.date(y, 1, 1), dt.date(y, 3, 31))
                if c:
                    row["first_5m"] = c[0][0][:10]
                    break
            y0 = int(row["first_5m"][:4]) if row["first_5m"] else 2008
            a = dt.date(y0, 1, 1)
            # the first daily candle: walk back in 2000-day windows from the first 5m year
            while a > dt.date(1994, 1, 1):
                b = a - dt.timedelta(days=1)
                a = max(b - dt.timedelta(days=1999), dt.date(1994, 1, 1))
                c = k.historical(tok, "day", a, b)
                if c:
                    row["first_day"] = c[0][0][:10]
                else:
                    break
            if row["first_day"] is None:
                c = k.historical(tok, "day", dt.date(y0, 1, 1), min(dt.date(y0, 1, 1) + dt.timedelta(days=1999), today))
                row["first_day"] = c[0][0][:10] if c else None
        rows.append(row)
        print(f"{sym:14} token={tok} first_5m={row['first_5m']} first_day={row['first_day']}")
    out = {"when": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "universe": universe, "user_id": k.user_id,
           "calls": k.calls, "rows": rows,
           "with_5m_from_2015_or_earlier": sum(1 for r in rows if r["first_5m"] and r["first_5m"] <= "2015-12-31"),
           "missing_token": [r["symbol"] for r in rows if not r["instrument_token"]]}
    _report("kite", out)
    print(json.dumps({k2: v for k2, v in out.items() if k2 != "rows"}, indent=1))
    return out


if __name__ == "__main__":
    paths.ensure()
    what = sys.argv[1] if len(sys.argv) > 1 else "nse"
    if what == "nse":
        nse_probe(float(sys.argv[2]) if len(sys.argv) > 2 else 1.0)
    elif what == "kite":
        kite_probe(sys.argv[2] if len(sys.argv) > 2 else "nifty50")
    else:
        raise SystemExit("nse | kite")
