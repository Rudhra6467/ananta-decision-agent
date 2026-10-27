"""The market-context feed (india/marketcontext.py; Madhav, 26 Oct 2026): readings with their own as-of dates and lags, a same-day rupee from the recorder's
USDINR future, and the fixed sentence that none of it predicts the Nifty."""
import datetime as dt
import gzip
import json

import pandas as pd
import pytest

from india import marketcontext as mc

TODAY = dt.date(2026, 10, 26)


@pytest.fixture
def lake(tmp_path, monkeypatch):
    d = tmp_path / "india"
    (d / "manifests").mkdir(parents=True)
    (d / "silver" / "macro").mkdir(parents=True)
    monkeypatch.setattr(mc.paths, "data_dir", lambda: d)
    monkeypatch.setattr(mc.paths, "manifest_dir", lambda: d / "manifests")
    monkeypatch.setattr(mc.paths, "bronze", lambda n: d / "bronze" / n)
    monkeypatch.setattr(mc.paths, "ensure", lambda: None)
    return d


def _macro(d, last="2026-10-23"):
    days = pd.bdate_range(end=last, periods=12)
    rows = []
    for sid, base in (("SP500", 7000.0), ("NASDAQCOM", 25000.0), ("DGS10", 4.9), ("DCOILBRENTEU", 100.0), ("DTWEXBGS", 121.0), ("VIXCLS", 18.0), ("DEXINUS", 94.0)):
        for i, x in enumerate(days):
            rows.append({"date": x, "series": sid, "value": base * (1 + 0.001 * i) if sid != "DGS10" else base + 0.01 * i})
    pd.DataFrame(rows).to_parquet(d / "silver" / "macro" / "macro.parquet")


def _future(d, name="USDINR26OCTFUT", folder="2026-10-28", closes=(94.0, 94.2, 94.1, 94.5, 94.6, 94.8, 95.0, 95.19)):
    p = d / "bronze" / "kite_1m_fo" / "cds" / folder
    p.mkdir(parents=True)
    days = pd.bdate_range(end="2026-10-26", periods=len(closes))
    candles = []
    for x, c in zip(days, closes):
        candles += [[f"{x.date()}T09:00:00+0530", c - 0.1, c, c - 0.1, c - 0.05, 5], [f"{x.date()}T16:59:00+0530", c, c, c, c, 9]]
    old = {"symbol": name, "candles": candles[:4]}
    new = {"symbol": name, "candles": candles}
    with gzip.open(p / f"{name}.jsonl.gz", "wt") as fh:
        fh.write(json.dumps(old) + "\n" + json.dumps(new) + "\n")        # one line per fetch: the last is the newest window


def test_macro_readings_carry_as_of_and_lag(lake):
    _macro(lake)
    r = mc.macro_readings(TODAY)
    assert r["SP500"]["as_of"] == "2026-10-23" and r["SP500"]["lag_days"] == 3 and r["SP500"]["change_kind"] == "percent"
    assert r["DGS10"]["change_kind"] == "points" and abs(r["DGS10"]["change_1"] - 0.01) < 1e-6
    assert "3 days behind today" in mc._words(r["SP500"])


def test_missing_macro_table_says_so(lake):
    r = mc.macro_readings(TODAY)
    assert all(v["status"] == "missing" for v in r.values())
    assert "no reading" in mc._words(r["SP500"])


def test_rupee_same_day_uses_the_newest_fetch_and_the_session_close(lake, monkeypatch):
    _future(lake)
    r = mc.rupee_same_day()
    assert r["status"] == "ok" and r["contract"] == "USDINR26OCTFUT" and r["as_of"] == "2026-10-26"
    assert r["value"] == 95.19 and abs(r["change_1"] - (95.19 / 95.0 - 1)) < 1e-4 and r["change_5"] > 0


def test_weekly_contracts_are_not_the_front_month(lake):
    _future(lake, name="USDINR26O30FUT", folder="2026-10-30", closes=(1.0,) * 8)
    assert mc._front_usdinr() == (None, [])


