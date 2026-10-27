"""GP1 / TS1 / HG1 (26 Oct 2026): specs written first with a frozen bar, research rows only, the stop walk agrees with the exitlab rules."""
from pathlib import Path

import numpy as np
import pandas as pd

from india import exitlab as X
from india import gaplab, registry

ROOT = Path(__file__).resolve().parents[1]


def test_specs_freeze_the_bar_and_list_every_variant():
    for st in ("GP1", "TS1", "HG1"):
        s = gaplab.spec(st)
        assert s["study"] == st and s["variants"] and all(v in (1, -1) for v in s["variants"].values())
        assert abs(registry.threshold(s["bar"]["union_k"]) - s["bar"]["z"]) < 0.01
        assert s["bar"]["union_k"] >= len(s["variants"])
    assert gaplab.spec("GP1")["bar"]["union_k"] == len(gaplab.spec("GP1")["variants"]) == 10
    assert gaplab.spec("TS1")["bar"]["union_k"] == 93 + 15 + len(gaplab.spec("TS1")["variants"])
    assert gaplab.spec("HG1")["bar"]["union_k"] == 12 + len(gaplab.spec("HG1")["variants"])


def test_every_planned_variant_is_in_the_spec_and_back():
    gp = set(gaplab.spec("GP1")["variants"])
    assert gp == {k for k, *_ in gaplab.STK_PLAN} | {k for k, *_ in gaplab.IDX_PLAN}
    ts_vars = set(gaplab.spec("TS1")["variants"])
    for v in ts_vars:
        name, pair = v.split("|")
        a, b = pair.split("_vs_")
        assert name in gaplab.SETS and a in gaplab.RULES and b in gaplab.RULES
    hg = set(gaplab.spec("HG1")["variants"])
    assert {v.split("|")[1] for v in hg} == {"return", "worst20"}


def test_research_rows_only_and_no_sealed_reader():
    src = (ROOT / "india" / "gaplab.py").read_text()
    assert "import sealed" not in src and "from india import sealed" not in src and "india.sealed" not in src.replace("no sealed purpose", "")
    assert gaplab.CUT == pd.Timestamp("2024-01-01")


def test_one_event_per_gap():
    on = pd.Series([True, True, False, True, False, False, True, True], index=pd.date_range("2020-01-01", periods=8))
    assert gaplab._cool(on, 3).tolist() == [True, False, False, True, False, False, True, False]


def _bars(rng, n=61, start=100.0, vol=0.02, gap=0.01):
    o = np.zeros(n)
    c = np.zeros(n)
    px = start
    for i in range(n):
        o[i] = px * (1 + rng.normal(0, gap))
        c[i] = o[i] * (1 + rng.normal(0, vol))
        px = c[i]
    h = np.maximum(o, c) * (1 + rng.uniform(0, 0.01, n))
    l = np.minimum(o, c) * (1 - rng.uniform(0, 0.01, n))
    return o, h, l, c


def test_walk_agrees_with_exitlab_rules():
    """fixed2atr = exitlab hold_60d, trail2atr = atr_trail_2, hold20 = hold_20d: same exit day, price and reason on random paths (with gaps through the stop)."""
    rng = np.random.default_rng(5)
    pairs = {"fixed2atr": X.Policy("hold_60d", "hold", 60), "trail2atr": X.Policy("atr_trail_2", "atr_trail", 2), "hold20": X.Policy("hold_20d", "hold", 20)}
    checked = 0
    for _ in range(300):
        o, h, l, c = _bars(rng, vol=rng.choice([0.01, 0.02, 0.04]), gap=rng.choice([0.005, 0.02]))
        entry, atr = o[0], o[0] * rng.uniform(0.01, 0.04)
        for rule, pol in pairs.items():
            k, px, why, peak = gaplab._walk(rule, o, h, l, c, entry, atr)
            k2, px2, why2, peak2 = X._exit(pol, o, h, l, c, entry, X.STOP_ATR * atr)
            assert k == k2 and abs(px - px2) < 1e-9 and abs(peak - peak2) < 1e-9, (rule, k, k2, px, px2)
            assert (why == "stop") == (why2 == "stop")
            checked += 1
    assert checked == 900


def test_fixed7_and_trail10_by_hand():
    o = np.array([100, 101, 103, 110, 108, 99.0, 98, 97])
    h = np.array([102, 104, 111, 112, 109, 100, 99, 98.0])
    l = np.array([99, 100, 102, 107, 98, 97, 96, 95.0])
    c = np.array([101, 103, 110, 108, 99, 98, 97, 96.0])
    # fixed 7%: stop 93, never touched in 8 bars, so it sells at the final close
    k, px, why, _ = gaplab._walk("fixed7", o, h, l, c, 100.0, 2.0)
    assert (k, px, why) == (7, 96.0, "end")
    # trail 10%: peak 112 on bar 3, stop 100.8; bar 4 low 98 is through it, the open 108 is not, so it fills at the stop
    k, px, why, peak = gaplab._walk("trail10", o, h, l, c, 100.0, 2.0)
    assert k == 4 and abs(px - 100.8) < 1e-9 and why == "stop" and peak == 112
    # a gap through the stop fills at the open, not the stop
    o2, h2, l2, c2 = np.array([100, 90.0]), np.array([101, 91.0]), np.array([99, 89.0]), np.array([100, 90.0])
    k, px, why, _ = gaplab._walk("fixed7", o2, h2, l2, c2, 100.0, 2.0)
    assert (k, px, why) == (1, 90.0, "stop")


def test_quarter_helpers():
    idx = pd.bdate_range("2020-01-01", periods=130)
    r = pd.Series(0.001, index=idx)
    q = gaplab._qret(r)
    assert abs(q.iloc[0] - ((1.001) ** int((idx.to_period("Q") == idx.to_period("Q")[0]).sum()) - 1)) < 1e-12
    r2 = r.copy()
    r2.iloc[60:65] = -0.05
    w = gaplab._w20_by_quarter(r2)
    assert w.min() < -0.2
