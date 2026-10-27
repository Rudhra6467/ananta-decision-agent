"""Lab 3 (india/lab3.py, 27 Oct 2026): CP1 candlesticks, VL1 Nifty valuation, BT1 low beta, OS1 option spreads, CA1 corporate actions. The specs were
written before the run; the code reads nothing sealed; the percentile and the spread legs use no future information."""
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from india import lab3, registry


@pytest.mark.parametrize("study,plan", [("CP1", [k for k, *_ in lab3.CP_PLAN]), ("VL1", [k for k, *_ in lab3.VL_PLAN]), ("BT1", [k for k, *_ in lab3.BT_PLAN]),
                                        ("OS1", [k for k, *_ in lab3.OS_PLAN]), ("CA1", [k for k, *_ in lab3.CA_PLAN])])
def test_spec_variants_match_the_code_and_the_bar(study, plan):
    s = lab3.spec(study)
    assert list(s["variants"]) == plan
    assert abs(registry.threshold(int(s["bar"]["union_k"])) - float(s["bar"]["z"])) < 0.01
    assert s["written"] == "2026-10-27" and "Yes to all your recommendations" in s["asked_by"]


def test_the_module_reads_nothing_sealed_and_nothing_after_2023():
    src = Path(lab3.__file__).read_text().split('"""', 2)[2]
    assert "sealed" not in src and "holdout" not in src.replace("not the holdout", "")
    assert lab3.CUT == pd.Timestamp("2024-01-01")


def test_expanding_percentile_uses_only_earlier_days():
    x = pd.Series(np.arange(1000, dtype=float))
    p1 = lab3._expanding_pct(x, min_prior=750)
    y = x.copy()
    y.iloc[900:] = -1.0                       # change the future: the earlier percentiles must not move
    p2 = lab3._expanding_pct(y, min_prior=750)
    assert p1.iloc[:750].isna().all() and p1.iloc[750] == 1.0
    pd.testing.assert_series_equal(p1.iloc[:900], p2.iloc[:900])


def test_short_leg_sells_further_out_and_refuses_beyond_the_chain():
    from india import costs, greeks, sp1
    setup = {"expiry": dt.date(2020, 1, 30), "carry": 1.0, "listed": np.array([11900.0, 11950.0, 12000.0, 12050.0, 12100.0]),
             "CE": (np.array([11900.0, 11950.0, 12000.0, 12050.0, 12100.0]), np.array([0.14] * 5)),
             "PE": (np.array([11900.0, 11950.0, 12000.0, 12050.0, 12100.0]), np.array([0.15] * 5))}
    day = dt.date(2020, 1, 14)
    call = lab3._short_leg(sp1, greeks, costs, "NIFTY", day, setup, 1, 12000.0, 1, 12000.0, 15, 12030.0, day, 300, False, 75)
    put = lab3._short_leg(sp1, greeks, costs, "NIFTY", day, setup, -1, 12000.0, 2, 12000.0, 15, 11980.0, day, 300, False, 75)
    assert call[2] == 12050.0 and put[2] == 11900.0
    assert call[1] > 0 and put[1] > 0
    assert lab3._short_leg(sp1, greeks, costs, "NIFTY", day, setup, 1, 12100.0, 1, 12100.0, 15, 12100.0, day, 300, False, 75) is None


def test_the_five_families_carry_their_headlines_once_in_the_ledger():
    from india import technicals as tx
    k = tx.knowledge()
    if k.get("status") != "ok":
        pytest.skip("ledger unavailable")
    fams = k["families"]
    for fam, study in (("candlestick patterns", "CP1"), ("valuation (P/E, P/B)", "VL1"), ("beta and volatility", "BT1"), ("option spreads", "OS1"),
                       ("corporate actions", "CA1")):
        assert fam in fams
        f = fams[fam]
        if any(t.get("study") == study for t in f["tested"]):
            assert f["headline"] and f["headline"].startswith("Tested 27 Oct")
    assert all("Rs" in w or "%" not in w.split(":")[-1] for t in fams["option spreads"]["tested"] for w in t.get("versions", []) if w.startswith("intraday") and "rupees" in w)