def test_flows_latest_reads_the_capture_manifest(lake):
    rows = [{"source": "nse", "status": 200, "rows": [{"date": "2026-10-26", "category": "DII", "net_cr": 2609.57}, {"date": "2026-10-26", "category": "FII", "net_cr": -1462.49}]},
            {"source": "nsdl", "status": 500, "rows": [{"date": "2026-10-27", "category": "FII", "net_cr": 1.0}]}]
    (lake / "manifests" / "fii_dii_cash.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
    f = mc.flows_latest()
    assert f["as_of"] == "2026-10-26" and f["rows"]["FII"]["net_cr"] == -1462.49 and f["rows"]["DII"]["net_cr"] == 2609.57


def test_build_says_it_explains_and_never_predicts(lake, monkeypatch):
    _macro(lake)
    _future(lake)
    monkeypatch.setattr(mc, "india_vix", lambda: {"label": "India VIX (fear gauge)", "status": "ok", "as_of": "2026-10-26", "lag_days": 0, "value": 17.16, "change_1": 0.018})
    out = mc.build()
    assert out["status"] == "ok" and "none of these readings predicts" in out["tested"] and "GIFT Nifty: no free source" in out["words"]
    assert out["gift_nifty"]["status"] == "missing" and "never to trade" in out["tested"]
    assert json.loads((lake / "manifests" / "market_context.json").read_text())["rules"] == mc.RULES
    assert mc.section()["words"] == out["words"]


def test_the_module_reads_no_sealed_folder():
    from pathlib import Path

    from india import leakcheck
    ok, msg = leakcheck.check_sealed_files()
    assert ok, msg
    body = Path(mc.__file__).read_text().split('"""', 2)[2]          # the code, not the docstring
    assert "sealed." not in body and "read_index(" not in body        # the only index read is technicals.latest_index (the logged paper_context purpose)


def test_opening_gap_is_open_against_the_previous_close(monkeypatch):
    """26 Oct: Ask said "the facts record no gap and no opening price"; the context now carries each index's open against the previous close."""
    import pandas as pd
    from india import technicals, marketcontext as mc
    df = pd.DataFrame({"index_name": ["NIFTY 50"] * 2, "date": pd.to_datetime(["2026-10-23", "2026-10-26"]),
                       "open": [22742.2, 22524.4], "close": [22600.0, 22753.2]})
    monkeypatch.setattr(technicals, "index_rows", lambda names=None, since=None: df)
    g = mc.opening_gaps()
    r = g["rows"]["NIFTY 50"]
    assert g["status"] == "ok" and r["date"] == "2026-10-26" and r["prev_close"] == 22600.0 and r["open"] == 22524.4
    assert r["gap"] == -0.0033 and r["open_to_close"] == 0.0102 and "GP1" in g["tested"]


def test_valuation_percentiles_use_2024_free_history_on_the_same_basis(tmp_path, monkeypatch):
    """27 Oct: Ananta said "my facts hold no PE or PB figure"; today's index P/E, P/B and yield come through the paper_context purpose and are
    compared with the pre-2024 file only, P/E on the same (consolidated) basis."""
    import pandas as pd
    from india import sealed, valuation, marketcontext as mc
    data = tmp_path / "india"
    (data / "silver" / "valuation").mkdir(parents=True)
    hist = pd.DataFrame({"index_name": "NIFTY 50", "date": pd.to_datetime(["2010-01-04", "2015-01-05", "2021-04-01", "2022-04-01", "2023-04-03"]),
                         "pe": [20.0, 22.0, 30.0, 22.0, 24.0], "pb": [3.0, 3.5, 4.0, 4.2, 3.8], "div_yield": [1.2, 1.3, 1.0, 1.3, 1.2],
                         "pe_basis": ["standalone", "standalone", "consolidated", "consolidated", "consolidated"]})
    hist.to_parquet(data / "silver" / "valuation" / "index_pepb.parquet")
    monkeypatch.setattr(valuation.paths, "data_dir", lambda: data)
    seen = {}
    def fake(purpose, since, names):
        seen["purpose"] = purpose
        return pd.DataFrame({"index_name": ["NIFTY 50"], "date": pd.to_datetime(["2026-10-26"]), "pe": [23.0], "pb": [2.79], "div_yield": [1.51],
                             "pe_basis": ["consolidated"]})
    monkeypatch.setattr(sealed, "read_valuation", fake)
    v = valuation.latest(("NIFTY 50",))["NIFTY 50"]
    assert seen["purpose"] == "paper_context"
    assert v["pe"] == 23.0 and v["pe_pctile"] == 33.0 and "consolidated" in v["pe_pctile_basis"]     # above 22 only, of 30/22/24
    assert v["pb_pctile"] == 0.0 and v["pb_pctile_basis"].startswith("P/B, 2010")
    monkeypatch.setattr(valuation, "latest", lambda names=valuation.INDICES: {"NIFTY 50": v})
    out = mc.valuation_latest()
    assert out["status"] == "ok" and out["as_of"] == "2026-10-26" and "VL1" in out["tested"]


def test_sealed_valuation_reader_refuses_other_purposes():
    import pytest
    from india import sealed
    for p in ("research", "holdout", "technicals_history"):
        with pytest.raises(PermissionError):
            sealed.read_valuation(p, "2026-10-01", ["NIFTY 50"])
