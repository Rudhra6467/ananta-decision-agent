"""The quote book (india/quotebook.py), the AMFI NAV file reader (india/mfdata.py) and the curated rules facts
(india/registrations/india_rules_facts.json): 27 Oct 2026, the outside review's data gaps (no price for any stock, no fund data)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from india import mfdata, quotebook

ROOT = Path(__file__).resolve().parents[1]


def _days(n, end="2026-10-27"):
    return pd.bdate_range(end=end, periods=n)


# ------------------------------------------------------------------------------------------------------------------------------ windows
def test_windows_are_calendar_not_session_counts():
    d = _days(300)
    dv = d.values.astype("datetime64[ns]")
    i = quotebook._start_index(dv, "1y")
    assert pd.Timestamp(dv[i]) <= pd.Timestamp("2025-10-27") < pd.Timestamp(dv[i + 1])      # the close on or before the same date a year back
    assert len(dv) - 1 - i < 262                                                             # about 261 weekdays, not a fixed 252 sessions
    i = quotebook._start_index(dv, "1m")
    assert pd.Timestamp(dv[i]) <= pd.Timestamp("2026-09-27")
    assert quotebook._start_index(dv, "1d") == len(dv) - 2
    assert quotebook._start_index(dv[-100:], "1y") is None                                   # too short: no 1-year change


def test_series_stats_basic_numbers():
    d = pd.Series(_days(300))
    c = np.linspace(100, 130, 300)
    c[-40] = c[-41] * 1.2                                                                    # one big day inside the last 60
    st = quotebook._series_stats(d, c, c * 1.01, c * 0.99, {"chg_1y": 0.10, "chg_ytd": 0.05})
    assert st["as_of"] == "2026-10-27" and st["close"] == pytest.approx(130.0)
    i = quotebook._start_index(d.values.astype("datetime64[ns]"), "1y")
    assert st["chg_1y"] == pytest.approx(round(c[-1] / c[i] - 1, 4))
    assert st["vs_nifty_1y"] == pytest.approx(round(st["chg_1y"] - 0.10, 4))
    assert st["high_52w"] == pytest.approx(round(max(c[-st["window_52w"]:] * 1.01), 2))
    assert st["vs_high_52w"] <= 0 and st["vs_low_52w"] >= 0
    assert st["biggest_day_60d"]["move"] == pytest.approx(0.2, abs=1e-3)
    assert 0 <= st["rsi14"] <= 100 and st["sma200"] is not None and "chg_ytd" in st


# ------------------------------------------------------------------------------------------------------------------------------ build
def _fake_lake(n=300):
    d = _days(n)
    rows = []
    specs = {"AAA": (1, 100.0, 5e8, False), "THIN": (2, 50.0, 1e5, False), "GOLDBEES": (3, 100.0, 1e6, True), "JMP": (4, 100.0, 5e8, False)}
    for sym, (sid, p0, to, fund) in specs.items():
        c = p0 * np.cumprod(np.full(n, 1.001))
        if sym == "JMP":
            c[-50:] = c[-50:] * 0.5                                                          # a demerger the adjustment missed
        for i, day in enumerate(d):
            rows.append({"sid": sid, "symbol": sym, "date": day, "close": c[i], "adj_close": c[i], "adj_high": c[i] * 1.01, "adj_low": c[i] * 0.99,
                         "volume": 1000, "turnover": to, "is_fund": fund})
    return pd.DataFrame(rows)


def _fake_index(names, since):
    d = _days(300)
    rows = []
    for j, nm in enumerate(names):
        c = 1000 * np.cumprod(np.full(300, 1 + 0.0002 * (j - 10)))
        rows += [{"index_name": nm, "date": day, "close": c[i]} for i, day in enumerate(d)]
    return pd.DataFrame(rows)


def test_build_filters_ranks_and_flags(tmp_path, monkeypatch):
    from india import paper, technicals
    monkeypatch.setattr(quotebook.paths, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(quotebook.paths, "manifest_dir", lambda: tmp_path / "manifests")
    monkeypatch.setattr(quotebook.paths, "ensure", lambda: (tmp_path / "manifests").mkdir(parents=True, exist_ok=True))
    monkeypatch.setattr(paper, "load_adjusted", lambda *a, **k: _fake_lake())
    monkeypatch.setattr(technicals, "index_rows", _fake_index)
    monkeypatch.setattr(quotebook, "name_map", lambda: {"AAA": {"name": "Aaa Industries Limited", "aliases": ["aaa"], "norm": "aaa"}})
    r = quotebook.build()
    out = json.loads((tmp_path / "manifests" / "quotebook.json").read_text())
    q = out["quotes"]
    assert "AAA" in q and "GOLDBEES" in q and "THIN" not in q                                # thin stocks dropped, every ETF kept
    assert q["GOLDBEES"]["kind"] == "etf" and q["AAA"]["name"] == "Aaa Industries Limited"
    assert q["JMP"]["price_jump_unadjusted"] is True and q["JMP"]["price_jump"]["move"] == pytest.approx(-0.5, abs=0.01)
    assert q["AAA"]["price_jump_unadjusted"] is False and q["AAA"]["price_jump"] is None
    ranks = [s["chg_3m"] for s in out["sectors"]]
    assert ranks == sorted(ranks, reverse=True) and out["sectors"][0]["rank_3m"] == 1
    assert out["gold"]["gold"]["symbol"] == "GOLDBEES" and "high_52w" in out["gold"]["gold"]
    assert out["nifty"]["chg_1y"] is not None and r["stocks"] == 2 and r["etfs"] == 1
    names = json.loads((tmp_path / "manifests" / "quotebook_names.json").read_text())
    assert names["AAA"]["liquid"] is True


def test_aliases_point_at_real_style_symbols():
    for sym, al in quotebook.ALIASES.items():
        assert sym == sym.upper() and al and all(a == a.lower() for a in al)
    assert "tata motors" in quotebook.ALIASES["TMPV"] and "zomato" in quotebook.ALIASES["ETERNAL"]


# ------------------------------------------------------------------------------------------------------------------------------ AMFI
AMFI = """Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date

