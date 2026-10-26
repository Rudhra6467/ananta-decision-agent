"""XO1 / FX1 / FII1 (26 Oct 2026): specs written first with a frozen bar, research rows only, one event per gap on an index."""
import json
from pathlib import Path

import pandas as pd

from india import registry, xstudies

ROOT = Path(__file__).resolve().parents[1]


def test_specs_freeze_the_bar_and_list_every_variant():
    for st in ("XO1", "FX1", "FII1"):
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
