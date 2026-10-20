"""SP3 pre-freeze step 2 (stage-1 candidates, india/sp3.py prep counts) on synthetic data, no lake needed: each family fires and does not fire on
hand-built series; eligibility; spacing comes before priority; CTL and the ANY rate; the hash is reproducible; nothing after T changes a
decision on T (future bars and events edited, or cut off)."""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
import pytest

from india import sp3

N = 600          # bars per synthetic stock; bar T = 560 falls on 2010-02-24, after the 2010 start of BAND and GAPD
T = 560
START = "2008-01-01"
DATES = pd.bdate_range(START, periods=1000)
SESSIONS = list(DATES)


def base(seed: int = 0, drift: float = 0.0015, noise: float = 0.01, n: int = N) -> pd.DataFrame:
    """A quiet uptrend: closes about 15% above the 200-day average and 1.5% above the 20-day, iid 1% noise, flat volume (so no BRK fires)."""
    rng = np.random.default_rng(seed)
    c = 100 * np.exp(drift * np.arange(n) + noise * rng.standard_normal(n))
    o = np.r_[c[0], c[:-1]]
    return pd.DataFrame({"date": DATES[:n], "o": o, "h": np.maximum(o, c) * 1.002, "l": np.minimum(o, c) * 0.998, "c": c, "volume": 1000.0})


def fix(b: pd.DataFrame, i: int, **kw) -> pd.DataFrame:
    """Set bar i's fields and keep the bar consistent (high above open and close, low below)."""
    b = b.copy()
    for k, v in kw.items():
        b.loc[i, k] = v
    b.loc[i, "h"] = max(b.loc[i, "h"], b.loc[i, "o"], b.loc[i, "c"])
    b.loc[i, "l"] = min(b.loc[i, "l"], b.loc[i, "o"], b.loc[i, "c"])
    return b


def lab_features(bars: pd.DataFrame) -> pd.DataFrame:
    """india.lab.build_features recomputed in pandas for synthetic bars (the same windows; each row uses its own and earlier rows). liq_rank: rank
    of the 60-bar median turnover, as U_LIQ-IN, from bar 126 on."""
    out = []
    for sid, g in bars.sort_values(["sid", "date"]).groupby("sid", sort=False):
        g = g.reset_index(drop=True)
        o, h, l, c, v = g["o"], g["h"], g["l"], g["c"], g["volume"]
        pc = c.shift(1)
        tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
        f = pd.DataFrame({"date": g["date"], "sid": sid, "symbol": sid, "o": o, "h": h, "l": l, "c": c, "ret_1": c / pc - 1, "ret_60": c / c.shift(60) - 1,
                          "gap_pct": o / pc - 1, "atr14": tr.rolling(14, min_periods=1).mean(), "vol_ratio20": v / v.shift(1).rolling(20, min_periods=1).mean(),
                          "dist_sma20": c / c.rolling(20, min_periods=1).mean() - 1, "dist_sma50": c / c.rolling(50, min_periods=1).mean() - 1,
                          "dist_sma200": c / c.rolling(200, min_periods=1).mean() - 1, "breakout20": c > h.shift(1).rolling(20, min_periods=1).max(),
                          "med60": (c * v).rolling(60, min_periods=1).median(), "n": np.arange(len(g)) + 1})
        out.append(f)
    f = pd.concat(out, ignore_index=True)
    f = f[f["n"] >= 126].copy()
    f["liq_rank"] = f.groupby("date")["med60"].rank(ascending=False, method="min").astype(int)
    return f.drop(columns=["med60", "n"]).reset_index(drop=True)


