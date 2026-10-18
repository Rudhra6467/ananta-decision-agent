"""F&O bhavcopy into typed silver, one Parquet per year (2024 on under sealed/), plus the expiry calendar.

  python -m india.fo build [year ...]     (default: every complete year)
  python -m india.fo expiries              silver/fo_calendar/expiries.parquet
Two source formats, one schema. Old (2000 to Jul 2024): INSTRUMENT, SYMBOL, EXPIRY_DT, STRIKE_PR, OPTION_TYP, OHLC, SETTLE_PR, CONTRACTS,
VAL_INLAKH, OPEN_INT, CHG_IN_OI, TIMESTAMP. New UDiFF (from Jul 2024): FinInstrmTp (IDF index future, STF stock future, IDO index option,
STO stock option), TckrSymb, XpryDt, StrkPric, OptnTp, prices, UndrlygPric, SttlmPric, OpnIntrst, TtlTradgVol, TtlTrfVal, NewBrdLotQty.
Schema: date, instrument (FUTIDX FUTSTK OPTIDX OPTSTK), symbol, expiry, strike, opt_type (CE PE or null), open, high, low, close, settle,
volume (contracts), value_rs, open_interest, chg_oi, underlying (new only), lot_size (new only; for older futures lot_est = value / (contracts x close)),
source, ingested_at. Value is in rupees (old files give lakhs).
"""
from __future__ import annotations

import datetime as dt
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from india import catalog, nse, paths, silver

TYPE_MAP = {"IDF": "FUTIDX", "STF": "FUTSTK", "IDO": "OPTIDX", "STO": "OPTSTK"}
COLS = ["date", "instrument", "symbol", "expiry", "strike", "opt_type", "open", "high", "low", "close", "settle", "volume", "value_rs",
        "open_interest", "chg_oi", "underlying", "lot_size", "lot_est", "source", "ingested_at"]


def _dt(col: pd.Series) -> pd.Series:
    """NSE old-format dates: 14-May-2012, but some files carry 14-May-12."""
    a = pd.to_datetime(col, format="%d-%b-%Y", errors="coerce")
    miss = a.isna() & col.notna()
    if miss.any():
        a[miss] = pd.to_datetime(col[miss], format="%d-%b-%y")
    return a


def parse_fo(path: Path) -> pd.DataFrame:
    z = zipfile.ZipFile(path)
    raw = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), dtype=str, on_bad_lines="skip", index_col=False)
    raw.columns = [c.strip() for c in raw.columns]
    for c in ("TIMESTAMP", "TradDt"):
        if c in raw.columns:
            raw = raw[raw[c] != c]
    if "TckrSymb" in raw.columns:
        df = pd.DataFrame({
            "date": pd.to_datetime(raw["TradDt"]).dt.date, "instrument": raw["FinInstrmTp"].map(TYPE_MAP), "symbol": raw["TckrSymb"].str.strip(),
            "expiry": pd.to_datetime(raw["XpryDt"]).dt.date, "strike": pd.to_numeric(raw["StrkPric"], errors="coerce"),
            "opt_type": raw["OptnTp"].where(raw["OptnTp"].isin(["CE", "PE"])), "open": pd.to_numeric(raw["OpnPric"]), "high": pd.to_numeric(raw["HghPric"]),
            "low": pd.to_numeric(raw["LwPric"]), "close": pd.to_numeric(raw["ClsPric"]), "settle": pd.to_numeric(raw["SttlmPric"]),
            "volume": pd.to_numeric(raw["TtlTradgVol"]), "value_rs": pd.to_numeric(raw["TtlTrfVal"]), "open_interest": pd.to_numeric(raw["OpnIntrst"]),
            "chg_oi": pd.to_numeric(raw["ChngInOpnIntrst"]), "underlying": pd.to_numeric(raw["UndrlygPric"], errors="coerce"),
            "lot_size": pd.to_numeric(raw["NewBrdLotQty"], errors="coerce"), "lot_est": float("nan")})
    else:
        ot = "OPTION_TYP" if "OPTION_TYP" in raw.columns else "OPTIONTYPE"
        df = pd.DataFrame({
            "date": _dt(raw["TIMESTAMP"]).dt.date, "instrument": raw["INSTRUMENT"].str.strip(),
            "symbol": raw["SYMBOL"].str.strip(), "expiry": _dt(raw["EXPIRY_DT"]).dt.date,
            "strike": pd.to_numeric(raw["STRIKE_PR"], errors="coerce"), "opt_type": raw[ot].where(raw[ot].isin(["CE", "PE"])),
            "open": pd.to_numeric(raw["OPEN"]), "high": pd.to_numeric(raw["HIGH"]), "low": pd.to_numeric(raw["LOW"]), "close": pd.to_numeric(raw["CLOSE"]),
            "settle": pd.to_numeric(raw["SETTLE_PR"]), "volume": pd.to_numeric(raw["CONTRACTS"]), "value_rs": pd.to_numeric(raw["VAL_INLAKH"]) * 1e5,
            "open_interest": pd.to_numeric(raw["OPEN_INT"]), "chg_oi": pd.to_numeric(raw["CHG_IN_OI"]), "underlying": float("nan"), "lot_size": float("nan")})
        fut = df["instrument"].isin(["FUTIDX", "FUTSTK"]) & (df["volume"] > 0) & (df["close"] > 0)
        df["lot_est"] = float("nan")
        df.loc[fut, "lot_est"] = (df.loc[fut, "value_rs"] / (df.loc[fut, "volume"] * df.loc[fut, "close"])).round()
    df["strike"] = df["strike"].where(df["opt_type"].notna())
    return df