Open Ended Schemes(Other Scheme - FoF Domestic)

SBI Mutual Fund

119788;INF200K01RP8;-;SBI GOLD FUND;Direct Plan;Growth Option;42.6546;27-Oct-2026
115676;INF200K01HA1;-;SBI GOLD FUND;Regular Plan;Growth Option;40.6658;27-Oct-2026
119789;INF200K01RN3;-;SBI GOLD FUND;Direct Plan;IDCW Option;42.5933;27-Oct-2026

Open Ended Schemes(Equity Scheme - Flexi Cap Fund)

PPFAS Mutual Fund

122639;INF879O01027;-;Parag Parikh Flexi Cap Fund - Direct Plan - Growth;89.30;26-Oct-2026
999999;-;-;Broken;Direct Plan;Growth Option;N.A.;27-Oct-2026
"""


def test_amfi_parse_both_layouts():
    rows = {r["code"]: r for r in mfdata.parse(AMFI)}
    a = rows[119788]
    assert a["name"] == "SBI GOLD FUND" and a["amc"] == "SBI Mutual Fund" and a["plan"] == "Direct" and a["option"] == "Growth"
    assert a["category"] == "Other Scheme - FoF Domestic" and a["type"] == "Open Ended Schemes" and a["nav"] == pytest.approx(42.6546)
    assert a["date"] == "2026-10-27" and rows[115676]["plan"] == "Regular" and rows[119789]["option"] == "IDCW"
    p = rows[122639]                                                                         # the older 6-field layout: plan and option in the name
    assert p["amc"] == "PPFAS Mutual Fund" and p["plan"] == "Direct" and p["option"] == "Growth" and p["date"] == "2026-10-26"
    assert p["category"] == "Equity Scheme - Flexi Cap Fund"
    assert rows.get(999999) is None or rows[999999]["nav"] is None                           # a non-numeric NAV never becomes a number


def test_amfi_falls_back_to_last_good_file(tmp_path, monkeypatch):
    monkeypatch.setattr(mfdata.paths, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(mfdata.paths, "manifest_dir", lambda: tmp_path / "manifests")
    (tmp_path / "manifests").mkdir()
    b = tmp_path / "bronze" / "mf"
    b.mkdir(parents=True)
    (b / "NAVAll_2026-10-26.txt").write_text(AMFI)

    def boom(*a, **k):
        raise OSError("offline")
    monkeypatch.setattr("requests.get", boom)
    r = mfdata.amfi(force=True)
    j = json.loads((tmp_path / "manifests" / "mf_schemes.json").read_text())
    assert j["schemes"] >= 4 and any(x["code"] == 119788 for x in j["rows"])
    assert r["status"] == "ok" and "fetch failed" in r["note"] and "NAVAll_2026-10-26" in r["note"]


# ------------------------------------------------------------------------------------------------------------------------------ rules facts
def test_rules_facts_are_dated_and_sourced():
    j = json.loads((ROOT / "india" / "registrations" / "india_rules_facts.json").read_text())
    ids = [f["id"] for f in j["facts"]]
    assert len(ids) == len(set(ids)) >= 15
    for f in j["facts"]:
        assert f["fact"] and f["as_of"] and f["source"] and f["topics"], f["id"]
        assert all(t == t.lower() for t in f["topics"]), f["id"]
    by = {f["id"]: f for f in j["facts"]}
    assert "12.5%" in by["equity_capital_gains"]["fact"] and "1.25 lakh" in by["equity_capital_gains"]["fact"]
    assert "91%" in by["fno_losses"]["fact"]


# ------------------------------------------------------------------------------------------------------------------------------ valuation context
def test_valuation_lowest_since_context():
    from india import valuation
    h = pd.DataFrame({"date": pd.to_datetime(["2003-01-01", "2008-12-01", "2020-03-23", "2020-06-01", "2023-12-29"]),
                      "pb": [2.0, 1.5, 1.4, 1.9, 2.6]})
    assert valuation._last_lower(h, "pb", 1.63) == {"date": "2020-03-23", "value": 1.4}
    assert valuation._last_lower(h, "pb", 1.0)["date"] is None
    v = {"pb": 1.63, "date": "2026-10-27", "pb_pctile": 6.0, "pb_pctile_basis": "P/B, 2003-09-15 to 2023-12-29", "pb_pctile_2010": 0.0,
         "pb_last_lower": {"date": "2020-05-26", "value": 1.63}}
    w = valuation._pb_words("NIFTY BANK", v)
    assert "lower than 94% of days" in w and "over 99% of days since 2010" in w and "2020-05-26" in w and "sealed" in w