def frame(stocks: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    bars = pd.concat([b.assign(sid=s) for s, b in stocks.items()], ignore_index=True)
    bars["raw_close"] = bars["c"]
    return lab_features(bars), bars[["sid", "date", "o", "h", "l", "c", "raw_close"]]


EMPTY = pd.DataFrame({"sid": pd.Series(dtype=str), "date": pd.Series(dtype="datetime64[ns]")})
NODIV = pd.DataFrame({"symbol": pd.Series(dtype=str), "date": pd.Series(dtype="datetime64[ns]"), "amount": pd.Series(dtype=float),
                      "known_from": pd.Series(dtype="datetime64[ns]")})


def fired(stocks, fam, sid="S", i=T, ca=EMPTY, band=EMPTY, div=NODIV) -> bool:
    feat, bars = frame(stocks)
    p = sp3.panel(feat, bars, ca, band, div, SESSIONS, None, START, str(DATES[N - 1].date()))
    row = p[(p["sid"] == sid) & (p["date"] == DATES[i])]
    assert len(row) == 1
    return bool(row["f_" + fam].iloc[0])


# ------------------------------------------------------------------------------------------------ each family fires / does not fire

def test_base_series_is_quiet():
    feat, bars = frame({"S": base()})
    p = sp3.panel(feat, bars, EMPTY, EMPTY, NODIV, SESSIONS, None, START, str(DATES[N - 1].date()))
    at = p[p["date"] == DATES[T]].iloc[0]
    assert at["dist_sma200"] > 0.08 and not any(at[f"f_{x}"] for x in ("BRK", "PULL", "REV", "DECL", "BAND", "LO52", "BBMR", "GAPU", "GAPD", "RETEST"))


def test_brk_volume_at_least_1_5x():
    b = base()
    hi = b["h"].iloc[T - 20:T].max()
    up = fix(b, T, c=hi * 1.02, volume=2000.0)
    assert fired({"S": up}, "BRK")
    assert fired({"S": fix(b, T, c=hi * 1.02, volume=1500.0)}, "BRK")          # exactly 1.5x: "at least"
    assert not fired({"S": fix(b, T, c=hi * 1.02, volume=1400.0)}, "BRK")
    assert not fired({"S": fix(b, T, c=hi * 0.999, o=hi * 0.99, volume=2000.0)}, "BRK")   # close not above the 20-day high


def test_pull():
    b = base()
    s19 = b["c"].iloc[T - 19:T].sum()   # the 19 closes before T; the 20-day average on T includes T's close
    c_hit = 0.94 * s19 / (20 - 0.94)    # c / ((s19 + c) / 20) = 0.94: 6% under the 20-day average
    assert fired({"S": fix(b, T, c=c_hit, o=c_hit)}, "PULL")
    c_miss = 0.96 * s19 / (20 - 0.96)
    assert not fired({"S": fix(b, T, c=c_miss, o=c_miss)}, "PULL")


def test_rev_rsi_under_30():
    b = base()
    down = b.copy()
    for k in range(T - 12, T + 1):
        down = fix(down, k, c=down.loc[k - 1, "c"] * 0.97, o=down.loc[k - 1, "c"])
    assert fired({"S": down}, "REV")
    mixed = b.copy()
    for k in range(T - 12, T + 1):
        mixed = fix(mixed, k, c=mixed.loc[k - 1, "c"] * (0.97 if k % 2 else 1.03), o=mixed.loc[k - 1, "c"])
    assert not fired({"S": mixed}, "REV")


def test_decl_more_than_30pct_in_60():
    b = base()
    c0 = b.loc[T - 60, "c"]
    for frac, want in ((0.65, True), (0.75, False)):
        d = b.copy()
        for k in range(T - 59, T + 1):
            lvl = c0 * (1 - (1 - frac) * (k - (T - 60)) / 60)
            d = fix(d, k, c=lvl, o=lvl)
        assert fired({"S": d}, "DECL") is want


def test_band_within_last_5_sessions():
    b = {"S": base()}
    hit = lambda i: pd.DataFrame({"sid": ["S"], "date": [DATES[i]]})
    assert fired(b, "BAND", band=hit(T - 4))       # T-4..T are the last 5 sessions
    assert not fired(b, "BAND", band=hit(T - 5))
    assert not fired(b, "BAND", band=hit(T + 1))   # a hit after T never counts


def test_hi52_strictly_above_250_closes():
    b = base()
    top = b["c"].iloc[T - 250:T].max()
    assert fired({"S": fix(b, T, c=top * 1.01)}, "HI52")
    assert not fired({"S": fix(b, T, c=top)}, "HI52")           # equal is not strictly above


def test_lo52_strictly_below_250_closes():
    b = base()
    low = b["c"].iloc[T - 250:T].min()
    assert fired({"S": fix(b, T, c=low * 0.99, o=low)}, "LO52")
    assert not fired({"S": fix(b, T, c=low, o=low * 1.01)}, "LO52")


def test_sqz_width_at_10th_percentile():
    b = base()
    calm = b.copy()
    for k in range(T - 25, T + 1):              # the last 20 closes barely move: the narrowest width of the 250
        calm = fix(calm, k, c=calm.loc[T - 26, "c"] * (1 + 0.0002 * (k - T + 26)), o=calm.loc[T - 26, "c"])
    assert fired({"S": calm}, "SQZ")
    loud = b.copy()
    for k in range(T - 19, T + 1):
        loud = fix(loud, k, c=loud.loc[k, "c"] * (1.05 if k % 2 else 0.97))
    assert not fired({"S": loud}, "SQZ")


def test_bbmr_under_lower_band_above_200():
    b = base()
    m = b["c"].iloc[T - 19:T].mean()
    assert fired({"S": fix(b, T, c=m * 0.95, o=m)}, "BBMR")
    assert not fired({"S": fix(b, T, c=m * 0.995, o=m)}, "BBMR")


def test_gapu_open_and_close_3pct_up():
    b = base()
    pc = b.loc[T - 1, "c"]
    assert fired({"S": fix(b, T, o=pc * 1.04, c=pc * 1.035)}, "GAPU")
    assert fired({"S": fix(b, T, o=pc * 1.03, c=pc * 1.03)}, "GAPU")      # exactly 3%: "at least"
    assert not fired({"S": fix(b, T, o=pc * 1.04, c=pc * 1.02)}, "GAPU")  # the close gave back the gap


def test_gapd_and_the_dividend_exclusion():
    b = base()
    pc = b.loc[T - 1, "c"]
    s = {"S": fix(b, T, o=pc * 0.96, c=pc * 0.965)}
    assert fired(s, "GAPD")
    assert not fired({"S": fix(b, T, o=pc * 0.96, c=pc * 0.98)}, "GAPD")
    div = lambda amt, known: pd.DataFrame({"symbol": ["S"], "date": [DATES[T]], "amount": [amt], "known_from": [DATES[known]]})
    assert not fired(s, "GAPD", div=div(pc * 0.025, T - 8))    # ex-date of a 2.5% dividend: a false gap
    assert not fired(s, "GAPD", div=div(pc * 0.02, T - 8))     # exactly 2%: "2% or more"
    assert fired(s, "GAPD", div=div(pc * 0.01, T - 8))         # a 1% dividend does not explain a 3.5% gap
    assert fired(s, "GAPD", div=div(pc * 0.025, T + 1))        # a record first listed after T was not known on T


def test_retest_of_the_latest_breakout_5_to_60_sessions_back():
    b = base()
    B = T - 10
    hi = b["h"].iloc[B - 20:B].max()
    b = fix(b, B, c=hi * 1.03, volume=2000.0)
    level = b["c"].iloc[B - 20:B].max()
    s = fix(b, T, c=level * 1.01, l=level * 0.995, o=level * 1.012)
    assert fired({"S": s}, "RETEST")
    assert not fired({"S": fix(b, T, c=level * 0.99, l=level * 0.98, o=level)}, "RETEST")        # closed back under the level
    far = fix(b, T, c=level * 1.2, o=level * 1.2, l=level * 1.19)
    assert not fired({"S": far}, "RETEST")                                                        # low nowhere near level + 1 ATR
    young = fix(base(), T - 3, c=base()["h"].iloc[T - 23:T - 3].max() * 1.03, volume=2000.0)
    lv = young["c"].iloc[T - 23:T - 3].max()
    assert not fired({"S": fix(young, T, c=lv * 1.01, l=lv * 0.995, o=lv * 1.012)}, "RETEST")   # the breakout is only 3 sessions old


def test_mom_top_decile_on_month_end_only():
    end = max(d for d in DATES[:N] if d.month == DATES[T].month and d.year == DATES[T].year)
    i_end = list(DATES).index(end)
    stocks = {f"S{k:02d}": base(seed=k, drift=0.0005 + 0.0002 * k) for k in range(12)}   # S11 has the strongest 250-session trend
    feat, bars = frame(stocks)
    p = sp3.panel(feat, bars, EMPTY, EMPTY, NODIV, SESSIONS, None, START, str(DATES[N - 1].date()))
    on = p[p["date"] == end]
    assert set(on.loc[on["f_MOM"], "sid"]) == {on.loc[on["mom"].idxmax(), "sid"]}       # n = 12: floor(12 / 10) = 1 stock
    assert not p.loc[p["date"] == DATES[i_end - 1], "f_MOM"].any()


def test_unconfirmed_corporate_action_in_200_sessions_blocks():
    b = {"S": fix(base(), T, o=base().loc[T - 1, "c"] * 1.04, c=base().loc[T - 1, "c"] * 1.035)}
    feat, bars = frame(b)
    for back, ok in ((199, False), (0, False), (200, True)):
        ca = pd.DataFrame({"sid": ["S"], "date": [DATES[T - back]]})
        p = sp3.panel(feat, bars, ca, EMPTY, NODIV, SESSIONS, None, START, str(DATES[N - 1].date()))
        assert bool(p.loc[p["date"] == DATES[T], "elig"].iloc[0]) is ok


# ------------------------------------------------------------------------------------------------ spacing, priority, CTL, ANY, hash

def _p(rows):
    """Hand-built panel rows: (sid, date, families firing)."""
    fams = list(sp3.REAL)
    out = []
    for sid, d, fs in rows:
        out.append({"sid": sid, "date": pd.Timestamp(d), "liq_rank": 1, "elig": True, **{"f_" + f: f in fs for f in fams}})
    return pd.DataFrame(out)


def test_spacing_comes_before_priority():
    p = _p([("S", "2010-01-04", {"BRK"}), ("S", "2010-01-14", {"BRK", "PULL"}), ("S", "2010-01-18", {"BRK"}), ("S", "2010-01-25", {"PULL"}),
            ("Q", "2010-01-14", set())])
    cand, info = sp3.assemble(p, ["BRK", "PULL"], rate=0.0, start="2010-01-01")
    got = {(r.family, str(r.signal_date.date()), r.priority_family) for r in cand.itertuples() if r.family != "CTL"}
    # BRK on the 14th is 10 days after the kept BRK of the 4th: spaced out first, so the 14th belongs to PULL (priority first would have given the
    # 14th to BRK and then lost it to spacing); BRK on the 18th is 14 days after the 4th (kept); PULL on the 25th is 11 days after the 14th (spaced out)
    assert got == {("BRK", "2010-01-04", True), ("PULL", "2010-01-14", True), ("BRK", "2010-01-18", True)}
    assert info["rows_after_spacing_total"] == {"BRK": 2, "PULL": 1, "CTL": 3}
    assert info["distinct_real_family_stock_days"] == 3 and info["ctl_rows"] == 3 and info["non_any_rows"] == 6


def test_priority_order_and_any_never_beats_a_real_family():
    p = _p([("S", "2010-01-04", {"DECL", "RETEST", "BRK"}), ("Q", "2010-01-04", set())])
    cand, _ = sp3.assemble(p, ["BRK", "DECL", "RETEST"], rate=0.03, start="2010-01-01")
    pri = cand[cand["priority_family"]]
    assert set(zip(pri["sid"], pri["family"])) <= {("S", "RETEST"), ("Q", "ANY")}
    assert ("S", "RETEST") in set(zip(pri["sid"], pri["family"]))
    assert not cand.loc[cand["family"] == "CTL", "priority_family"].any()
    # force an ANY row on S: with rate 1.0 every eligible stock-day is drawn, and S's ANY row loses to its real-family row
    cand, _ = sp3.assemble(p, ["BRK", "DECL", "RETEST"], rate=1.0, start="2010-01-01")
    s_any = cand[(cand["sid"] == "S") & (cand["family"] == "ANY")]
    assert len(s_any) == 1 and not s_any["priority_family"].iloc[0]
    assert cand[(cand["sid"] == "Q") & (cand["family"] == "ANY")]["priority_family"].all()


def test_ctl_takes_lowest_hash_13_and_is_not_spaced():
    days = ["2010-01-04", "2010-01-05"]
    sids = [f"X{k}" for k in range(8)]
    rows = [(s, d, {"BRK"} if (s in ("X0", "X1") and d == days[0]) or (s == "X0" and d == days[1]) else set()) for s in sids for d in days]
    cand, info = sp3.assemble(_p(rows), ["BRK"], rate=0.0, start="2010-01-01")
    ctl = cand[cand["family"] == "CTL"]
    for d, k in ((days[0], 2), (days[1], 0)):                # X0's second BRK is spaced out, so day 2 has no real-family stock-day
        want = sorted(sids, key=lambda s: sp3.hash_u(s, d, 13))[:k]
        assert sorted(ctl.loc[ctl["signal_date"] == pd.Timestamp(d), "sid"]) == sorted(want)
    assert info["ctl_rows"] == info["distinct_real_family_stock_days"] == 2


def test_any_draw_then_spacing():
    rows = [("S", str(d.date()), set()) for d in pd.bdate_range("2010-01-01", periods=40)]
    cand, info = sp3.assemble(_p(rows), ["BRK"], rate=1.0, start="2010-01-01")
    got = list(cand.loc[cand["family"] == "ANY", "signal_date"])
    assert all((b - a).days >= 14 for a, b in zip(got, got[1:])) and len(got) == info["any_rows"] < info["any_drawn_before_spacing"] == 40


def test_any_rate_formula():
    assert sp3.any_rate(100_000, 5_000_000)[0] == 0.03            # (300k / 5M = 6%) capped at 3%
    assert sp3.any_rate(380_000, 1_000_000)[0] == 0.02
    assert sp3.any_rate(390_000, 1_000_000)[0] == 0.01            # exactly 1%: an exact multiple survives the rounding
    assert sp3.any_rate(391_000, 1_000_000)[0] == 0.005           # 0.9% rounds down to 0.5%
    assert sp3.any_rate(399_000, 1_000_000)[0] == 0.005           # 0.1%: at least 0.5%
    assert sp3.any_rate(450_000, 1_000_000)[0] == 0.005           # non-ANY rows alone over 400k: nothing is thinned, the floor applies
    assert sp3.any_rate(250_000, 1_000_000) == (0.03, 0.15)


def test_hash_reproducible():
    sid, d = "INE002A01018", "2015-03-02"
    want = int(hashlib.sha256(f"{sid}|{d}|11".encode()).hexdigest()[:8], 16) / 16 ** 8
    assert sp3.hash_u(sid, d, 11) == want == sp3.hash_u(sid, pd.Timestamp(d), 11)
    assert sp3.hash_u("RELIANCE", "2007-06-29", 13) == int(hashlib.sha256(b"RELIANCE|2007-06-29|13").hexdigest()[:8], 16) / 4294967296.0
    many = sp3.hash_many(["INE002A01018", "RELIANCE"], [pd.Timestamp(d), pd.Timestamp("2007-06-29")], 11)
    assert many[0] == want and many[1] == sp3.hash_u("RELIANCE", "2007-06-29", 11)
    assert 0 <= want < 1 and sp3.hash_u(sid, d, 13) != want


# ------------------------------------------------------------------------------------------------ nothing after T changes a decision on T

NR, CUT = 900, 700   # the random panel runs to 2011-06; T = bar 700 (2010-09) so BAND and GAPD have eight months before it


def _random_stocks(seed: int, n_stocks: int = 14) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    out = {}
    for k in range(n_stocks):
        r = rng.standard_normal(NR) * 0.022 + rng.normal(0, 0.0012)
        c = 100 * np.exp(np.cumsum(r))
        o = np.r_[c[0], c[:-1]] * np.exp(rng.standard_normal(NR) * 0.015)
        h = np.maximum(o, c) * (1 + np.abs(rng.standard_normal(NR)) * 0.01)
        l = np.minimum(o, c) * (1 - np.abs(rng.standard_normal(NR)) * 0.01)
        v = 1000 * np.exp(rng.standard_normal(NR) * 0.5)
        out[f"R{k:02d}"] = pd.DataFrame({"date": DATES[:NR], "o": o, "h": h, "l": l, "c": c, "volume": v})
    return out


def _events(stocks, seed, lo, hi):
    rng = np.random.default_rng(seed)
    sids = list(stocks)
    pick = lambda n: pd.DataFrame({"sid": rng.choice(sids, n), "date": DATES[rng.integers(lo, hi, n)]}).drop_duplicates()
    band, ca = pick(80), pick(3)
    dv = pick(25).rename(columns={"sid": "symbol"})
    dv["amount"] = rng.uniform(0.5, 6.0, len(dv))
    dv["known_from"] = dv["date"] - pd.Timedelta(days=7)
    return ca, band, dv


def test_nothing_after_T_changes_the_candidates():
    stocks = _random_stocks(5)
    cut, end = DATES[CUT], str(DATES[NR - 1].date())
    ca, band, dv = _events(stocks, 6, 130, CUT)
    feat, bars = frame(stocks)
    base_c, _, _ = sp3.stage1(feat, bars, ca, band, dv, SESSIONS, rate=0.03, start="2008-07-01", end=end)
    want = base_c[base_c["signal_date"] <= cut].reset_index(drop=True)
    assert len(want) > 300 and set(want["family"]) >= {"BRK", "PULL", "REV", "BAND", "HI52", "LO52", "GAPU", "GAPD", "MOM", "CTL", "ANY"}
    # 1) every bar after T rewritten (prices and volume), and new events after T
    rng = np.random.default_rng(9)
    edited = {}
    for s, b in stocks.items():
        e = b.copy()
        fut = e["date"] > cut
        for col in ("o", "c", "volume"):
            e.loc[fut, col] = e.loc[fut, col] * rng.uniform(0.3, 3.0, fut.sum())
        e.loc[fut, "h"] = e.loc[fut, ["o", "c"]].max(axis=1) * 1.01
        e.loc[fut, "l"] = e.loc[fut, ["o", "c"]].min(axis=1) * 0.99
        edited[s] = e
    ca2, band2, dv2 = _events(stocks, 7, CUT + 1, NR)
    feat2, bars2 = frame(edited)
    got, _, _ = sp3.stage1(feat2, bars2, pd.concat([ca, ca2]), pd.concat([band, band2]), pd.concat([dv, dv2]), SESSIONS, rate=0.03, start="2008-07-01", end=end)
    pd.testing.assert_frame_equal(got[got["signal_date"] <= cut].reset_index(drop=True), want)
    # 2) everything after T cut off (the calendar stays: exchange holidays are published ahead, so month ends are known)
    feat3, bars3 = feat[feat["date"] <= cut], bars[bars["date"] <= cut]
    got3, _, _ = sp3.stage1(feat3, bars3, ca, band, dv, SESSIONS, rate=0.03, start="2008-07-01", end=end)
    pd.testing.assert_frame_equal(got3.reset_index(drop=True), want)


def test_struck_results_families_are_required():
    with pytest.raises(NotImplementedError):
        sp3.stage1(pd.DataFrame(), pd.DataFrame(), EMPTY, EMPTY, NODIV, SESSIONS, struck=("RESU",))


# ------------------------------------------------------------------------------------------------ prep stops (2005-2023 permanent stops)

CAL = list(pd.bdate_range("2020-01-01", periods=400))
E_TEST = str(CAL[-1].date())


def _rows(spec):
    """spec: (symbol, series, isin, sid, first index, last index) -> cash rows on the calendar CAL."""
    out = []
    for sym, ser, isin, sid, a, z in spec:
        for d in CAL[a:z + 1]:
            out.append({"date": d, "symbol": sym, "series": ser, "isin": isin, "sid": sid})
    return pd.DataFrame(out)


def test_stop_cases_boundary_62_sessions_and_all_series():
    n = len(CAL) - 1
    rows = _rows([("AAA", "EQ", "INE000A01011", "INE000A01011", 0, n - 62),                   # E - L = 62: a stop
                  ("BBB", "EQ", "INE000B01011", "INE000B01011", 0, n - 61),                   # 61: data_end, not a stop
                  ("CCC", "EQ", "INE000C01011", "INE000C01011", 0, n - 100), ("CCC", "BZ", "INE000C01011", "INE000C01011", n - 99, n - 10)])  # BZ rows count
    got = sp3.stop_cases(rows, {"INE000A01011", "INE000B01011", "INE000C01011"}, CAL, E_TEST)
    assert list(got["sid"]) == ["INE000A01011"] and int(got["gap"].iloc[0]) == 62


def test_settle_key_switch_and_symbol_change():
    rows = _rows([("OLDCO", "EQ", None, "OLDCO", 0, 200), ("OLDCO", "EQ", "INE111A01011", "INE111A01011", 201, 399),        # 2011-style key switch
                  ("XONE", "EQ", None, "XONE", 0, 150), ("XTWO", "EQ", None, "XTWO", 151, 399),                              # rename, next session
                  ("YONE", "EQ", None, "YONE", 0, 150), ("YTWO", "EQ", None, "YTWO", 180, 399)])                             # new symbol 30 sessions later
    cases = sp3.stop_cases(rows, {"OLDCO", "XONE", "YONE"}, CAL, E_TEST)
    sc = [{"old": "XONE", "new": "XTWO", "effective": str(CAL[151].date()), "company": "X"}, {"old": "YONE", "new": "YTWO", "effective": str(CAL[151].date()), "company": "Y"}]
    got = sp3.settle_mechanical(cases, sp3._Rows(rows), sc)
    assert got["OLDCO"]["class"] == "renamed" and got["OLDCO"]["successor"] == "INE111A01011" and "carries ISIN" in got["OLDCO"]["evidence"]
    assert got["XONE"]["successor"] == "XTWO"
    assert "YONE" not in got                       # the new symbol starts too late to be the same stock without a record: left to the manual list


def test_mechanical_rule_window_and_precedence():
    n = len(CAL) - 1
    spec = [(f"S{k}", "EQ", f"INE00{k}A01011", f"INE00{k}A01011", 0, 300) for k in range(5)]
    rows = _rows(spec + [("OLDCO", "EQ", None, "OLDCO", 0, 300), ("OLDCO", "EQ", "INE999A01011", "INE999A01011", 301, n)])
    sids = {f"INE00{k}A01011" for k in range(5)} | {"OLDCO"}
    cases = sp3.stop_cases(rows, sids, CAL, E_TEST)
    L = CAL[300]
    ann = pd.DataFrame([
        {"symbol": "S0", "isin": None, "category": "Amalgamation/Merger", "date": CAL[200], "text": "scheme of amalgamation"},          # scheme
        {"symbol": "S1", "isin": None, "category": "Voluntary Delisting", "date": CAL[290], "text": "delisting offer"},                 # voluntary
        {"symbol": "S2", "isin": None, "category": "Delisting", "date": CAL[290], "text": "has delisted its shares from the Delhi Stock Exchange"},  # regional: no
        {"symbol": "S3", "isin": None, "category": "Amalgamation/Merger", "date": CAL[300 - 250], "text": "x"},                          # one session too early
        {"symbol": "S4", "isin": None, "category": "Voluntary Delisting", "date": CAL[280], "text": "x"},
        {"symbol": "S4", "isin": None, "category": "Scheme of Arrangement", "date": CAL[250], "text": "x"}])                          # scheme beats voluntary
    empty_p = pd.DataFrame({"date": pd.Series(dtype="datetime64[ns]"), "symbol": pd.Series(dtype=str), "subject": pd.Series(dtype=str)})
    empty_b = pd.DataFrame({"symbol": pd.Series(dtype=str), "isin": pd.Series(dtype=str), "ex_date": pd.Series(dtype="datetime64[ns]"), "subject": pd.Series(dtype=str)})
    rx = sp3._Rows(rows)
    settled = sp3.settle_mechanical(cases, rx, [])
    m = sp3.mechanical(cases, rx, CAL, settled, ann, empty_p, empty_b, E_TEST).set_index("sid")["mech_class"]
    assert m["INE000A01011"] == "scheme" and m["INE001A01011"] == "voluntary_delisting" and m["INE002A01011"] == "end_failed"
    assert m["INE003A01011"] == "end_failed" and m["INE004A01011"] == "scheme" and m["OLDCO"] == "renamed"
    assert all(pd.Timestamp(x) == L for x in cases["L"])
