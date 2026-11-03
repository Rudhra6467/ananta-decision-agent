"""The RS paper trial (Madhav, 2 Nov 2026): RS1's 'top tenth by 6-month strength, not stretched' recorded forward from the universe files."""
import json

import numpy as np

from india import paper, rstrial


def _uni(d, day, rows):
    (d / f"{day}.universe.json").write_text(json.dumps({"key": day, "rows": rows}))


def _rows(n=100, rets=None, seed=0):
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        out.append({"sid": f"S{i}", "symbol": f"S{i}", "rs_ret126": i / n, "dist_sma50": 0.20 if i % 2 else 0.01,
                    "ret_1": (rets or {}).get(f"S{i}", float(rng.normal(0, 0.01)))})
    return out


def test_cohort_is_top_tenth_and_not_stretched():
    c = rstrial.cohort(_rows())
    assert {r["sid"] for r in c} == {f"S{i}" for i in range(90, 100) if i % 2 == 0}      # top tenth, and the stretched half left out


def test_trial_scores_the_rs_book_against_the_average_and_a_random_book(tmp_path, monkeypatch):
    monkeypatch.setenv("INDIA_DATA_DIR", str(tmp_path))
    d = tmp_path / "paper" / "decisions"
    d.mkdir(parents=True)
    _uni(d, "2026-11-02", _rows(seed=1))
    winners = {f"S{i}": 0.02 for i in range(90, 100)}                                    # the picks rise 2% the next day, the rest about 0
    _uni(d, "2026-11-03", _rows(rets=winners, seed=2))
    _uni(d, "2026-10-30", _rows(seed=3))                                                 # before the start day: ignored
    out = rstrial.run()
    assert out["scored"] == 1 and out["sessions"][0]["cohorts_held"] == 1
    assert out["sessions"][0]["rs_vs_avg"] > 0.015                                       # 2% less the average and a twentieth of a round trip
    assert "1 of 20 scored sessions" in out["words"] and json.loads((tmp_path / "paper" / "rs_trial.json").read_text())["need"] == 20


def test_universe_rows_carry_the_rs_fields():
    c = np.linspace(100, 150, 130)
    import pandas as pd
    dates = pd.bdate_range("2026-01-01", periods=130)
    ix = pd.Series(np.linspace(1000, 1100, 130), index=dates)
    v = paper._rs126(c, dates.values, ix)
    assert abs(v - ((150 / 1100) / (c[-127] / ix.iloc[-127]) - 1)) < 1e-6
    assert paper._rs126(c[:100], dates.values[:100], ix) is None and paper._rs126(c, dates.values, None) is None
