"""SP3 runner: the vectorised action harness must reproduce exitlab._exit bar for bar (the independent re-derivation the spec asks for),
and the forced ends (halt, data_end, permanent stops) must follow in_window_events."""
import numpy as np
import pandas as pd
import pytest

from india import exitlab
from india import sp3run as R


def _windows(n_rows: int, seed: int) -> tuple:
    rng = np.random.default_rng(seed)
    W = R.W
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, (n_rows, W + 25)), axis=1))
    o = c * np.exp(rng.normal(0, 0.01, c.shape))
    h = np.maximum(o, c) * np.exp(np.abs(rng.normal(0, 0.012, c.shape)))
    l = np.minimum(o, c) * np.exp(-np.abs(rng.normal(0, 0.012, c.shape)))
    # ll20 from the 20 bars before each bar (history included), as the holding-bars table computes it
    ll20 = np.full(c.shape, np.nan)
    for i in range(20, c.shape[1]):
        ll20[:, i] = l[:, i - 20:i].min(axis=1)
    k = 25   # entry bar in the long arrays
    atr = np.full(n_rows, 3.0)
    return o[:, k:], h[:, k:], l[:, k:], c[:, k:], ll20[:, k:], atr


@pytest.mark.parametrize("name,kind,n,stop_atr", R.ACTIONS)
def test_actions_match_exitlab(name, kind, n, stop_atr):
    O, H, L, C, LL, atr = _windows(300, 11)
    entry = O[:, 0]
    nv = np.full(len(O), R.W)
    eb, px, why = R.action_exits(kind, n, stop_atr, O, H, L, C, LL, entry, atr, nv)
    pol = {"hold": "hold", "target": "target", "trail": "atr_trail", "sma": "sma_close", "swing": "swing_low", "scale_half": "scale_half", "hold_low20": "hold"}[kind]
    sig = ("low20",) if kind == "hold_low20" else ()
    p = exitlab.Policy(name, pol, n, sig)
    bad = 0
    for i in range(len(O)):
        risk = (stop_atr if stop_atr is not None else np.inf) * atr[i]
        aux = {"ll20": LL[i]}
        k, px_e, why_e, _ = exitlab._exit(p, O[i], H[i], L[i], C[i], entry[i], risk, aux=aux)
        # exitlab's R unit is the stop distance; SP3's is always 2 ATR, so only the exit bar and price are compared
        if why_e == "end":
            ok = eb[i] >= R.W or (eb[i] == R.W - 1 and False)
            ok = eb[i] >= R.W
        else:
            ok = eb[i] == k and abs(px[i] - px_e) < 1e-9
        bad += 0 if ok else 1
    assert bad == 0, f"{name}: {bad} of {len(O)} windows differ from exitlab"


def test_roll_helpers():
    C = np.arange(1, 8, dtype=float)[None, :]
    m = R._roll_mean(C, 3)
    assert np.isnan(m[0, :2]).all() and m[0, 2] == 2.0 and m[0, 6] == 6.0
    L = np.array([[5, 3, 4, 1, 2, 6, 7.0]])
    mn = R._roll_min_prev(L, 2)
    assert np.isnan(mn[0, :2]).all() and mn[0, 2] == 3 and mn[0, 3] == 3 and mn[0, 4] == 1 and mn[0, 6] == 2


def test_forced_end_applies_when_no_exit_inside():
    O, H, L, C, LL, atr = _windows(5, 3)
    entry = O[:, 0]
    # only 10 valid bars: a hold_20d cannot exit inside, a hold_5d exits at bar 5
    nv = np.full(5, 10)
    eb, px, why = R.action_exits("hold", 20, 2.0, O, H, L, C, LL, entry, np.full(5, 1e6), nv)
    assert (eb == R.W).all() and np.isnan(px).all()
    eb5, px5, why5 = R.action_exits("hold", 5, 2.0, O, H, L, C, LL, entry, np.full(5, 1e6), nv)
    assert (eb5 == 5).all() and np.allclose(px5, O[:, 5]) and (why5 == "time").all()
    # a pending decision on the last valid bar has no next bar inside: the forced end applies
    eb10, _, _ = R.action_exits("hold", 10, 2.0, O, H, L, C, LL, entry, np.full(5, 1e6), nv)
    assert (eb10 == R.W).all()


def test_stops_table_reasons():
    s = R.stops_table()
    assert set(s["end_reason"]) <= {"followed", "relist_no_factor", "end_exchange_change", "end_scheme", "end_failed"}
    assert (s.loc[s["class"].isin(["scheme", "voluntary_delisting"]), "end_reason"] == "end_scheme").all()
    assert (s.loc[(s["class"] == "renamed") & ~s["check"], "end_reason"] == "followed").all()
    assert (s.loc[(s["class"] == "renamed") & s["check"], "end_reason"] == "relist_no_factor").all()
    assert (s.loc[s["symbols"].str.upper().str.contains("SPICEJET"), "end_reason"] == "end_exchange_change").all()