def build_year(year: int) -> dict:
    rows = nse.manifest_rows("fo_bhavcopy")
    now = pd.Timestamp.now(tz="UTC").floor("s")
    frames = []
    for d, r in sorted(rows.items()):
        if r.get("status") != 200 or not d.startswith(str(year)):
            continue
        df = parse_fo(paths.data_dir() / r["path"])
        df["source"] = r["sha256"][:16]
        df["ingested_at"] = now
        frames.append(df)
    if not frames:
        return {"year": year, "rows": 0}
    full = pd.concat(frames, ignore_index=True)[COLS]
    if year >= int(paths.HOLDOUT_START[:4]):
        assert (pd.to_datetime(full["date"]) >= pd.Timestamp(paths.HOLDOUT_START)).all()
    out = silver._year_target("fo_bhavcopy", year)
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pandas(full, preserve_index=False), out, compression="zstd")
    return {"year": year, "rows": len(full), "files": len(frames), "options": int(full["opt_type"].notna().sum()), "path": str(out.relative_to(paths.data_dir()))}


def expiries() -> dict:
    import duckdb

    root = paths.data_dir()
    files = [str(p) for p in list((root / "silver/fo_bhavcopy").glob("year=*/part.parquet")) + list((root / "sealed/silver/fo_bhavcopy").glob("year=*/part.parquet"))]
    con = duckdb.connect()
    con.execute(f"""create table ex as select symbol, instrument, expiry, min(date) as first_seen, max(date) as last_seen, count(distinct date) as days
                    from read_parquet({files!r}) where instrument in ('OPTIDX','FUTIDX') group by 1, 2, 3""")
    con.execute("""create table cal as select *, expiry = max(expiry) over (partition by symbol, instrument, year(expiry), month(expiry)) as is_monthly_last
                   from ex""")
    out = root / "silver" / "fo_calendar"
    out.mkdir(parents=True, exist_ok=True)
    con.execute(f"copy (select * from cal order by symbol, instrument, expiry) to '{out / 'expiries.parquet'}' (format parquet, compression zstd)")
    res = {"index_expiries": con.execute("select count(*) from cal").fetchone()[0],
           "nifty_weekday_by_year": con.execute("select year(expiry) y, dayname(expiry) d, count(*) from cal where symbol='NIFTY' and instrument='OPTIDX' and is_monthly_last = false group by 1,2 order by 1,3 desc").fetchall()[:40]}
    con.close()
    return res


if __name__ == "__main__":
    paths.ensure()
    if sys.argv[1] == "expiries":
        print(expiries())
    else:
        years = [int(y) for y in sys.argv[2:]] or silver.complete_years("fo_bhavcopy")
        for y in years:
            print(build_year(y), flush=True)
        catalog.heartbeat("fo.build", True, f"years {years}")
