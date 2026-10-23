"""SZ2 trade table: the structure legs, the expiry rule, the smile and the value-lowering stress, on synthetic inputs."""
import datetime as dt

import numpy as np

from india import sz2


def test_smile_interpolates_in_log_moneyness_and_is_flat_beyond():
    ks = np.array([10800.0, 10900.0, 11000.0])
    ivs = np.array([0.14, 0.12, 0.10])
    f = 10900.0
    assert abs(sz2.smile_iv(ks, ivs, f, 10900.0) - 0.12) < 1e-12
    mid = sz2.smile_iv(ks, ivs, f, 10950.0)
    assert 0.10 < mid < 0.12
    assert sz2.smile_iv(ks, ivs, f, 12000.0) == 0.10 and sz2.smile_iv(ks, ivs, f, 9000.0) == 0.14
    assert np.isnan(sz2.smile_iv(np.array([]), np.array([]), f, 10900.0))


def _sessions_after(day, exp):
    n, d = 0, day + dt.timedelta(days=1)
    while d <= exp:
        if d.weekday() < 5:
            n += 1
        d += dt.timedelta(days=1)
    return n


def test_expiry_rule_nifty_nearest_with_two_sessions_three_for_nextopen():
    day = dt.date(2023, 6, 13)  # Tuesday
    exps = [dt.date(2023, 6, 15), dt.date(2023, 6, 22), dt.date(2023, 6, 29)]
    assert sz2.choose_expiry("NIFTY", day, exps, _sessions_after, nextopen=False) == dt.date(2023, 6, 15)   # 2 sessions left
    assert sz2.choose_expiry("NIFTY", day, exps, _sessions_after, nextopen=True) == dt.date(2023, 6, 22)    # needs 3
    assert sz2.choose_expiry("NIFTY", dt.date(2023, 6, 14), exps, _sessions_after, nextopen=False) == dt.date(2023, 6, 22)  # 1 left: next


def test_expiry_rule_banknifty_monthly_only():
    day = dt.date(2023, 6, 27)  # Tuesday; the June monthly is the 29th (2 sessions left)
    exps = [dt.date(2023, 6, 28), dt.date(2023, 6, 29), dt.date(2023, 7, 6), dt.date(2023, 7, 27)]
    assert sz2.choose_expiry("BANKNIFTY", day, exps, _sessions_after, nextopen=False) == dt.date(2023, 6, 29)
    assert sz2.choose_expiry("BANKNIFTY", day, exps, _sessions_after, nextopen=True) == dt.date(2023, 7, 27)   # monthly with 3+ sessions


def test_leg_strikes():
    listed = np.arange(10000.0, 12001.0, 50.0)
    traded = listed[(listed >= 10500) & (listed <= 11500)]
    px = 10876.0
    legs, why = sz2.leg_strikes("LONG_ATM", "CE", px, listed, traded, "NIFTY")
    assert legs == [(10900.0, 1)] and why is None
    legs, _ = sz2.leg_strikes("LONG_OTM1", "CE", px, listed, traded, "NIFTY")
    assert legs == [(10950.0, 1)]                      # at least one step (50) out of the money from the price
    legs, _ = sz2.leg_strikes("LONG_OTM1", "PE", px, listed, traded, "NIFTY")
    assert legs == [(10800.0, 1)]
    legs, _ = sz2.leg_strikes("SPREAD_NARROW", "CE", px, listed, traded, "NIFTY")
    assert legs == [(10900.0, 1), (11000.0, -1)]       # W = 100 further out from ATM
    legs, _ = sz2.leg_strikes("SPREAD_WIDE", "PE", px, listed, traded, "NIFTY")
    assert legs == [(10900.0, 1), (10700.0, -1)]
    legs, why = sz2.leg_strikes("SPREAD_WIDE", "CE", 11480.0, listed, traded, "NIFTY")
    assert legs is None and why == "strike"            # no traded short leg 200 further out


def test_stress_shift_lowers_the_position_value():
    legs = [(10900.0, 1), (11000.0, -1)]
    iv_of = lambda F, K: 0.15
    v0 = sz2._value(legs, 10900.0, 10 / 365, iv_of, True)
    v1 = sz2._value(legs, 10900.0, 10 / 365, iv_of, True, shift=0.02)
    assert v1 < v0
    v_long0 = sz2._value([(10900.0, 1)], 10900.0, 10 / 365, iv_of, True)
    v_long1 = sz2._value([(10900.0, 1)], 10900.0, 10 / 365, iv_of, True, shift=0.02)
    assert v_long1 < v_long0


def test_half_spread_fallback_rule():
    assert sz2._hs("NIFTY", 50.0) == 0.5 and sz2._hs("NIFTY", 500.0) == 2.0 and sz2._hs("BANKNIFTY", 100.0) == 1.0
