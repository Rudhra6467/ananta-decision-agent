"""21 Nov 2026 (the variable map of 20 Nov; Madhav: "the sizing changes and others we found"): when last night's Nasdaq moved 1% or more,
the morning view says how the Nifty followed on history, as a lean, not a forecast. Fails on the code before (no us_lean)."""
import pandas as pd

from india import morningview as mv


def _us(tmp_path, monkeypatch, nq_ret):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    d = tmp_path / "silver" / "us"
    d.mkdir(parents=True)
    rows = []
    for sym, r in (("SPY", 0.004), ("QQQ", nq_ret)):
        for i, day in enumerate(("2026-11-18", "2026-11-19", "2026-11-20")):
            rows.append({"symbol": sym, "date": day, "close": 100 + i, "adj_close": 100 + i, "volume": 1, "ret": r})
    pd.DataFrame(rows).to_parquet(d / "us_close.parquet")
    monkeypatch.setattr(mv, "_data", lambda: tmp_path)


def test_a_big_nasdaq_night_brings_the_lean(tmp_path, monkeypatch):
    _us(tmp_path, monkeypatch, -0.021)
    ov = mv.overnight({})
    assert ov["us_lean"]["nasdaq_ret"] == -0.021 and "2 times in 3" in ov["us_lean"]["words"] and "not a forecast" in ov["us_lean"]["words"]


def test_a_quiet_nasdaq_night_says_nothing_more(tmp_path, monkeypatch):
    _us(tmp_path, monkeypatch, 0.003)
    assert "us_lean" not in mv.overnight({})
