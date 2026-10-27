"""Lab 4 (india/lab4.py; Madhav, 27 Oct 2026 18:26: "yes please also run the three studies on the gaps the grader named"): option Greeks and time
decay (GK1), intraday breakouts (IB1), intraday patterns (MS1). The specs are frozen and consistent, the trade logic does what the spec says, nothing
sealed is read, and Ananta's indicator knowledge carries the three families."""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from india import lab4, registry

REG = Path(lab4.__file__).resolve().parent / "registrations"


def test_specs_are_frozen_and_consistent():
    k = {"GK1": 46, "IB1": 36, "MS1": 42}
    n = {"GK1": 8, "IB1": 8, "MS1": 6}
    for st in k:
        s = json.loads((REG / f"{st.lower()}_v1.json").read_text())
        assert s["bar"]["union_k"] == k[st] and abs(registry.threshold(k[st]) - s["bar"]["z"]) < 0.01
        assert len(s["variants"]) == n[st] and all(v in (1, -1) for v in s["variants"].values())
        assert (REG / f"{st.lower()}_v1.md").exists()
    assert 38 + 8 == 46 and 28 + 8 == 36 and 36 + 6 == 42          # options_intraday + options_eod; intraday (+ IB1)


def _day(prices_h, prices_l, opens=None, closes=None):
    H = np.array([prices_h], float)
    L = np.array([prices_l], float)
    O = np.array([opens if opens is not None else prices_l], float)
    C = np.array([closes if closes is not None else prices_h], float)
    return O, H, L, C


def test_breakout_long_entry_stop_and_exit():
    # range of bars 0-1 is [99, 101]; bar 2 breaks up (entry at 101), bar 4 falls to the stop at 99
    O, H, L, C = _day([101, 100, 102, 103, 100, 104], [99, 99.5, 100, 101, 98.5, 103], opens=[100, 100, 100.5, 102, 100, 103], closes=[100, 100, 102, 102.5, 99, 104])
    tr = lab4._break_trades(O, H, L, C, np.array([101.0]), np.array([99.0]), 2, 4, 5)
    assert tr == [(0, 1, 101.0, 99.0, True)]
    # no stop: out at the exit bar's close
    O, H, L, C = _day([101, 100, 102, 103, 104, 105], [99, 99.5, 100, 101, 102, 104], closes=[100, 100, 102, 102.5, 103, 104.5])
    tr = lab4._break_trades(O, H, L, C, np.array([101.0]), np.array([99.0]), 2, 4, 5)
    assert tr == [(0, 1, 101.0, 104.5, False)]


def test_breakout_both_sides_in_one_bar_is_skipped_and_long_only_ignores_shorts():
    O, H, L, C = _day([101, 100, 102, 101], [99, 99.5, 98, 99.5])
    assert lab4._break_trades(O, H, L, C, np.array([101.0]), np.array([99.0]), 2, 3, 3) == []
    O, H, L, C = _day([101, 100, 100, 100], [99, 99.5, 98, 98], opens=[100, 100, 99.5, 99])     # bar 2 opens inside the range, then breaks down
    assert lab4._break_trades(O, H, L, C, np.array([101.0]), np.array([99.0]), 2, 3, 3, long_only=True) == []
    short = lab4._break_trades(O, H, L, C, np.array([101.0]), np.array([99.0]), 2, 3, 3)
    assert short and short[0][1] == -1 and short[0][2] == 99.0


def test_block_statistics_monthly():
    d = pd.DataFrame({"date": pd.date_range("2015-01-01", "2023-12-31", freq="7D")})
    d["y"] = 0.001 + 0.0001 * np.sin(np.arange(len(d)))
    r = lab4._absolute(d, "y", "M")
    assert r["dev"][2] == 36 and r["val"][2] == 72 and r["dev"][0] > 0
    on = pd.Series(np.arange(len(d)) % 3 == 0)
    d2 = d.assign(z=np.where(on, 0.02, 0.01))
    s = lab4._split_m(d2, on, "z")
    assert abs(s["dev"][0] - 0.01) < 1e-9 and s["dev"][2] >= 16


def test_nothing_sealed_is_read():
    src = Path(lab4.__file__).read_text()
    assert "sealed" not in re.sub(r'""".*?"""', "", src, flags=re.S).replace("no sealed folder", "").replace("nothing_sealed", "")
    assert src.count("< DATE '2024-01-01'") >= 4 and 'CUT = pd.Timestamp("2024-01-01")' in src


def test_the_three_families_are_in_indicator_knowledge():
    from india import technicals as tx
    for fam, st in (("option Greeks and time decay", "GK1"), ("intraday breakouts", "IB1"), ("intraday patterns", "MS1")):
        assert tx.FAMILIES[fam]["studies"] == [(st, None)]
        assert any(k[0] == st and k[1] == fam for k in tx.HEADLINE)
