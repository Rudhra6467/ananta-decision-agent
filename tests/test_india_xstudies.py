"""XO1 / FX1 / FII1 / SR1 (26 Oct 2026): specs written first with a frozen bar, research rows only, one event per gap on an index."""
import json
from pathlib import Path

import pandas as pd

from india import registry, xstudies

ROOT = Path(__file__).resolve().parents[1]


def test_specs_freeze_the_bar_and_list_every_variant():
    for st in ("XO1", "FX1", "FII1", "SR1"):
        s = xstudies.spec(st)
        assert s["study"] == st and s["variants"] and all(v in (1, -1) for v in s["variants"].values())
        assert abs(registry.threshold(s["bar"]["union_k"]) - s["bar"]["z"]) < 0.01
        assert s["bar"]["union_k"] >= len(s["variants"])
    assert xstudies.spec("XO1")["bar"]["union_k"] == len(xstudies.spec("XO1")["variants"]) == 27


def test_research_rows_only_and_nothing_sealed():
    src = (ROOT / "india" / "xstudies.py").read_text()
    assert "sealed" not in src.lower()
    assert xstudies.CUT == pd.Timestamp("2024-01-01")


def test_one_index_event_per_gap():
    on = pd.Series([True, True, False, True, False, False, True, True], index=pd.date_range("2020-01-01", periods=8))
    kept = xstudies._cool(on, 3)
    assert kept.tolist() == [True, False, False, True, False, False, True, False]


def test_sr1_bar_counts_xo1_in_the_same_family():
    s = xstudies.spec("SR1")
    assert s["family"] == xstudies.spec("XO1")["family"] == "technical"
    assert s["bar"]["union_k"] == 27 + len(s["variants"]) == 38


def test_sr1_levels_are_the_panels_own():
    """What Ananta says (india/technicals.py swings, last 60 sessions) and what SR1 tested are the same support and resistance, on every day."""
    import numpy as np

    from india import technicals as tx
    rng = np.random.default_rng(11)
    n = 220
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.015, n)))
    h, l = c * (1 + rng.uniform(0, 0.01, n)), c * (1 - rng.uniform(0, 0.01, n))
    for w in (20, 60):
        S, R = xstudies._levels(h, l, c, w)
        assert np.isnan(S[:w]).all() and np.isnan(R[:w]).all()
        for t in range(w, n):
            sh, sl = tx.swings(pd.Series(h[:t]), pd.Series(l[:t]), window=w)
            sup = [v for _, v in sl if v < c[t - 1]]
            res = [v for _, v in sh if v > c[t - 1]]
            assert np.isclose(max(sup) if sup else np.nan, S[t], equal_nan=True), (w, t)
            assert np.isclose(min(res) if res else np.nan, R[t], equal_nan=True), (w, t)


def test_sr1_levels_never_look_ahead():
    import numpy as np
    rng = np.random.default_rng(3)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 150)))
    S, R = xstudies._levels(c, c, c, 60)
    c2 = c.copy()
    c2[100:] *= 0.5                              # change the future from row 100 on
    S2, R2 = xstudies._levels(c2, c2, c2, 60)
    assert np.allclose(S[:101], S2[:101], equal_nan=True) and np.allclose(R[:101], R2[:101], equal_nan=True)
