"""The independent second record for raw closes: BSE's own daily bhavcopy, compared with NSE's close for the same ISIN and day.

  python -m india.bse check [pairs=300] [seed=7]
Files: bseindia.com/download/BhavCopy/Equity/EQ_ISINCODE_ddmmyy.zip (carries ISIN, available from 2017) and EQddmmyy_CSV.ZIP (2008 on,
no ISIN: matched through the BSE scrip code -> ISIN map taken from the ISIN files). Sampled dates are spread over 2008-2023 (four per
year), up to eight liquid stocks per date (top 100 NSE turnover that day that also trade on BSE). Both exchanges report unadjusted closes,
so the two should agree within 1% for liquid stocks. Gate (I0 section 5): at least 285 of 300 within 1%.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import random
import sys
import time
import zipfile

import duckdb
import pandas as pd
import requests

from india import paths

BASE = "https://www.bseindia.com/download/BhavCopy/Equity/"
H = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
     "Referer": "https://www.bseindia.com/", "Accept": "*/*"}


def _get(s: requests.Session, name: str, d: dt.date) -> pd.DataFrame | None:
    p = paths.bronze("bse_bhavcopy") / str(d.year) / name
    if not p.exists():
        r = s.get(BASE + name, timeout=30)
        time.sleep(1.0)
        if r.status_code != 200 or r.content[:2] != b"PK":
            return None
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(r.content)
    z = zipfile.ZipFile(p)
    df = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), encoding="latin1", dtype=str, on_bad_lines="skip")
    df.columns = [c.strip() for c in df.columns]
    return df


def load_day(s: requests.Session, d: dt.date) -> pd.DataFrame | None:
    tag = f"{d:%d%m%y}"
    df = _get(s, f"EQ_ISINCODE_{tag}.zip", d) if d.year >= 2017 else None
    if df is None:
        df = _get(s, f"EQ{tag}_CSV.ZIP", d)
    if df is None:
        return None
    df["CLOSE"] = pd.to_numeric(df["CLOSE"], errors="coerce")
    df["SC_CODE"] = df["SC_CODE"].str.strip()
    if "ISIN_CODE" in df:
        df["ISIN_CODE"] = df["ISIN_CODE"].str.strip()
    return df


def check(n_pairs: int = 300, seed: int = 7) -> dict:
    rng = random.Random(seed)
    root = paths.data_dir()
    con = duckdb.connect()
    con.execute(f"create view cm as select * from read_parquet(['{root}/silver/cm_bhavcopy/year=*/part.parquet'])")
    s = requests.Session()
    s.headers.update(H)
    # scrip code -> ISIN, from several ISIN files across 2017-2020 (codes are stable for a company)
    code_isin: dict[str, str] = {}
    for d in (dt.date(2017, 6, 15), dt.date(2018, 6, 15), dt.date(2019, 6, 14), dt.date(2020, 1, 10)):
        df = load_day(s, d)
        if df is not None and "ISIN_CODE" in df:
            for c, i in zip(df["SC_CODE"], df["ISIN_CODE"]):
                if isinstance(i, str) and i.startswith("IN"):
                    code_isin.setdefault(c, i)
    pairs, dates_used, missing = [], 0, []
    for y in range(2008, 2024):
        days = [r[0] for r in con.execute(f"select distinct date from cm where year(date) = {y}").fetchall()]
        for d in rng.sample(days, 4):
            bse = load_day(s, d)
            if bse is None:
                missing.append(str(d))
                continue
            dates_used += 1
            if "ISIN_CODE" not in bse:
                bse["ISIN_CODE"] = bse["SC_CODE"].map(code_isin)
            bse = bse.dropna(subset=["ISIN_CODE", "CLOSE"]).drop_duplicates("ISIN_CODE").set_index("ISIN_CODE")
            top = con.execute(f"""select isin, symbol, close from cm where date = DATE '{d}' and series = 'EQ' and isin is not null
                                  order by turnover desc limit 100""").fetchall()
            both = [(i, sym, c) for i, sym, c in top if i in bse.index]
            for i, sym, c in rng.sample(both, min(8, len(both))):
                b = float(bse.loc[i, "CLOSE"])
                pairs.append({"date": str(d), "isin": i, "symbol": sym, "nse_close": c, "bse_close": b, "pct_diff": round(100 * (c / b - 1), 3)})
    rng.shuffle(pairs)
    pairs = pairs[:n_pairs]
    within = sum(abs(p["pct_diff"]) <= 1.0 for p in pairs)
    bad = sorted((p for p in pairs if abs(p["pct_diff"]) > 1.0), key=lambda p: -abs(p["pct_diff"]))
    res = {"pairs": len(pairs), "within_1pct": within, "gate": "285 of 300", "dates_used": dates_used, "dates_without_file": missing,
           "years": sorted({p["date"][:4] for p in pairs}), "worst": bad[:10], "ran_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    (paths.manifest_dir() / f"probe_bse_check_{dt.date.today():%Y%m%d}.json").write_text(json.dumps({**res, "all_pairs": pairs}, indent=1))
    from india import catalog

    catalog.heartbeat("bse.check", within >= 285 * len(pairs) / 300, json.dumps({k: res[k] for k in ("pairs", "within_1pct", "dates_used")}))
    return res


if __name__ == "__main__":
    paths.ensure()
    if sys.argv[1] == "check":
        print(json.dumps(check(int(sys.argv[2]) if len(sys.argv) > 2 else 300, int(sys.argv[3]) if len(sys.argv) > 3 else 7), indent=1, default=str))
