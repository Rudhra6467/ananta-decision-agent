"""Atlas: bracket first-hit logic (stop first, gaps), lookup fallback."""
try:
    import numpy as np

    from src.research import intraday_atlas as ia
except ImportError:
    ia = None


def test_bracket_stop_first_and_gap_and_time():
    if ia is None:
        return
    o = np.array([100.0, 100, 100, 97, 100, 100])
    h = np.array([100.5, 102, 100.2, 97.2, 100.1, 100.1])
    lo = np.array([99.5, 98.5, 99.9, 96.8, 99.9, 99.9])
    c = np.array([100.0, 100, 100, 97, 100, 100.4])
    code, res = ia._bracket(o, h, lo, c, np.array([1, 2, 4]), 0.01, 0.01, 2)
    assert code[0] == -1 and abs(res[0] + 0.01) < 1e-12          # bar 1 touches both: stop first
    assert code[1] == -1 and abs(res[1] - (97 / 100 - 1)) < 1e-12  # bar 3 opens below the stop: fill at the open
    assert code[2] == 0 and abs(res[2] - 0.004) < 1e-12           # neither: close of the last bar


def test_lookup_falls_back_to_the_setup():
    if ia is None:
        return
    atlas = {"contexts": {"E6|BEAR|BEAR": {"CONFIRM": {"n": 200}, "stable_positive_after_costs": []}},
             "setups": {"E6": {"CONFIRM": {"n": 900}, "stable_positive_after_costs": ["2/1_24h"]}}}
    assert ia.lookup(atlas, "E6", "BEAR", "BEAR")["level"] == "context"
    r = ia.lookup(atlas, "E6", "BULL", "BULL")
    assert r["level"] == "setup" and r["stable_positive_after_costs"] == ["2/1_24h"]


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print("ok", name)
