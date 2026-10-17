"""Quality gate checks for the daily spine (I0 registration, section 5).

  python -m india.quality kite_day      Kite daily candles from bronze/kite_day/*.jsonl.gz into silver/ (2024+ into sealed/)
  python -m india.quality spot [n]      n random (symbol, day) pairs from the cash lake, 2003 to 2023, against Kite's daily close;
                                        the gate wants at least 297 of 300 within 0.5%
Results are rows in silver/quality/ and a heartbeat in the catalog; nothing here changes a bar.
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import sys

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from india import paths


def build_kite_day() -> dict:
    rows = []
    now = pd.Timestamp.now(tz="UTC").floor("s")
    for p in sorted(paths.bronze("kite_day").glob("*.jsonl.gz")):
        seen = set()
        with gzip.open(p, "rt") as fh:
            for line in fh:
                rec = json.loads(line)
                for c in rec["candles"]:
                    d = c[0][:10]
                    if (d) in seen:
                        continue
                    seen.add(d)
                    rows.append((dt.date.fromisoformat(d), rec["symbol"], rec["token"], float(c[1]), float(c[2]), float(c[3]), float(c[4]), int(c[5]), f"kite:{rec['token']}", now))
    df = pd.DataFrame(rows, columns=["date", "symbol", "token", "open", "high", "low", "close", "volume", "source", "ingested_at"])
    hold = df["date"] >= dt.date.fromisoformat(paths.HOLDOUT_START)
    out = paths.data_dir() / "silver" / "kite_day" / "kite_day.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(df[~hold], preserve_index=False), out, compression="zstd")
    sealed = paths.sealed_dir() / "silver" / "kite_day" / "kite_day.parquet"
    sealed.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(df[hold], preserve_index=False), sealed, compression="zstd")
    return {"rows": int((~hold).sum()), "sealed_rows": int(hold.sum()), "symbols": int(df["symbol"].nunique()), "path": str(out)}


def spot_check(n: int = 300, seed: int = 20261017, tol: float = 0.005) -> dict:
    """Kite's daily candles come back adjusted for splits and bonuses (LUPIN 2006, ICICIBANK 2008 showed it), so the check
    compares the catalog's adjusted close (NSE bars times the two-record factors) with Kite's close: one test covers the bars
    and the adjustment layer together. The raw close is kept beside it to tell the two kinds of miss apart."""
    from india import catalog

    con = catalog.connect(read_only=True)
    kd = str(paths.data_dir() / "silver" / "kite_day" / "kite_day.parquet")
    con.execute(f"select setseed({(seed % 1000) / 1000.0})")
    df = con.execute(f"""
        with pairs as (select c.date, c.symbol, c.close as nse_close, c.adj_close as nse_adj_close, c.cum_factor, c.volume as nse_volume
                       from cm_adj c
                       where c.date between '2003-01-01' and '2023-12-31' and c.close > 0
                         and c.symbol in (select distinct symbol from read_parquet('{kd}'))
                       order by random() limit {n})
        select p.*, k.close as kite_close, k.volume as kite_volume,
               abs(p.nse_adj_close / k.close - 1) as adj_diff, abs(p.nse_close / k.close - 1) as raw_diff
        from pairs p left join read_parquet('{kd}') k on k.symbol = p.symbol and k.date = p.date
        order by p.date""").df()
    con.close()
    df["within_tol"] = df["adj_diff"] <= tol
    df["kite_missing"] = df["kite_close"].isna()
    df["kind"] = ["ok" if w else ("kite_missing" if m else ("adjustment" if r <= tol else "bar")) for w, m, r in zip(df["within_tol"], df["kite_missing"], df["raw_diff"].fillna(9))]
    out_dir = paths.data_dir() / "silver" / "quality"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"spot_checks_{dt.date.today():%Y%m%d}.parquet"
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), out)
    res = {"n": len(df), "within_0_5pct": int(df["within_tol"].sum()), "kinds": df["kind"].value_counts().to_dict(),
           "max_adj_diff": float(df["adj_diff"].max()), "median_adj_diff": float(df["adj_diff"].median()),
           "gate_297_of_300": bool(df["within_tol"].sum() >= 297) if n == 300 else None, "path": str(out)}
    bad = df[~df["within_tol"]][["date", "symbol", "nse_close", "nse_adj_close", "kite_close", "adj_diff", "raw_diff", "kind"]]
    res["misses"] = bad.head(25).to_dict(orient="records")
    catalog.heartbeat("quality.spot_check", bool(res["within_0_5pct"] >= 0.99 * n), json.dumps({k: v for k, v in res.items() if k != "misses"}, default=str))
    return res


def spot_check_delivery(n: int = 300, seed: int = 20261017, tol: float = 0.005, start: str = "2020-01-01", end: str = "2023-12-31") -> dict:
    """Raw second record: the close in NSE's delivery report (a separate report, prices from 2020) against the cash bhavcopy close,
    same symbol, same day, series EQ. The gate wants at least 297 of 300 within 0.5%."""
    from india import catalog

    con = catalog.connect(read_only=True)
    con.execute(f"select setseed({(seed % 1000) / 1000.0})")
    df = con.execute(f"""
        with p as (select date, symbol, close as nse_close, open as nse_open, volume as nse_volume from cm
                   where series = 'EQ' and close > 0 and date between '{start}' and '{end}' order by random() limit {n})
        select p.*, d.close as del_close, d.open as del_open, d.traded_qty as del_volume,
               abs(p.nse_close / d.close - 1) as close_diff, abs(p.nse_open / d.open - 1) as open_diff
        from p left join delivery d on d.symbol = p.symbol and d.date = p.date and d.series = 'EQ'
        order by p.date""").df()
    con.close()
    df["within_tol"] = df["close_diff"] <= tol
    out_dir = paths.data_dir() / "silver" / "quality"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"spot_checks_delivery_{dt.date.today():%Y%m%d}.parquet"
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), out)
    res = {"n": len(df), "within_0_5pct": int(df["within_tol"].sum()), "missing_in_delivery": int(df["del_close"].isna().sum()),
           "open_within_0_5pct": int((df["open_diff"] <= tol).sum()), "volume_equal": int((df["nse_volume"] == df["del_volume"]).sum()),
           "max_close_diff": float(df["close_diff"].max()), "gate_297_of_300": bool(df["within_tol"].sum() >= 297) if n == 300 else None, "path": str(out)}
    res["misses"] = df[~df["within_tol"]][["date", "symbol", "nse_close", "del_close", "close_diff"]].head(20).to_dict(orient="records")
    catalog.heartbeat("quality.spot_check_delivery", bool(res["within_0_5pct"] >= 0.99 * n), json.dumps({k: v for k, v in res.items() if k != "misses"}, default=str))
    return res


if __name__ == "__main__":
    paths.ensure()
    what = sys.argv[1]
    if what == "kite_day":
        print(build_kite_day(), flush=True)
    elif what == "spot":
        print(json.dumps(spot_check(int(sys.argv[2]) if len(sys.argv) > 2 else 300), default=str, indent=1), flush=True)
    elif what == "spot_delivery":
        print(json.dumps(spot_check_delivery(int(sys.argv[2]) if len(sys.argv) > 2 else 300), default=str, indent=1), flush=True)
