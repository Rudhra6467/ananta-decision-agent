"""Silver and the adjustment layer: both bhavcopy formats parse to one schema, holdout rows go to sealed/, the subject
parser reads NSE's corporate-action text, and the price-gap record snaps only to clean ratios."""
from __future__ import annotations

import datetime as dt
import io
import zipfile

import pyarrow.parquet as pq
import pytest

from india import actions, paths, silver


def _zip(name: str, text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(name, text)
    return buf.getvalue()


OLD = "SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,TIMESTAMP,TOTALTRADES,ISIN,\nINFY,EQ,1990,2030,1985,2026.5,2026,1992.1,1596460,3.2e9,10-JUN-2015,51234,INE009A01021,\n"
UDIFF = ("TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4\n"
         "2024-07-08,2024-07-08,CM,NSE,STK,1594,INE009A01021,INFY,EQ,,,,,INFOSYS LIMITED,1650.00,1670.00,1640.00,1660.50,1660.00,1648.20,,1660.50,,,5000000,8.3e9,120000,F1,1,,,,,\n")


def test_parse_both_formats(tmp_path):
    a = tmp_path / "old.csv.zip"
    a.write_bytes(_zip("cm10JUN2015bhav.csv", OLD))
    b = tmp_path / "new.csv.zip"
    b.write_bytes(_zip("BhavCopy_NSE_CM_0_0_0_20240708_F_0000.csv", UDIFF))
    da, db = silver.parse_cm(a), silver.parse_cm(b)
    assert list(da.columns) == list(db.columns) == silver.CM_COLS
    assert da.iloc[0]["date"] == dt.date(2015, 6, 10) and da.iloc[0]["prev_close"] == 1992.1 and int(da.iloc[0]["trades"]) == 51234
    assert db.iloc[0]["date"] == dt.date(2024, 7, 8) and db.iloc[0]["close"] == 1660.5 and db.iloc[0]["isin"] == "INE009A01021"


def test_holdout_years_go_to_sealed(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path / "india"))
    assert "sealed" in str(silver._year_target("cm_bhavcopy", 2024))
    assert "sealed" not in str(silver._year_target("cm_bhavcopy", 2023))


@pytest.mark.parametrize("subject,kind,ratio,amount", [
    ("Bonus 1:1", "BONUS", 2.0, None),
    ("Bonus 3:2", "BONUS", 2.5, None),
    ("Annual General Meeting/ Dividend - Rs 29.50/- Per Share And Bonus 1:1", "BONUS", 2.0, 29.5),
    ("Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share", "SPLIT", 5.0, None),
    ("FV SPLT FRM RS 10 TO RS 2", "SPLIT", 5.0, None),
    ("Bonus 1:1/Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share", "BONUS+SPLIT", 10.0, None),
    ("Consolidation Of Shares - From Re 1/- Per Share To Rs 10/- Per Share", "CONSOLIDATION", 0.1, None),
    ("Interim Dividend Rs.30/- Per Share (Purpose Revised)", "DIVIDEND", None, 30.0),
    ("Rights 1:4 @ Premium Rs 90/- Per Share", "RIGHTS", None, None),
    ("Buyback Of Shares", "BUYBACK", None, None),
])
def test_parse_subject(subject, kind, ratio, amount):
    out = actions.parse_subject(subject)
    assert out["kind"] == kind and out["ratio"] == ratio and out["amount"] == amount


def test_snap_only_clean_ratios():
    assert actions.snap(1.98) == 2.0 and actions.snap(5.1) == 5.0 and actions.snap(0.102) == 0.1
    assert actions.snap(1.7) == 1.7 and actions.snap(15.0) is None and actions.snap(1.03) is None
