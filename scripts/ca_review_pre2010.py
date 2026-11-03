"""Evidence table for the pre-2010 big falls (3 Nov 2026). Read-only. One row per fall with: raw close before, raw open/close on the day, the
ratio to the nearest clean split/bonus value, shares traded 20 sessions after vs before, the close 20 sessions later vs before, and any NSE
corporate-action record within 40 days."""
import os, sys
import duckdb, pandas as pd
sys.path.insert(0, os.path.expanduser("~/code/ananta-records"))
from india.actions import snap

D = os.path.expanduser("~/ananta_data/india/")
fx = pd.read_csv(os.path.expanduser("~/code/ananta-records/india/registrations/big_falls_v1.csv"))
cases = fx[fx["date"] < "2010"]
con = duckdb.connect()
g = D + "silver/cm_bhavcopy/year=*/part.parquet"
rb = pd.read_parquet(D + "silver/corporate_actions/record_b.parquet")
rb["ex_date"] = pd.to_datetime(rb["ex_date"])
rows = []
for r in cases.itertuples():
    d = pd.Timestamp(r.date)
    px = con.execute(f"select date, series, open, close, volume from read_parquet('{g}', union_by_name=true) where symbol = ? and series in ('EQ','BE','BZ') "
                     f"and date between ? and ? order by date", [r.symbol, d - pd.Timedelta(days=45), d + pd.Timedelta(days=45)]).df()
    px["date"] = pd.to_datetime(px["date"])
    before, after = px[px["date"] < d], px[px["date"] >= d]
    if before.empty or after.empty:
        rows.append({"date": r.date, "symbol": r.symbol, "label": r.label, "note": "no raw prices on both sides"})
        continue
    cb, oa, ca = before["close"].iloc[-1], after["open"].iloc[0], after["close"].iloc[0]
    gap_o, gap_c = cb / oa if oa else None, cb / ca if ca else None
    v0, v1 = before["volume"].tail(20).median(), after["volume"].head(20).median()
    later = after["close"].iloc[min(19, len(after) - 1)]
    b = rb[(rb["symbol"] == r.symbol) & ((rb["ex_date"] - d).abs() <= pd.Timedelta(days=40))]
    rows.append({"date": r.date, "symbol": r.symbol, "label": r.label, "rank": r.liq_rank, "close_before": cb, "open_day": oa, "close_day": ca,
                 "gap_open": round(gap_o, 3) if gap_o else None, "snap_open": snap(gap_o) if gap_o else None, "gap_close": round(gap_c, 3) if gap_c else None,
                 "snap_close": snap(gap_c) if gap_c else None, "vol_x": round(v1 / v0, 2) if v0 else None, "later_vs_before": round(later / cb, 3),
                 "series_day": after["series"].iloc[0], "days_gap": (after["date"].iloc[0] - before["date"].iloc[-1]).days,
                 "ca": " | ".join(f"{x.ex_date.date()} {x.kind} {x.subject}" for x in b.itertuples())[:200]})
out = pd.DataFrame(rows)
out.to_csv(os.path.expanduser("~/ananta_runs/ca_review_pre2010.csv"), index=False)
pd.set_option("display.width", 260); pd.set_option("display.max_colwidth", 90); pd.set_option("display.max_rows", 400)
print(out.groupby("label").size().to_dict())
print(out.drop(columns=["rank"]).to_string(index=False))
