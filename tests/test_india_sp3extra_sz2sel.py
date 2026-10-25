"""SP3's remaining parts (india/sp3extra.py) and the SZ2 selection engine (india/sz2sel.py): the book arithmetic and the sizing rules on small
synthetic inputs (no lake needed), and the sealed SZ2 reader's refusals."""
import types

import numpy as np
import pandas as pd
import pytest

from india import sealed, sp3extra, sz2sel


def _index_X(n_bars=8):
    sess = pd.date_range("2020-01-01", periods=n_bars + 2, freq="B")
    Pc = np.array([[2.0, 5.0, 1.0, 4.0, 6.0, 6.0, 6.0, 6.0]])
    Po = np.array([[0.0, 3.0, 2.0, 2.0, 5.0, 7.0, 7.0, 7.0]])
    roll = np.zeros((1, n_bars), bool); roll[0, 2] = True
    X = {"sess": sess, "s0": np.array([1]), "n_valid": np.array([n_bars]), "E": np.array([100.0]), "Pc": Pc, "Po": Po, "roll_at": roll,
         "fee_in": np.array([[0.001, 0.0012]]), "fee_roll": np.zeros((1, n_bars, 2)), "fee_out": np.full((1, n_bars, 2), 0.0005),
         "exit_bar": np.array([[4] * sp3extra.INA])}
    X["fee_roll"][0, 2] = [0.002, 0.002]
    T = sp3extra.TICK
    # long, exit at the open of bar 4: points Po[4] = 5, ticks entry + exit + 2 for the roll
    X["gross"] = np.array([[(5.0 - 4 * T) / 100.0] * 5 + [(-5.0 - 4 * T) / 100.0] * 5])
    X["fees"] = np.array([[0.001 + 0.002 + 0.0005] * 5 + [0.0012 + 0.002 + 0.0005] * 5])
    return X


def test_index_book_daily_returns_add_up_to_the_trade_net():
    X = _index_X()
    b = sp3extra.IndexBook(X)
    for a in (0, 5):                              # a long and a short action
        r = b.run(1, 8, {1: (0, a)})
        assert abs(r["daily"].sum() - (X["gross"][0, a] - X["fees"][0, a])) < 1e-12
        assert len(r["trades"]) == 1 and r["trades"]["exit_s"].iloc[0] == 5


def test_index_book_takes_one_position_and_no_rebuy_at_the_exit_open():
    X = _index_X()
    b = sp3extra.IndexBook(X)
    r = b.run(1, 8, {1: (0, 0), 3: (0, 0), 5: (0, 0)})       # 3: a position is open; 5: the old one exits at that open
    assert len(r["trades"]) == 1


def test_reverse_priority_flags_pick_the_reverse_family_and_keep_any_last():
    cand = pd.DataFrame({"sid": ["A", "A", "A", "B", "B"], "signal_date": pd.to_datetime(["2020-01-02"] * 3 + ["2020-01-02"] * 2),
                         "family": ["RETEST", "LO52", "CTL", "ANY", "BRK"]})
    d = types.SimpleNamespace(cand=cand, N=len(cand))
    f = sp3extra.reverse_priority_flags(d)
    assert f.tolist() == [False, True, False, False, True]   # LO52 beats RETEST in reverse; a real family still beats ANY; CTL never


def _slots(ml=1000.0, net=100.0, f_flag=False, two=False, nextopen=False):
    n = 1
    A = {k: np.zeros((n, 2)) for k in sz2sel.Slots.F}
    A["reason"] = np.full((n, 2), "", dtype=object); A["sym"] = np.full((n, 2), "", dtype=object); A["row"] = np.full((n, 2), -1)
    for j in range(2 if two else 1):
        A["exists"][0, j] = A["avail"][0, j] = 1
        A["m_in"][0, j] = 1 if j == 0 else 15
        A["m_out"][0, j] = (sz2sel.NMIN + 1) if (nextopen and j == 0) else 200
        A["ml"][0, j], A["net"][0, j], A["marg"][0, j] = ml, net, ml
        A["nextopen"][0, j] = float(nextopen and j == 0)
        A["flag"][0, j] = float(f_flag)
    S = types.SimpleNamespace(A=A, n=n, marks={(0, j): np.linspace(0, -3 * ml if f_flag else -0.1 * ml, 400) for j in range(2)})
    return S


def test_sizing_floor_budget_and_size_zero():
    S = _slots(ml=1000.0, net=100.0)
    r = sz2sel.run_paths(S, np.zeros((1, 1), int), 0.02, 60_000.0, paused_mode=True)
    assert r["taken"][0] == 1 and abs(r["eq"][0, 0] - (60_000.0 + 1 * 100.0)) < 1e-9          # floor(1,200 / 1,000) = 1 lot
    r = sz2sel.run_paths(_slots(ml=5000.0), np.zeros((1, 1), int), 0.02, 60_000.0, paused_mode=True)
    assert r["taken"][0] == 0 and r["reasons"]["size_zero"] == 1
    # two trades at once: the second is cut to the budget left by the first's planned max loss (5% x W = 3,000)
    S2 = _slots(ml=1000.0, net=0.0, two=True)
    r = sz2sel.run_paths(S2, np.zeros((1, 1), int), 0.05, 60_000.0, paused_mode=True)
    assert r["taken"][0] == 1 and r["reasons"]["budget"] == 1


def test_limit_replay_closes_the_day_when_a_position_loses_beyond_its_plan():
    S = _slots(ml=1000.0, net=-3000.0, f_flag=True)
    r = sz2sel.run_paths(S, np.zeros((1, 1), int), 0.05, 60_000.0, paused_mode=True)
    assert r["limit_days"][0] == 1 and r["eq"][0, 0] < 60_000.0


def test_sealed_sz2_reader_refuses_other_purposes():
    with pytest.raises(PermissionError):
        sealed.read_sz2("paper_lookback", "policy_trades")
    with pytest.raises(PermissionError):
        sealed.sz2_output_dir("holdout")
